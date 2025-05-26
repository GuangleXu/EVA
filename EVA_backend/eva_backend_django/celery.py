# EVA_backend/eva_backend_django/celery.py

from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

# 设置默认的 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eva_backend_django.settings')

# 初始化 Celery 应用
app = Celery('eva')

# 加载 Django 的 settings 配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# 确保 Celery 应用可以被导入
__all__ = ('app',)

