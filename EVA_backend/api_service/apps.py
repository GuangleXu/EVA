# 在 api_service/apps.py 中

from django.apps import AppConfig
from logs.logs import logger


class ApiServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_service'

    def ready(self):
        """当 Django 应用准备就绪时加载 LLM"""
        import sys
        if 'runserver' not in sys.argv and 'daphne' not in sys.argv:
            return

        try:
            logger.system("成功加载 LangChain 模型")
        except Exception as e:
            logger.error(f"加载 LangChain 模型时发生错误: {e}")
