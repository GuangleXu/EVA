# EVA_backend/llm_manager_app/apps.py

from django.apps import AppConfig
from logs.logs import logger
import asyncio


class LlmManagerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'llm_manager_app'

    def ready(self):
        try:
            from llm_manager_app.utils.llm_service import llm_service
            
            logger.debug("🔄 LLM服务初始化状态检查: is_initialized=%s", llm_service.is_initialized)
            
            if not llm_service.is_initialized:
                logger.info("🚀 启动LLM核心引擎...")
                # 不在这里初始化，而是在 ASGI 应用启动时初始化
                logger.info("✅ LLM服务将在 ASGI 应用启动时初始化")
                
        except Exception as e:
            logger.error("‼️ 关键服务初始化失败", exc_info=True)

