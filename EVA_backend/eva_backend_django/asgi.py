# EVA_backend/eva_backend_django/asgi.py

import os
import asyncio
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from .routing import websocket_urlpatterns
from logs.logs import logger
from memory_service_app.utils.redis_client import init_redis
from channels.auth import AuthMiddlewareStack
import channels.layers
from typing import cast, Any

# === 入口测试日志输出 ===
print("【入口print】asgi.py 启动成功")
try:
    from logs.logs import logger as entry_logger
    entry_logger.info("【入口logger】asgi.py 启动成功")
except Exception as e:
    print(f"【入口logger异常】{e}")

if not websocket_urlpatterns:
    raise ValueError("❌ WebSocket 端点 (websocket_urlpatterns) 为空！请检查 `routing.py` 是否正确配置。")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eva_backend_django.settings")

async def initialize_services():
    """初始化所有异步服务"""
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            logger.info("准备初始化 Redis ...")
            await init_redis()
            logger.info("✅ Redis 初始化完成")
            
            logger.info("准备验证 Channel Layer ...")
            channel_layer = cast(Any, channels.layers.get_channel_layer())
            test_channel = "test_channel"
            try:
                logger.info("准备 group_add ...")
                await channel_layer.group_add(test_channel, "test")
                logger.info("group_add 完成")
                logger.info("准备 group_discard ...")
                await channel_layer.group_discard(test_channel, "test")
                logger.info("group_discard 完成")
                logger.info(f"✅ Channels Layer 配置加载成功: {channel_layer}")
            except Exception as e:
                logger.error(f"❌ Channels Layer 测试失败: {str(e)}")
                raise
            
            logger.info("准备初始化 LLM 服务 ...")
            from llm_manager_app.utils.llm_service import llm_service
            await llm_service.initialize()
            logger.info("✅ LLM 服务初始化完成")
            
            logger.info("准备初始化 Memory 服务 ...")
            from memory_service_app.utils.central_executive import central_executive
            await central_executive.initialize()
            logger.info("✅ Memory 服务初始化完成")
            
            break  # 如果成功，跳出循环
            
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ 服务初始化失败 (尝试 {retry_count}/{max_retries}): {str(e)}")
            if retry_count < max_retries:
                logger.info(f"等待 5 秒后重试...")
                await asyncio.sleep(5)
            else:
                logger.error("❌ 服务初始化失败，已达到最大重试次数")
                raise

async def lifespan_app(scope, receive, send):
    """生命周期管理"""
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                # 初始化所有服务
                await initialize_services()
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                from memory_service_app.utils.redis_client import close_redis
                await close_redis()
                await send({"type": "lifespan.shutdown.complete"})
                return

# 创建ASGI应用
application = ProtocolTypeRouter({
    "lifespan": lifespan_app,
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        SessionMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})