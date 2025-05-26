from __future__ import absolute_import, unicode_literals

# 导入 celery 实例
from .eva_backend_django.celery import app as celery_app

__all__ = ('celery_app',)
