# EVA_backend/prompts/generator.py

import json
import random
from datetime import datetime
from typing import Dict, List, Optional
from .default_prompts import (
    DEFAULT_SYSTEM_PROMPT,
    MEMORY_PROMPT_TEMPLATE,
    CONVERSATION_HISTORY_TEMPLATE,
    LANGUAGE_EXAMPLES
)


class PromptGenerator:
    """EVA 的提示词生成器"""

    def __init__(self, learned_rules: List[str] = None) -> None:
        # 初始时可以传入学习的规则
        self.constraints = []
        self.capabilities = []
        self.memory_context = []
        self.conversation_history = []
        self.user_info = {}  # 【新增】用于存储用户的动态信息（如姓名、偏好等）
        self.name = "EVA"
        self.role = "AI Assistant"
        self.learned_rules = learned_rules if learned_rules else []  # 【新增】存储用户的学习规则
        # 添加情感表达和个性化元素
        self.greeting_templates = [
            "很高兴又见到你",
            "希望你今天过得愉快",
            "有什么我能帮你的？",
            "又见面啦",
            "日安",
            "你好啊"
        ]
        self.time_greetings = {
            "morning": ["早上好", "早安", "美好的早晨"],
            "afternoon": ["下午好", "午后好时光"],  
            "evening": ["晚上好", "夜晚愉快"],
            "night": ["夜深了", "晚安时光"]
        }
        
    def add_constraint(self, constraint: str) -> None:
        """添加约束条件"""
        self.constraints.append(constraint)
        
    def add_capability(self, capability: str) -> None:
        """添加能力描述"""
        self.capabilities.append(capability)
        
    def add_memory(self, memory: str) -> None:
        """添加记忆上下文"""
        self.memory_context.append(memory)
        
    def add_conversation(self, conversation: str) -> None:
        """添加对话历史"""
        self.conversation_history.append(conversation)
    
    def add_user_info(self, key: str, value: str) -> None:
        """【新增】添加用户信息（如姓名、偏好等）"""
        self.user_info[key] = value
        
    def add_learned_rule(self, rule: str) -> None:
        """【新增】添加新的学习规则"""
        self.learned_rules.append(rule)
        
    def _get_time_based_greeting(self) -> str:
        """根据当前时间生成适合的问候语"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            greetings = self.time_greetings["morning"]
        elif 12 <= hour < 18:
            greetings = self.time_greetings["afternoon"]
        elif 18 <= hour < 22:
            greetings = self.time_greetings["evening"]
        else:
            greetings = self.time_greetings["night"]
            
        return random.choice(greetings)
    
    def _generate_personalized_intro(self) -> str:
        """生成简洁的个性化介绍语（去除动作、表情、拟人化）"""
        intro_parts = []
        # 仅添加时间问候
        time_greeting = self._get_time_based_greeting()
        intro_parts.append(time_greeting)
        # 如有用户名，仅加称呼
        if self.user_info.get("name"):
            name_greeting = f"{self.user_info.get('name')}"
            intro_parts.append(name_greeting)
        else:
            intro_parts.append(random.choice(self.greeting_templates))
        # 不再添加任何偏好、动作、表情等描述
        return "，".join(intro_parts) + "。"
        
    def generate_prompt_string(self, user_message: str) -> str:
        """生成完整的提示词（去除动作、表情、拟人化引导）"""
        language = self._detect_language(user_message)
        current_datetime = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        personalized_intro = self._generate_personalized_intro()
        # 只保留自然问候和系统 prompt，不引导任何动作或表情
        prompt = f"当前时间是 {current_datetime}。\n{personalized_intro}\n" + DEFAULT_SYSTEM_PROMPT.format(
            LANGUAGE_EXAMPLES=LANGUAGE_EXAMPLES[language]
        )
        if self.conversation_history:
            prompt += "\n" + CONVERSATION_HISTORY_TEMPLATE.format(
                conversation_history=self._format_history()
            )
        if self.memory_context:
            prompt += "\n" + MEMORY_PROMPT_TEMPLATE.format(
                memory_context=self._format_memory()
            )
        if self.constraints or self.capabilities:
            prompt += "\n当前约束和能力：\n"
            prompt += self._format_constraints_and_capabilities()
        if self.learned_rules:
            prompt += "\n用户学习的规则：\n"
            prompt += self._format_learned_rules()
        prompt += f"\n用户: {user_message}\nEVA: "
        return prompt

    def _detect_language(self, text: str) -> str:
        """简单的语言检测"""
        if any('\u4e00-\u9fff' in char for char in text):
            return "中文"
        elif any('\u3040-\u30ff' in char for char in text):
            return "日本語"
        return "English"

    def _format_history(self) -> str:
        """格式化对话历史"""
        return "\n".join(self.conversation_history[-6:])  # 保留最近3轮对话
        
    def _format_memory(self) -> str:
        """修复记忆格式化方法"""
        # 新增测试数据过滤
        filtered_memories = [
            m for m in self.memory_context[-3:] 
            if not any(keyword in m for keyword in ["测试", "示例", "sample"])
        ]
        return "\n".join(filtered_memories)
        
    def _format_constraints_and_capabilities(self) -> str:
        """格式化约束和能力"""
        result = []
        if self.constraints:
            result.append("约束条件：")
            result.extend([f"- {c}" for c in self.constraints])
        if self.capabilities:
            if result:
                result.append("")
            result.append("能力：")
            result.extend([f"- {c}" for c in self.capabilities])
        return "\n".join(result)
    
    def _format_learned_rules(self) -> str:
        """格式化用户学习的规则"""
        return "\n".join([f"- {rule}" for rule in self.learned_rules])
