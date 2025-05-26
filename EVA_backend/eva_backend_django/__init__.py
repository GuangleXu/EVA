from __future__ import absolute_import, unicode_literals

# 导入 celery 实例
from .celery import app as celery_app

__all__ = ('celery_app',)
