# EVA_backend/eva_backend_django/apps.py

from django.apps import AppConfig
from django.core.management import call_command
import time
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EvaBackendDjangoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eva_backend_django'

    def ready(self):
        """在 Django 启动时执行健康检查"""
        if settings.DEBUG:
            logger.info("✅ [Startup] 开发模式，跳过健康检查")
            return

        logger.info("🚀 [Startup] 开始健康检查...")
        max_retries = 5  # 最大重试次数
        retry_delay = 5  # 每次重试间隔（秒）

        for attempt in range(max_retries):
            try:
                response = requests.get("http://127.0.0.1:8000/api/health/")
                if response.status_code == 200 and response.json().get("status") == "ok":
                    logger.info("✅ [Startup] 健康检查通过，服务器正常启动！")
                    return
                else:
                    logger.error(f"⚠️ [Startup] 健康检查失败: {response.json()}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ [Startup] 服务器无法访问健康检查 API: {e}")

            time.sleep(retry_delay)  # 等待后重试

        logger.error("🚨 [Startup] 服务器健康检查失败，终止启动！")
        raise RuntimeError("健康检查失败，Django 服务器未通过自检！")
