# EVA_backend/memory_service_app/tasks.py

from celery import shared_task

# 定义一个异步任务
@shared_task
def clean_expired_memories():
    # 清理过期的记忆数据
    print("Cleaning expired memories...")