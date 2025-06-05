# EVA_backend/memory_service_app/utils/central_executive.py
"""
EVA 记忆系统中央执行控制器（CentralExecutive）

【定位说明】
本模块是 EVA 智能体的"大总管"，负责调度和整合所有记忆类型，并为大模型（LLM）拼接最终上下文。

【SecondMe 深度集成后的职责】
1. 只使用 SecondMe 记忆系统（长期、工作、规则），所有记忆操作均通过 SecondMe 适配器实现。
2. 负责初始化和调用各类 SecondMe 适配器，彻底移除原生 EVA 记忆模块。
3. 负责对用户输入进行优先级、类型判定，并分流到不同记忆适配器进行存储、检索、合并。
4. 负责将 SecondMe 检索到的多类型记忆（兴趣、规则、历史事件、最近对话等）结构化拼接为 LLM 可用的上下文字符串（final_context）。
5. 负责异常处理、日志记录、记忆决策等全局调度逻辑。

【与 SecondMe 的关系】
- SecondMe 负责"结构化记忆的存储与检索"，但不负责"多类型记忆的上下文拼接"。
- CentralExecutive 负责把 SecondMe 返回的各类记忆，按对话场景需求拼成 LLM prompt，实现"有记忆的智能体对话"。

【最佳实践】
- 保留中控器的"调度+拼接"功能，所有记忆相关操作全部走 SecondMe 适配器。
- 这样既保证架构清晰，也方便未来升级和维护。

【注意】
- 本文件已彻底移除原生 EVA 记忆相关代码，仅保留 SecondMe 适配器。
- 如需扩展其它记忆系统，只需新增适配器并在此处统一调度。

"""

import os
import sys
import asyncio
from typing import Dict, Optional
# import logging

# 添加项目根目录到系统路径
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 项目导入
from logs.logs import logger

# LLM服务导入
try:
    from llm_manager_app.utils.llm_service import llm_service
except ImportError:
    logger.warning("无法导入llm_service，可能需要配置正确的Python路径")
    llm_service = None

# Second-Me分类适配器导入
try:
    from .memory_classifier_adapter import MemoryClassifierAdapter
    SECONDME_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入MemoryClassifierAdapter: {e}")
    SECONDME_AVAILABLE = False


class BaseMemoryModule:
    def __init__(self):
        self.initialized = False

    def ensure_initialized(self):
        if not self.initialized:
            raise RuntimeError(f"{self.__class__.__name__} 未初始化")

    async def initialize(self):
        pass


class CentralExecutive(BaseMemoryModule):
    """记忆系统的中央执行控制器"""

    def __init__(self):
        super().__init__()
        logger.info("[CentralExecutive] 初始化中...")

        self.llm_service = llm_service

        # 初始化 SecondMe 适配器
        self.memory_adapter = MemoryClassifierAdapter()

        self.memory_lock = asyncio.Lock()
        self.initialized = True

        logger.info("[CentralExecutive] 初始化完成")

    async def process_input(self, raw_input: str) -> Optional[Dict]:
        logger.info(f"[DEBUG][central_executive.process_input] 被调用，raw_input: {raw_input}")
        try:
            # 1. 直接处理原始输入
            processed = {"clean_text": raw_input}
            logger.info(f"[DEBUG][central_executive.process_input] 感知处理结果: {processed}")
            if not processed:
                logger.warning("[CentralExecutive] 感知处理结果为空")
                return {"stage": "short_term", "reason": "input_empty", "input": raw_input}

            # 2. 通过 MemoryClassifierAdapter 添加记忆
            add_result = await self.memory_adapter.add_memory(processed["clean_text"])
            logger.info(f"[CentralExecutive] 已保存记忆: {processed['clean_text'][:30]}... 结果: {add_result}")
            store_result = {
                "status": "stored",
                "adapter_result": add_result
            }
            return {"stage": "memory_stored", "result": store_result}
        except Exception as e:
            logger.error(f"[CentralExecutive] 处理输入失败: {str(e)}")
            return {"stage": "error", "error": str(e)}

    async def initialize(self):
        """初始化记忆组件"""
        if self.initialized:
            return
        logger.info("[CentralExecutive] 开始初始化记忆组件...")
        if SECONDME_AVAILABLE:
            await self.memory_adapter.initialize()
        self.initialized = True
        logger.info("[CentralExecutive] 记忆组件初始化完成")

# ✅ 全局实例
central_executive = CentralExecutive()
