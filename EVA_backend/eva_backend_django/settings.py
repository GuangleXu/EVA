# eva_backend_django/settings.py

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import traceback
from pathlib import Path
from decouple import config, Csv
import dj_database_url
from logs.logs import logger
from celery.schedules import crontab
import yaml

# 确保项目根目录在 Python 路径中
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

DEBUG = True

if DEBUG:
    import logging
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.asgi').setLevel(logging.WARNING)

def safe_config(key, default=None, cast=None):
    try:
        print(f"[DEBUG] config type: {type(config)}")  # 增加类型调试输出
        return config(key, default=default, cast=cast)
    except Exception as e:
        print(f"[settings.py] 环境变量 {key} 读取失败: {e}，使用默认值 {default}")
        return default

def trace_imports(frame, event, arg):
    if event == "call" and frame.f_code.co_name == "<module>" and DEBUG:
        module_name = frame.f_globals.get('__name__', '<unknown module>')
        print(f"Importing {module_name}")
    return None

# if DEBUG:
#     sys.settrace(trace_imports)
# else:
#     sys.settrace(None)

ROOT_URLCONF = 'eva_backend_django.urls'

SECRET_KEY = safe_config('DJANGO_SECRET_KEY', default='unsafe-key')
ALLOWED_HOSTS = safe_config('DJANGO_ALLOWED_HOSTS', default='127.0.0.1,localhost,*', cast=Csv())

INSTALLED_APPS = [
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "llm_manager_app.apps.LlmManagerAppConfig",
    "memory_service_app.apps.MemoryServiceAppConfig",
    "api_service.apps.ApiServiceConfig",
    "speech.apps.SpeechConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        },
    },
]

ASGI_APPLICATION = "eva_backend_django.asgi.application"

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = safe_config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://127.0.0.1:3000', cast=Csv())

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
    "file://"
]

CORS_ALLOW_METHODS = [
    'DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT'
]

CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type', 'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with'
]

# ✅ 替换配置变量为标准 Django settings 成员
PINECONE_API_KEY = safe_config("PINECONE_API_KEY", default="")
PINECONE_REGION = safe_config('PINECONE_REGION', default='us-east-1')
PINECONE_MEMORY_INDEX_NAME = safe_config("PINECONE_MEMORY_INDEX_NAME", default="eva-memory")
PINECONE_RULE_INDEX_NAME = safe_config('PINECONE_RULE_INDEX_NAME', default='eva-rule')
PINECONE_INDEX_NAME = PINECONE_MEMORY_INDEX_NAME
PINECONE_DIMENSION = safe_config('PINECONE_DIMENSION', default=1024, cast=int)
PINECONE_METRIC = safe_config('PINECONE_METRIC', default='cosine')
PINECONE_CLOUD = safe_config('PINECONE_CLOUD', default='aws')

LLM_APIS = {
    "deepseek": {
        "MODEL": safe_config("DEEPSEEK_MODEL", default="deepseek-chat"),
        "BASE_URL": safe_config("DEEPSEEK_API_BASE_URL", default="https://api.deepseek.com/v1/chat/completions"),
        "API_KEY": safe_config("DEEPSEEK_API_KEY", default=""),
        "MAX_TOKENS": safe_config("DEEPSEEK_MAX_TOKENS", default=4096, cast=int),
        "TEMPERATURE": safe_config("DEEPSEEK_TEMPERATURE", default=0.7, cast=float),
    },
    "siliconflow": {
        "MODEL": safe_config("SILICONFLOW_MODEL", default="deepseek-ai/DeepSeek-V3"),
        "BASE_URL": safe_config("SILICONFLOW_API_BASE_URL", default="https://api.siliconflow.cn/v1/chat/completions"),
        "API_KEY": safe_config("SILICONFLOW_API_KEY", default=""),
        "MAX_TOKENS": safe_config("SILICONFLOW_MAX_TOKENS", default=4096, cast=int),
        "TEMPERATURE": safe_config("SILICONFLOW_TEMPERATURE", default=0.7, cast=float),
    },
}

DATABASE_URL = safe_config('DATABASE_URL', default='sqlite:///db.sqlite3')
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
}

