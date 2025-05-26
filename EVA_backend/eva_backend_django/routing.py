# EVA_backend/eva_backend_django/routing.py

from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from llm_manager_app.consumers import LLMConsumer
from memory_service_app.consumers import MemoryConsumer

# WebSocket 路由配置
websocket_urlpatterns = [
    # LLM服务的WebSocket路由 - ws://localhost:8000/ws/llm/
    path("ws/llm/", LLMConsumer.as_asgi(), name='llm-websocket'),
    
    # 记忆服务的WebSocket路由 - ws://localhost:8000/ws/memory/
    path("ws/memory/", MemoryConsumer.as_asgi(), name='memory-websocket'),
]

# 应用路由配置
application = ProtocolTypeRouter({
    # HTTP路由配置将由Django自动处理
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})


