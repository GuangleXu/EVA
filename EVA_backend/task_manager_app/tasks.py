import asyncio
from celery import Celery
from logs.logs import logger
from memory_service_app.utils import (
    MemoryOptimizer,
    memory_manager,
    index_manager
)

# 初始化Celery
app = Celery('task_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')

@app.task
def memory_maintenance():
    """包装异步任务的同步接口"""
    asyncio.run(async_memory_maintenance())

async def async_memory_maintenance():
    """异步记忆维护任务"""
    try:
        optimizer = MemoryOptimizer()
        
        logger.system("🔄 开始执行记忆维护任务...")
        
        # 执行记忆优化流程
        await optimizer.consolidate_memories()
        await memory_manager.clean_expired_memories()
        
        # 执行索引优化
        await index_manager.optimize_index()
        
        logger.success("✅ 记忆维护任务完成")
        
    except Exception as e:
        logger.error(f"记忆维护任务失败: {e}")
        raise

# 配置Celery定时任务
app.conf.beat_schedule = {
    'daily-memory-maintenance': {
        'task': 'task_manager_app.tasks.memory_maintenance',
        'schedule': 86400.0,  # 24小时
        'options': {'timezone': 'Asia/Shanghai'}
    },
} 