FROM python:3.12-slim

ENV TZ=Asia/Shanghai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git \
    python3-dev \
    gcc \
    supervisor \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.7.1 -i https://pypi.mirrors.ustc.edu.cn/simple

WORKDIR /app