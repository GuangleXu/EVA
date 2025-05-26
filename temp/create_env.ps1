# 创建.env文件脚本
# 使用方法：在PowerShell中运行 .\temp\create_env.ps1

$envContent = @"
# EVA 后端环境变量配置

# Django 配置
DEBUG=True
SECRET_KEY=django-insecure-development-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DJANGO_SETTINGS_MODULE=eva_backend_django.settings

# 数据库配置
DATABASE_URL=postgres://postgres@db:5432/eva_db

# Redis 配置
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Pinecone 向量数据库配置
PINECONE_API_KEY=5c190a0f-50bc-47c4-ad83-8eea0dd8185b
PINECONE_ENVIRONMENT=us-east-1-aws
PINECONE_MEMORY_INDEX_NAME=eva-memory
PINECONE_RULE_INDEX_NAME=eva-rule
PINECONE_TEXT_KEY=text
PINECONE_DIMENSION=1024
PINECONE_METRIC=cosine
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# LLM 配置
LLM_MODEL=deepseek
LLM_API_KEY=your-llm-api-key-here
LLM_API_BASE_URL=https://api.deepseek.com/v1

# 日志配置
LOG_LEVEL=DEBUG
LOG_DIR=/app/logfiles

# 存储路径配置
MEDIA_ROOT=/app/media

# 系统配置
PYTHONPATH=/app
PYTHONIOENCODING=utf-8
LANG=C.UTF-8
"@

# 创建目录（如果不存在）
if (-not (Test-Path -Path "EVA_backend\logfiles")) {
    New-Item -Path "EVA_backend\logfiles" -ItemType Directory -Force
}

# 创建目录（如果不存在）
if (-not (Test-Path -Path "EVA_backend\media")) {
    New-Item -Path "EVA_backend\media" -ItemType Directory -Force
}

# 写入环境变量文件
$envContent | Out-File -FilePath "EVA_backend\.env" -Encoding utf8 -NoNewline

Write-Host ".env 文件创建成功！路径：EVA_backend\.env" -ForegroundColor Green
Write-Host "已创建必要的日志和媒体目录" -ForegroundColor Green 