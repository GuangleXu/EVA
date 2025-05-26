# EVA_backend/memory_service_app/apps.py

from django.apps import AppConfig
from logs.logs import logger

class MemoryServiceAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'memory_service_app'

    def ready(self):
        try:
            from memory_service_app.utils.central_executive import central_executive
            
            logger.info("🔄 Memory服务将在 ASGI 应用启动时初始化")
            
        except Exception as e:
            logger.error(f"❌ MemoryServiceApp 初始化失败: {str(e)}", exc_info=True)