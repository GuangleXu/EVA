"""Second-Me工作记忆适配器

该适配器将Second-Me的L1层功能适配到EVA的工作记忆接口。
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union

# EVA导入
# from ..working_term_memory.working_term_memory import BaseWorkingTermMemory
from logs.logs import logger
from .config import load_config

# Second-Me导入
try:
    # 尝试导入Second-Me的模块
    from lpm_kernel.L1.l1_generator import L1Generator
    from lpm_kernel.L0.l0_generator import L0Generator
    
    SECOND_ME_IMPORTED = True
except ImportError as e:
    logger.warning(f"Second-Me导入失败: {e}")
    SECOND_ME_IMPORTED = False

# 强制指定F盘路径，彻底绕过config
config = load_config()
DATA_PATH = config.get("data_path", "/app/data")
CONVERSATION_FILE_PATH = os.path.join(DATA_PATH, "conversations", "history.json")

def _load_conversations():
    """加载所有对话历史（本地JSON文件）"""
    if not os.path.exists(CONVERSATION_FILE_PATH):
        return []
    try:
        with open(CONVERSATION_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载对话历史文件失败: {str(e)}")
        return []

def _save_conversations(conversations):
    logger.info(f"[DEBUG][working_memory_adapter] _save_conversations 被调用，conversations 长度: {len(conversations)}，内容预览: {str(conversations)[:200]}")
    os.makedirs(os.path.dirname(CONVERSATION_FILE_PATH), exist_ok=True)
    try:
        with open(CONVERSATION_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        logger.info(f"[DEBUG][working_memory_adapter] 写入成功: {CONVERSATION_FILE_PATH}")
    except Exception as e:
        logger.warning(f"[DEBUG][working_memory_adapter] 保存对话历史文件失败: {str(e)}")
        print(f"[DEBUG][working_memory_adapter] 写入异常: {e}")

class SecondMeWorkingMemoryAdapter:
    """适配Second-Me的工作记忆系统到EVA接口"""
    
    def __init__(self):
        """初始化Second-Me工作记忆适配器"""
        self.initialized = False
        self.l1_generator = None
        self.l0_generator = None
        self.conversation_history = []
        self.lock = asyncio.Lock()
        self.max_history_length = 20  # 最大对话历史长度
        
        # 检查Second-Me是否可用
        if not SECOND_ME_IMPORTED:
            logger.warning("Second-Me模块未成功导入，部分功能可能不可用")
    
    async def initialize(self):
        """初始化Second-Me的工作记忆组件（本地JSON实现）"""
        if self.initialized:
            return
        async with self.lock:
            if self.initialized:
                return
            try:
                logger.info("[SecondMeWorkingMemoryAdapter] 正在初始化Second-Me工作记忆组件...")
                os.makedirs("data/conversations", exist_ok=True)
                self.conversation_history = _load_conversations()
                logger.info(f"[SecondMeWorkingMemoryAdapter] 加载了 {len(self.conversation_history)} 条对话历史")
                self.initialized = True
            except Exception as e:
                logger.error(f"[SecondMeWorkingMemoryAdapter] 初始化失败: {str(e)}")
                raise RuntimeError(f"无法初始化Second-Me工作记忆系统: {str(e)}")
    
    def ensure_initialized(self):
        """确保组件已初始化"""
        if not self.initialized:
            raise RuntimeError("Second-Me工作记忆适配器尚未初始化")
    
    def _extract_entities_relations_tags(self, text: str):
        """
        简单实体、关系、标签抽取（可扩展为L0/L1层调用）
        返回：entities, relations, tags
        """
        entities = []
        relations = []
        tags = []
        import re
        match = re.match(r"(我|小明|小红)?(喜欢|讨厌|需要|拥有|吃|喝|去|看|玩|学|买|用)(.+)", text)
        if match:
            subject = match.group(1) or "我"
            predicate = match.group(2)
            obj = match.group(3).strip()
            entities = [subject, obj]
            relations = [{"subject": subject, "predicate": predicate, "object": obj}]
            tags = [predicate]
        return entities, relations, tags

    async def add_message(self, human_message: str, ai_message: str) -> Dict[str, Any]:
        logger.debug(f"【DEBUG】已进入 add_message，human_message: {human_message}, ai_message: {ai_message}")
        await self.initialize()
        self.ensure_initialized()
        try:
            processed_human = await self._process_with_l0(human_message)
            processed_ai = await self._process_with_l0(ai_message)
            # 优先用L0/L1深度语义分析
            entities, relations, tags, interests, events = [], [], [], [], []
            try:
                if hasattr(self, 'l0_generator') and self.l0_generator:
                    l0_result = await self.l0_generator.process_text(human_message)
                    entities = l0_result.get("entities", [])
                    tags = l0_result.get("tags", [])
                if hasattr(self, 'l1_generator') and self.l1_generator:
                    l1_result = await self.l1_generator.analyze_text(human_message)
                    relations = l1_result.get("relations", [])
                    interests = l1_result.get("interests", [])
                    events = l1_result.get("events", [])
            except Exception as l_err:
                logger.warning(f"[SecondMeWorkingMemoryAdapter] L0/L1分析失败，回退正则: {str(l_err)}")
                entities, relations, tags = self._extract_entities_relations_tags(human_message)
            turn = {
                "human": {
                    "raw": human_message,
                    "processed": processed_human.get("processed_text", human_message),
                    "entities": entities,
                    "relations": relations,
                    "tags": tags,
                    "interests": interests,
                    "events": events
                },
                "ai": {
                    "raw": ai_message,
                    "processed": processed_ai.get("processed_text", ai_message)
                },
                "timestamp": self._get_timestamp()
            }
            self.conversation_history.append(turn)
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
            _save_conversations(self.conversation_history)
            try:
                analysis = await self._analyze_with_l1(human_message, ai_message)
                logger.debug(f"[SecondMeWorkingMemoryAdapter] L1层分析结果: {str(analysis)[:100]}...")
            except Exception as analysis_error:
                logger.warning(f"[SecondMeWorkingMemoryAdapter] L1层分析失败: {str(analysis_error)}")
            logger.info(f"[SecondMeWorkingMemoryAdapter] 成功添加对话到工作记忆，实体: {entities}，关系: {relations}，标签: {tags}，兴趣: {interests}，事件: {events}")
            # 返回标准格式
            return {
                "role": "user",
                "content": human_message,
                "metadata": {"ai_reply": ai_message, "timestamp": turn["timestamp"], "entities": entities, "relations": relations, "tags": tags, "interests": interests, "events": events}
            }
        except Exception as e:
            logger.error(f"[SecondMeWorkingMemoryAdapter] 添加对话失败: {str(e)}")
            # 返回标准格式，标记失败
            return {
                "role": "user",
                "content": human_message,
                "metadata": {"ai_reply": ai_message, "error": str(e)}
            }
    
    async def get_messages(self, query: str = None, top_k: int = 5) -> list:
        """
        检索工作记忆：
        - 仅用内容、标签、规则、优先级等多维条件
        - 完全忽略 embedding
        - 返回标准格式
        """
        await self.initialize()
        self.ensure_initialized()
        try:
            all_msgs = self._load_messages()
            results = []
            if query:
                query_lower = query.lower()
                for msg in all_msgs:
                    content = msg.get('content', '').lower()
                    meta = msg.get('metadata', {})
                    tags = meta.get('tags', [])
                    if query_lower in content or any(query_lower in str(tag).lower() for tag in tags):
                        results.append(msg)
            else:
                results = all_msgs
            # 按优先级、时间排序
            def sort_key(msg):
                meta = msg.get('metadata', {})
                priority = float(meta.get('priority', 0.5))
                ts = meta.get('timestamp', '')
                try:
                    from datetime import datetime
                    t = datetime.fromisoformat(ts) if ts else None
                except Exception:
                    t = None
                return (-priority, -(t.timestamp() if t else 0))
            results = sorted(results, key=sort_key)
            return results[:top_k]
        except Exception as e:
            logger.error(f"[SecondMeWorkingMemoryAdapter] 检索工作记忆失败: {str(e)}")
            return []
    
    async def clear_messages(self) -> Dict[str, Any]:
        """清空工作记忆中的所有对话消息，返回标准格式"""
        await self.initialize()
        self.ensure_initialized()
        try:
            logger.info(f"【DEBUG】调用 clear_messages，目标路径: {CONVERSATION_FILE_PATH}")
            backup_dir = os.path.join(DATA_PATH, "conversations")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, "history_backup.json")
            try:
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
                    logger.info(f"[SecondMeWorkingMemoryAdapter] 对话历史已备份到 {backup_path}")
            except Exception as backup_error:
                logger.warning(f"[SecondMeWorkingMemoryAdapter] 备份对话历史失败: {str(backup_error)}")
            self.conversation_history = []
            _save_conversations(self.conversation_history)
            logger.info("[SecondMeWorkingMemoryAdapter] 成功清空工作记忆")
            return {
                "role": "system",
                "content": "",
                "metadata": {"cleared": True}
            }
        except Exception as e:
            logger.error(f"[SecondMeWorkingMemoryAdapter] 清空工作记忆失败: {str(e)}")
            return {
                "role": "system",
                "content": "",
                "metadata": {"cleared": False, "error": str(e)}
            }
    
    async def summarize(self) -> Dict[str, Any]:
        """生成工作记忆中对话的摘要，返回标准格式"""
        await self.initialize()
        self.ensure_initialized()
        if not self.conversation_history:
            return {
                "role": "system",
                "content": "无对话历史",
                "metadata": {"summary": "工作记忆为空"}
            }
        try:
            history_text = "\n".join([
                f"Human: {turn.get('human', {}).get('raw', '')}\nAI: {turn.get('ai', {}).get('raw', '')}"
                for turn in self.conversation_history
            ])
            if self.l1_generator:
                summary_result = await self.l1_generator.generate_conversation_summary(history_text)
                summary = summary_result.get("summary", "无法生成摘要")
            else:
                summary = f"对话历史包含 {len(self.conversation_history)} 个回合"
            logger.info(f"[SecondMeWorkingMemoryAdapter] 生成摘要: {summary[:100]}...")
            return {
                "role": "system",
                "content": summary,
                "metadata": {"summary": summary}
            }
        except Exception as e:
            logger.error(f"[SecondMeWorkingMemoryAdapter] 生成摘要失败: {str(e)}")
            return {
                "role": "system",
                "content": f"摘要生成失败: {str(e)}",
                "metadata": {"error": str(e)}
            }
    
    def _save_conversation_history(self):
        """保存对话历史到文件"""
        try:
            logger.info(f"【DEBUG】调用 _save_conversation_history，目标路径: {CONVERSATION_FILE_PATH}")
            backup_dir = os.path.join(DATA_PATH, "conversations")
            os.makedirs(backup_dir, exist_ok=True)
            with open(CONVERSATION_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
                logger.debug("[SecondMeWorkingMemoryAdapter] 对话历史已保存")
        except Exception as e:
            logger.warning(f"[SecondMeWorkingMemoryAdapter] 保存对话历史失败: {str(e)}")
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def _process_with_l0(self, text: str) -> Dict[str, Any]:
        """使用Second-Me的L0层处理文本
        
        Args:
            text: 要处理的文本
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 使用L0Generator处理文本
            if self.l0_generator:
                result = await self.l0_generator.process_text(text)
                return result
            else:
                return {"processed_text": text, "text": text}
        except Exception as e:
            logger.warning(f"[SecondMeWorkingMemoryAdapter] L0处理失败，使用简单处理: {str(e)}")
            # 失败时使用简单处理
            return {"processed_text": text, "text": text}
    
    async def _analyze_with_l1(self, human_message: str, ai_message: str) -> Dict[str, Any]:
        """使用Second-Me的L1层分析对话
        
        Args:
            human_message: 用户消息
            ai_message: AI回复消息
            
        Returns:
            Dict: 分析结果
        """
        try:
            # 使用L1Generator分析对话
            if self.l1_generator:
                conversation = f"Human: {human_message}\nAI: {ai_message}"
                result = await self.l1_generator.analyze_conversation(conversation)
                return result
            else:
                return {}
        except Exception as e:
            logger.warning(f"[SecondMeWorkingMemoryAdapter] L1分析失败: {str(e)}")
            return {}

    async def add_conversation(self, user_text: str, ai_text: str) -> dict:
        """兼容测试用例，添加一轮对话，返回标准格式"""
        await self.initialize()
        self.conversation_history.append({"user": user_text, "ai": ai_text})
        _save_conversations(self.conversation_history)
        return {
            "role": "user",
            "content": user_text,
            "metadata": {"ai_reply": ai_text}
        }

    async def get_conversation_history(self) -> list:
        """兼容测试用例，获取全部对话历史，返回标准格式"""
        await self.initialize()
        # 返回标准格式
        result = []
        for turn in self.conversation_history:
            result.append({
                "role": "user",
                "content": turn.get("human", {}).get("raw", turn.get("user", "")),
                "metadata": {"timestamp": turn.get("timestamp", "")}
            })
            result.append({
                "role": "assistant",
                "content": turn.get("ai", {}).get("raw", turn.get("ai", "")),
                "metadata": {"timestamp": turn.get("timestamp", "")}
            })
        return result

    async def add_messages(self, messages: list = None, *args, **kwargs) -> None:
        logger.debug(f"【DEBUG】已进入 add_messages，messages: {messages}")
        if messages is None:
            messages = []
        for msg in messages:
            if isinstance(msg, dict):
                human = msg.get("human") or msg.get("user") or msg.get("content") or ""
                ai = msg.get("ai") or msg.get("assistant") or msg.get("response") or ""
            else:
                human = getattr(msg, "human", getattr(msg, "user", getattr(msg, "content", "")))
                ai = getattr(msg, "ai", getattr(msg, "assistant", getattr(msg, "response", "")))
            await self.add_message(human, ai)

    # 示例规则方法
    async def get_rules(self, limit: int = 5) -> list:
        """返回规则对象列表，每条为RuleObj，含content/role/metadata/page_content属性"""
        rules = []
        for i in range(limit):
            rule = self.RuleObj()
            rule.content = f"规则内容{i+1}"
            rule.role = "rule"
            rule.metadata = {"priority": 100}
            rule.page_content = f"规则内容{i+1}"
            rules.append(rule)
        return rules

    async def load_memory_variables(self, inputs: dict = None) -> dict:
        """兼容EVA主流程，返回标准chat_history对象列表"""
        await self.initialize()
        self.ensure_initialized()
        limit = 5
        if inputs and isinstance(inputs, dict):
            limit = inputs.get("limit", 5)
        history = self.conversation_history[-limit:] if limit > 0 else self.conversation_history
        chat_history = []
        for turn in history:
            chat_history.append({
                "role": "user",
                "content": turn.get("human", {}).get("raw", turn.get("user", "")),
                "metadata": {"timestamp": turn.get("timestamp", "")}
            })
            chat_history.append({
                "role": "assistant",
                "content": turn.get("ai", {}).get("raw", turn.get("ai", "")),
                "metadata": {"timestamp": turn.get("timestamp", "")}
            })
        return {"chat_history": chat_history} 