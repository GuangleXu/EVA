from typing import Optional, Dict, Any
from .generator import PromptGenerator
from .default_prompts import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TASK_PROMPT,
    LANGUAGE_EXAMPLES
)

async def build_eva_prompt(
    user_message: str, 
    conversation_history: Optional[str] = None, 
    memory_context: Optional[str] = None,
    user_info: Optional[Dict[str, Any]] = None
) -> str:
    """构建 EVA 的完整提示词，增强个性化和自然度
    
    Args:
        user_message: 用户的当前消息
        conversation_history: 对话历史
        memory_context: 记忆上下文
        user_info: 用户信息字典，包含姓名、偏好等
    
    Returns:
        完整的提示词字符串
    """
    
    generator = PromptGenerator()
    
    # 添加用户信息以增强个性化
    if user_info:
        # 用户信息已经扁平化处理
        for key, value in user_info.items():
            generator.add_user_info(key, value)
    
    # 添加对话历史
    if conversation_history:
        generator.add_conversation(conversation_history)
    
    # 添加记忆上下文
    if memory_context:
        generator.add_memory(memory_context)
    
    # 生成最终提示词
    return generator.generate_prompt_string(user_message)