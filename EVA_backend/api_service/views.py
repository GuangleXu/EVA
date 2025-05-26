# EVA_backend/api_service/views.py

import os
import json
import requests
import asyncio
from eva_backend_django import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from logs.logs import logger
from django.db import connections
from django.db.utils import OperationalError
from decouple import config
from llm_manager_app.utils.llm_service import Message, llm_service
import time
import redis
from eva_backend_django.celery import app as celery_app
from typing import cast, Any

# **健康检查 API**
@csrf_exempt
def health_check(request):
    """简单的健康检查，只检查基本服务是否可用"""
    status = {
        "database": True,
        "redis": True,
        "tts": True,
        "overall": True
    }
    messages = []

    try:
        # 检查数据库连接
        for conn_name in connections:
            try:
                connections[conn_name].cursor()
                logger.debug(f"✅ 数据库连接 {conn_name} 正常")
            except OperationalError:
                status["database"] = False
                status["overall"] = False
                msg = f"数据库连接 {conn_name} 失败"
                logger.error(f"❌ {msg}")
                messages.append(msg)

        # 检查 Redis 连接
        try:
            redis_port = int(settings.REDIS_PORT)
            conn = redis.Redis(host=str(settings.REDIS_HOST), port=redis_port)
            if not conn.ping():
                raise Exception("Redis ping failed")
            logger.debug("✅ Redis 连接正常")
        except Exception as e:
            status["redis"] = False
            status["overall"] = False
            msg = f"Redis 连接失败: {str(e)}"
            logger.error(f"❌ {msg}")
            messages.append(msg)

        # 检查 TTS 目录
        try:
            if not os.path.exists(settings.TTS_OUTPUT_DIR):
                os.makedirs(str(settings.TTS_OUTPUT_DIR), exist_ok=True)
            if not os.access(settings.TTS_OUTPUT_DIR, os.W_OK):
                status["tts"] = False
                status["overall"] = False
                msg = f"TTS 目录无写入权限: {settings.TTS_OUTPUT_DIR}"
                logger.error(f"❌ {msg}")
                messages.append(msg)
            else:
                logger.debug("✅ TTS 目录检查正常")
        except Exception as e:
            status["tts"] = False
            status["overall"] = False
            msg = f"TTS 目录检查失败: {str(e)}"
            logger.error(f"❌ {msg}")
            messages.append(msg)

        # 返回健康状态
        response_data = {
            "status": "ok" if status["overall"] else "unavailable",
            "checks": status,
            "messages": messages if messages else ["服务正常运行"]
        }
        return JsonResponse(response_data, status=200 if status["overall"] else 503)

    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return JsonResponse({
            "status": "unavailable",
            "error": str(e),
            "checks": status,
            "messages": messages + [str(e)]
        }, status=500)

@csrf_exempt
def modules_status(request):
    status = {
        "emotional_analyzer": "loaded",
    }
    return JsonResponse(status)
