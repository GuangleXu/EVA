# -*- coding: utf-8 -*-
"""Django's command-line utility for administrative tasks."""
import os
import sys
import asyncio

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# 添加 ChatTTS 模块路径
sys.path.insert(0, os.path.abspath(os.path.join(project_root, "ChatTTS_main")))

# === 入口测试日志输出 ===
print("【入口print】manage.py 启动成功")
try:
    from logs.logs import logger
    logger.info("【入口logger】manage.py 启动成功")
except Exception as e:
    print(f"【入口logger异常】{e}")

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eva_backend_django.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # 设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        execute_from_command_line(sys.argv)
    finally:
        loop.close()

if __name__ == "__main__":
    main()
