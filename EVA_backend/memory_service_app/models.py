from django.db import models
from typing import Optional

class Memory(models.Model):
    """
    Memory 模型表示一个记忆项，用于存储和管理长期记忆。
    
    属性:
        id: 主键，自动生成
        content: 记忆内容
        timestamp: 创建时间
        metadata: 元数据信息
    """
    id = models.AutoField(primary_key=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self) -> str:
        """
        返回记忆对象的字符串表示
        
        Returns:
            str: 格式为 "Memory {id} - {timestamp}" 的字符串
        """
        return f"Memory {self.id} - {self.timestamp}"
