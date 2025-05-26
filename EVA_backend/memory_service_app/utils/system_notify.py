import asyncio
from channels.layers import get_channel_layer

async def send_system_notification_to_frontend(message: str, level: str = "info"):
    """通过 WebSocket 向前端推送系统通知（如 Pinecone/LLM/Redis 异常/恢复）"""
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        await channel_layer.group_send(
            "llm_group",
            {
                "type": "system_message",
                "message": message,
                "level": level
            }
        ) 