REDIS_HOST = os.environ.get('REDIS_HOST') or safe_config('REDIS_HOST', default='eva-redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT') or safe_config('REDIS_PORT', default=6379, cast=int))
REDIS_DB = int(os.environ.get('REDIS_DB') or safe_config('REDIS_DB', default=0, cast=int))

MEMORY_BACKEND = safe_config('MEMORY_BACKEND', default='pinecone')
HUGGINGFACE_EMBEDDING_MODEL = safe_config('HUGGINGFACE_EMBEDDING_MODEL', default='sentence-transformers/all-mpnet-base-v2')

SESSION_EXPIRATION_HOURS = safe_config("SESSION_EXPIRATION_HOURS", default=24, cast=int)

AI_CONFIG_FILE = BASE_DIR / "config" / "ai_settings.yaml"
AI_SETTINGS_FILE = safe_config('AI_SETTINGS_FILE', default='ai_settings.yaml')
PROMPT_SETTINGS_FILE = safe_config('PROMPT_SETTINGS_FILE', default='prompt_settings.yaml')

MEDIA_URL = str(safe_config('MEDIA_URL', default='/media/'))
MEDIA_ROOT = Path(str(safe_config('MEDIA_ROOT', default='/app/media')))
TTS_OUTPUT_DIR = Path(str(safe_config('TTS_OUTPUT_DIR', default='/app/media/tts_output')))
USE_CHAT_TTS = safe_config("USE_CHAT_TTS", default=True, cast=bool)
TTS_URL_PREFIX = f"{MEDIA_URL}tts_output/"

MEMORY_CONSOLIDATION_HOURS = safe_config('MEMORY_CONSOLIDATION_HOURS', default=24, cast=int)
MEMORY_RETENTION_THRESHOLD = safe_config('MEMORY_RETENTION_THRESHOLD', default=0.6, cast=float)
MEMORY_CLEANUP_BATCH_SIZE = safe_config('MEMORY_CLEANUP_BATCH_SIZE', default=100, cast=int)
MEMORY_SYNAPTIC_STRENGTHEN_RATE = safe_config('MEMORY_SYNAPTIC_STRENGTHEN_RATE', default=1.2, cast=float)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
APPEND_SLASH = False

os.makedirs(str(MEDIA_ROOT), exist_ok=True)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
os.makedirs(str(TTS_OUTPUT_DIR), exist_ok=True)
TTS_URL_PREFIX = TTS_URL_PREFIX
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 注释 debug_toolbar 相关配置，避免模板渲染报错
# if 'debug_toolbar' in INSTALLED_APPS:
#     INSTALLED_APPS.remove('debug_toolbar')
# if 'debug_toolbar.middleware.DebugToolbarMiddleware' in MIDDLEWARE:
#     MIDDLEWARE.remove('debug_toolbar.middleware.DebugToolbarMiddleware')

MEMORY_SYSTEM_CONFIG = {
    "LLM_MODE": "logic_layer",
    "MAX_CONCURRENT_PROCESSING": 100,
    "EMOTION_CACHE_TTL": 3600
}

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULE = {
    'clean-tts-files': {
        'task': 'speech.tasks.clean_tts_files',
        'schedule': crontab(hour="0", minute="0"),
    },
    'clean-expired-memories-every-day': {
        'task': 'memory_service_app.tasks.clean_expired_memories',
        'schedule': crontab(hour="0", minute="0"),
    },
}

if DEBUG:
    logger.system(f"TTS_OUTPUT_DIR: {TTS_OUTPUT_DIR}, MEDIA_ROOT: {MEDIA_ROOT}")

# 自动创建日志目录，避免日志写入报错
os.makedirs('/app/logfiles', exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/app/logfiles/django.log',
            'formatter': 'verbose',
            'level': 'DEBUG',
            'mode': 'w',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'channels': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'channels_layers': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'llm_manager_app': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'channels_redis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'logs': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Channels 配置
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

WHITENOISE_ALLOW_ALL_ORIGINS = True
WHITENOISE_ROOT = str(MEDIA_ROOT)

# 读取 OpenAI API Key（可用于全局配置）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # 从环境变量读取OpenAI密钥
