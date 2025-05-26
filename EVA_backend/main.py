# EVA_backend/main.py

import os
import sys
import time
import signal
import asyncio
import traceback
import locale
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 关闭 transformers 的INFO/DEBUG日志（如有必要）
from logs.logs import logger
import logging
transformers_logger = logging.getLogger("transformers")
transformers_logger.setLevel(logging.ERROR)
transformers_logger.propagate = False

# 设置 Django 设置模块
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eva_backend_django.settings")

import django
from django.conf import settings

# 如果你还需要端口管理器，就保留，否则也可去掉
from eva_backend_django.utils.port_manager import PortManager  

# 如果你的 LongTermMemory 也不再需要，可以注释掉
# from EVA_backend.memory_service_app.utils.long_term_memory import LongTermMemory

def setup_locale():
    """设置本地化语言环境"""
    if sys.platform.startswith("win"):
        try:
            locale.setlocale(locale.LC_ALL, "C.UTF-8")
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, "zh_CN.UTF-8")
            except locale.Error:
                logger.warn("无法设置本地化编码，将使用默认设置")

# 设置必要的环境变量
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "1"
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# 强制设置标准输出流编码为 utf-8，防止 emoji/中文日志报错
# 某些环境下 sys.stdout 可能没有 reconfigure 方法，需判断
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 确保项目路径在 sys.path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def print_django_info():
    """打印 Django 信息"""
    print(f"Django version {django.get_version()}, using settings '{settings.SETTINGS_MODULE}'")
    print(f"Starting development server at http://127.0.0.1:8000/")
    print("Quit the server with CTRL-C.")

def start_daphne():
    """启动 Daphne 服务"""
    try:
        logger.system("启动 Daphne 服务...")
        import subprocess
        process = subprocess.Popen([
            "daphne",
            "-b", "127.0.0.1",
            "-p", "8000",
            "eva_backend_django.asgi:application"
        ])
        time.sleep(2)
        logger.system("Daphne 服务已启动")
        return process
    except Exception as e:
        logger.error(f"Daphne 启动失败: {e}")
        return None

async def shutdown(signal, loop, daphne_process):
    """清理并关闭服务"""
    logger.info(f"收到信号 {signal.name}，开始关闭服务...")

    # 终止 Daphne 服务
    if daphne_process:
        logger.info("正在终止 Daphne 服务...")
        daphne_process.terminate()
        daphne_process.wait()
        logger.info("Daphne 服务已关闭。")

    # 停止异步任务
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()

    logger.info(f"等待 {len(tasks)} 个任务完成...")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logger.info("服务关闭完成")

def handle_exception(loop, context):
    """处理未捕获的异常"""
    msg = context.get("exception", context["message"])
    logger.error(f"未捕获的异常: {msg}")
    logger.error("异常详情:", exc_info=context.get("exception"))

async def main():
    """主服务启动函数"""
    logger.system(f"当前工作目录: {os.getcwd()}")

    # 如果仍需要端口管理器
    port_manager = PortManager(8000)
    port_manager.ensure_port_available()

    # 启动 Daphne 服务
    daphne_process = start_daphne()

    # 如果你还需要初始化 LongTermMemory，则取消注释并调用
    # long_term_memory_manager = LongTermMemory()

    # 此处原先调用 query_siliconflow 的部分已删除

    # 使事件循环保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("主循环已取消。")

    return daphne_process

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}", exc_info=True)
    finally:
        logger.info("服务已完全关闭")
