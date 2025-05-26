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
import json
from typing import List, Dict, Optional, Any
# import logging

# 添加项目根目录到系统路径
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 核心导入

# 尝试不同的导入路径
try:
    from langchain_community.memory import ConversationBufferMemory
except ImportError:
    try:
        from langchain.memory import ConversationBufferMemory
    except ImportError:
        ConversationBufferMemory = object
        print("警告: 无法导入ConversationBufferMemory")

try:
    from langchain_community.chains import ConversationalRetrievalChain
except ImportError:
    try:
        from langchain.chains import ConversationalRetrievalChain
    except ImportError:
        ConversationalRetrievalChain = object
        print("警告: 无法导入ConversationalRetrievalChain")

# 项目导入
from logs.logs import logger

# LLM服务导入
try:
    from llm_manager_app.utils.llm_service import llm_service
except ImportError:
    logger.warning("无法导入llm_service，可能需要配置正确的Python路径")
    llm_service = None

# 记忆服务导入 - 原始模块
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Second-Me适配器导入（分文件存储，彻底去除 adapter.py 相关引用）
try:
    from .secondme_integration.memory_adapter import SecondMeMemoryAdapter as get_secondme_long_term_adapter
    from .secondme_integration.working_memory_adapter import SecondMeWorkingMemoryAdapter as get_secondme_working_adapter
    from .secondme_integration.rule_adapter import SecondMeRuleAdapter as get_secondme_rule_adapter
    SECONDME_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入Second-Me适配器: {e}")
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

        # 只使用 SecondMe 适配器，变量命名全部适配器风格
        if SECONDME_AVAILABLE:
            logger.info("[CentralExecutive] 使用Second-Me集成模式（适配器命名风格）")
            self.secondme_long_term_adapter = get_secondme_long_term_adapter()
            self.secondme_rule_adapter = get_secondme_rule_adapter()
            self.secondme_working_adapter = get_secondme_working_adapter()
        else:
            raise RuntimeError("当前仅支持 SecondMe 记忆链路，原生 EVA 记忆已移除")

        self.memory_lock = asyncio.Lock()
        self.initialized = True

        logger.info("[CentralExecutive] 初始化完成")

    async def process_input(self, raw_input: str) -> Optional[Dict]:
        logger.info(f"[DEBUG][central_executive.process_input] 被调用，raw_input: {raw_input}")
        try:
            # 1. 通过感知缓冲区处理原始输入
            processed = await self.sensory_buffer.process_input(raw_input)
            logger.info(f"[DEBUG][central_executive.process_input] 感知处理结果: {processed}")
            if not processed:
                logger.warning("[CentralExecutive] 感知处理结果为空")
                return {"stage": "short_term", "reason": "sensory_buffer_empty", "input": raw_input}

            # 2. 分类决策：调用 memory_decision.categorize_memory
            categorize_result = await self.memory_decision.categorize_memory(processed)
            logger.info(f"[DEBUG][central_executive.process_input] 分类决策结果: {categorize_result}")
            memory_type = categorize_result.get("memory_type", "shortterm")
            processed["priority"] = categorize_result.get("priority", 0.5)
            logger.info(f"[DEBUG][central_executive.process_input] memory_type: {memory_type}, processed: {processed.get('clean_text', '')[:50]}")

            # 3. 根据分类分流到不同适配器
            logger.info(f"[DEBUG][central_executive.process_input] 分流决策后，memory_type={memory_type}，clean_text={processed.get('clean_text', '')[:50]}")
            if memory_type == "rule":
                logger.info("[CentralExecutive] 判定为规则记忆，进入规则处理流程")
                result = await self._process_rule_pipeline(processed)
                logger.info(f"[DEBUG][central_executive.process_input] 规则记忆处理结果: {result}")
                return result
            elif memory_type == "longterm":
                logger.info(f"[CentralExecutive] 判定为长期记忆，准备调用 _process_long_term_memory，clean_text={processed.get('clean_text', '')[:50]}")
                result = await self._process_long_term_memory(processed)
                logger.info(f"[DEBUG][central_executive.process_input] 长期记忆处理结果: {result}")
                return result
            else:  # shortterm 或其它
                logger.info("[CentralExecutive] 判定为工作记忆，进入工作记忆流程")
                result = await self._process_working_memory_pipeline(processed)
                logger.info(f"[DEBUG][central_executive.process_input] 工作记忆处理结果: {result}")
                return result

        except Exception as e:
            logger.error(f"[CentralExecutive] 处理异常: {str(e)}", exc_info=True)
            return {
                "stage": "short_term", 
                "reason": "processing_exception", 
                "error": str(e),
                "input": raw_input
            }

    async def _process_rule_pipeline(self, processed: Dict) -> Dict:
        """处理规则流水线：检索、判断相似度、合并/更新/创建"""
        rule_content = processed['clean_text']
        rule_metadata = {
            "source": processed.get("source", "user"),
            "priority": processed.get("priority", 0.0),
            "emotion": json.dumps(processed.get("emotion_profile", {}))
        }

        # 检索相似规则
        similar_rules = await self.secondme_rule_adapter.retrieve_rules(rule_content, top_k=1)
        if similar_rules:
            top_rule = similar_rules[0]
            similarity_score = getattr(top_rule, "score", 0)
            rule_id = top_rule.metadata.get("id")

            if similarity_score >= 0.9:
                merged_text = f"{top_rule.page_content}\n---\n{rule_content}"
                result = await self.secondme_rule_adapter.update_rule(
                    rule_id=rule_id,
                    rule_text=merged_text,
                    metadata=rule_metadata
                )
                logger.info("[CentralExecutive] 已合并并更新规则")
                return {"stage": "rule_merged", "rule_id": rule_id, "success": result}

            elif similarity_score >= 0.6:
                result = await self.secondme_rule_adapter.update_rule(
                    rule_id=rule_id,
                    rule_text=rule_content,
                    metadata=rule_metadata
                )
                logger.info("[CentralExecutive] 已更新相似规则")
                return {"stage": "rule_updated", "rule_id": rule_id, "success": result}

        # 存储为新规则
        rule_id = await self.secondme_rule_adapter.store_rule(
            rule_text=rule_content, 
            metadata=rule_metadata
        )
        logger.info("[CentralExecutive] 已创建新规则")
        return {"stage": "rule_created", "rule_id": rule_id}

    async def _process_working_memory_pipeline(self, processed: Dict) -> Dict:
        """只写入工作记忆，不再做长期记忆巩固，确保 shortterm 内容只进 conversations/history.json"""
        logger.info(f"[DEBUG] secondme_working_adapter 类型: {type(self.secondme_working_adapter)}")
        if hasattr(self.secondme_working_adapter, 'add_message'):
            await self.secondme_working_adapter.add_message(
                processed.get("clean_text", ""), ""
            )
        elif hasattr(self.secondme_working_adapter, 'add_messages'):
            await self.secondme_working_adapter.add_messages(
                input_text=processed.get("clean_text", ""),
                response_text=""
            )
        else:
            logger.warning("[DEBUG] 未找到 add_message/add_messages 方法，跳过写入")
        logger.info(f"[工作记忆] 已保存短期记忆: {processed.get('clean_text','')[:30]}...")
        store_result = {
            "status": "stored",
            "session_id": getattr(self.secondme_working_adapter, 'session_id', 'unknown')
        }
        return {"stage": "short_term", "result": store_result}
    
    async def _process_long_term_memory(self, processed: Dict) -> Dict:
        """
        根据 processed 记忆，判断是否存储为长期记忆或更新已有记忆
        """
        content = processed["clean_text"]
        metadata = {
            "source": str(processed.get("source", "user")),
            "priority": float(processed.get("priority", 0.0)),
            "emotion": json.dumps(processed.get("emotion_profile", {}))
        }
        try:
            logger.info(f"[DEBUG] secondme_long_term_adapter 类型: {type(self.secondme_long_term_adapter)}")
            # 检索相似记忆
            if hasattr(self.secondme_long_term_adapter, 'retrieve_memory'):
                retrieved = await self.secondme_long_term_adapter.retrieve_memory(query=content, top_k=5)
            else:
                retrieved = []
            candidates = [doc for doc in retrieved if getattr(doc, "score", 0) > 0.7]
            logger.info(f"[长期记忆] 检索到{len(candidates)}条高相关记忆")
            if not candidates:
                # 存储为新记忆
                if hasattr(self.secondme_long_term_adapter, 'store_memory'):
                    logger.info(f"[DEBUG][central_executive._process_long_term_memory] 即将调用 store_memory，适配器类型: {type(self.secondme_long_term_adapter)}, text: {content}, metadata: {metadata}")
                    memory_id = await self.secondme_long_term_adapter.store_memory(
                        text=str(content),
                        metadata=metadata
                    )
                    logger.info(f"[DEBUG][central_executive._process_long_term_memory] store_memory 返回: {memory_id}")
                else:
                    logger.warning("[DEBUG][central_executive._process_long_term_memory] secondme_long_term_adapter 无 store_memory 方法，跳过写入")
                    memory_id = None
                logger.info(f"[长期记忆] 已存储新记忆，ID={memory_id}")
                return {"stage": "long_term_created", "memory_id": memory_id}
            top = candidates[0]
            if content.strip() != top.page_content.strip():
                merged = f"{top.page_content.strip()}\n---\n{content.strip()}"
                memory_id = top.metadata.get("id", "")
                logger.info(f"[长期记忆] 发现相似记忆，执行合并，ID={memory_id}")
                result = await self.secondme_long_term_adapter.update_memory(
                    memory_id=memory_id,
                    content=merged,
                    metadata=metadata
                )
                logger.info(f"[长期记忆] 合并并更新成功，ID={memory_id}")
                return {"stage": "long_term_updated", "result": result}
            else:
                logger.info(f"[长期记忆] 内容重复，跳过存储，ID={top.metadata.get('id','')}")
                return {"stage": "long_term_skipped", "reason": "duplicated"}
        except Exception as e:
            logger.error(f"[长期记忆] 处理异常: {e}", exc_info=True)
            return {"stage": "long_term_error", "message": str(e)}

    async def combine_context(self, user_message: str) -> Dict[str, Any]:
        # logger.debug(f"【DEBUG】已进入 combine_context，user_message: {user_message}")
        try:
            async with self.memory_lock:
                logger.info(f"[CentralExecutive] 开始组合上下文: {user_message[:50]}...")
                rules = await self._get_related_rules(user_message)
                logger.info(f"[CentralExecutive] 找到 {len(rules)} 条相关规则")
                working_memories = await self._get_working_memories(user_message)
                logger.info(f"[CentralExecutive] 找到 {len(working_memories)} 条工作记忆")
                long_term_memories = await self._get_long_term_memories(user_message)
                logger.info(f"[CentralExecutive] 找到 {len(long_term_memories)} 条长期记忆")
                # 结构化归纳兴趣、规则、事件、冲突
                interests = []
                events = []
                user_rules = []
                conflicts = []
                # 归纳长期记忆中的兴趣、事件
                for mem in long_term_memories:
                    meta = mem.get('metadata', {})
                    interests.extend(meta.get('interests', []))
                    events.extend(meta.get('events', []))
                # 归纳规则
                for rule in rules:
                    meta = rule.get('metadata', {})
                    user_rules.append(rule.get('content', ''))
                # 简单冲突检测（如同一实体有正反关系）
                like_set = set()
                dislike_set = set()
                for mem in long_term_memories:
                    for rel in mem.get('metadata', {}).get('relations', []):
                        if rel.get('predicate') in ['喜欢', '爱好']:
                            like_set.add(rel.get('object'))
                        if rel.get('predicate') in ['不喜欢', '讨厌']:
                            dislike_set.add(rel.get('object'))
                conflicts = list(like_set & dislike_set)
                # 结构化分块拼接上下文
                context_parts = []
                if interests:
                    context_parts.append("【兴趣归纳】\n" + "，".join(set(interests)))
                if user_rules:
                    context_parts.append("【规则列表】\n" + "\n".join(user_rules))
                if events:
                    context_parts.append("【历史事件】\n" + "，".join(set(events)))
                if conflicts:
                    context_parts.append("【冲突检测】\n" + "，".join(conflicts))
                # 新增：拼接所有长期记忆内容到"【相关记忆】"分块
                if long_term_memories:
                    context_parts.append("【相关记忆】\n" + "\n".join(str(m.get('content', '')) for m in long_term_memories))
                # 最近对话
                if working_memories:
                    context_parts.append("【最近对话】\n" + "\n".join(f"{msg['role']}: {msg['content']}" for msg in working_memories[-5:]))
                # 当前用户消息
                context_parts.append(f"【当前消息】\n{user_message}")
                final_context = "\n\n".join(context_parts)
                logger.info(f"[DEBUG] combine_context 输出: {final_context}")
                return {
                    "related_rules": rules,
                    "related_working_term": working_memories,
                    "related_memories": long_term_memories,
                    "final_context": final_context,
                    "system_context": "结构化记忆检索完成"
                }
        except Exception as e:
            logger.error(f"[CentralExecutive] 组合上下文失败: {e}", exc_info=True)
            return {
                "related_rules": [],
                "related_working_term": [],
                "related_memories": [],
                "final_context": "",
                "system_context": f"记忆检索失败: {str(e)}"
            }

    async def _get_related_rules(self, query: str) -> List[Dict]:
        """获取相关规则，自动归纳总结，并按统计字段排序，输出标准格式"""
        try:
            rules = await self.secondme_rule_adapter.retrieve_rules(query)
            def sort_key(rule):
                meta = getattr(rule, 'metadata', {}) or {}
                return (
                    -meta.get("reference_count", 0),
                    -(meta.get("last_reference_time") or 0),
                    -meta.get("update_count", 0)
                )
            rules = sorted(rules, key=sort_key)
            # 转为标准格式
            result = []
            for rule in rules:
                # 兼容对象和字典
                if isinstance(rule, dict):
                    result.append({
                        "role": rule.get("role", "rule"),
                        "content": rule.get("content", rule.get("page_content", "")),
                        "metadata": rule.get("metadata", {})
                    })
                else:
                    result.append({
                        "role": getattr(rule, "role", "rule"),
                        "content": getattr(rule, "content", getattr(rule, "page_content", "")),
                        "metadata": getattr(rule, "metadata", {})
                    })
            # 自动归纳总结
            if len(result) > 1:
                prompt = ChatPromptTemplate.from_template("请用简明中文总结以下规则内容：{context}")
                llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
                chain = create_stuff_documents_chain(llm, prompt)
                summary = chain.invoke({"context": [r["content"] for r in result]})
                result.append({
                    "role": "system",
                    "content": summary,
                    "metadata": {"summary": "以上为自动归纳总结"}
                })
            return result
        except Exception as e:
            logger.error(f"[CentralExecutive] 获取规则失败: {e}")
            return []

    async def _get_working_memories(self, query: str) -> List[Dict]:
        """获取工作记忆，自动归纳总结，并按统计字段排序，输出标准格式"""
        try:
            memories = await self.secondme_working_adapter.load_memory_variables({"input": query})
            chat_history = memories.get("chat_history", [])
            def sort_key(msg):
                meta = msg.get("metadata", {}) if isinstance(msg, dict) else getattr(msg, 'metadata', {}) or {}
                return (
                    -meta.get("reference_count", 0),
                    -(meta.get("last_reference_time") or 0),
                    -meta.get("update_count", 0)
                )
            # 转为标准格式
            result = []
            for msg in chat_history:
                if isinstance(msg, dict):
                    result.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", msg.get("raw", "")),
                        "metadata": msg.get("metadata", {})
                    })
                else:
                    result.append({
                        "role": getattr(msg, "role", "user"),
                        "content": getattr(msg, "content", getattr(msg, "raw", "")),
                        "metadata": getattr(msg, "metadata", {})
                    })
            result = sorted(result, key=sort_key)
            # 自动归纳总结
            if len(result) > 1:
                prompt = ChatPromptTemplate.from_template("请用简明中文总结以下对话内容：{context}")
                llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
                chain = create_stuff_documents_chain(llm, prompt)
                summary = chain.invoke({"context": [m["content"] for m in result]})
                result.append({
                    "role": "system",
                    "content": summary,
                    "metadata": {"summary": "以上为自动归纳总结"}
                })
            return result
        except Exception as e:
            logger.error(f"[CentralExecutive] 获取工作记忆失败: {e}")
            return []

    async def _get_long_term_memories(self, query: str) -> list:
        """
        检索长期记忆：
        - 只用 second-me 的结构化检索，不用 embedding
        - 返回标准格式
        """
        try:
            memories = await self.secondme_long_term_adapter.retrieve_memory(query)
            return memories
        except Exception as e:
            logger.error(f"[CentralExecutive] 检索长期记忆失败: {str(e)}")
            return []

    async def _merge_memories(self, content1: str, content2: str) -> Dict:
        """自动融合两条相似记忆，返回融合内容和说明"""
        try:
            merge_prompt = ChatPromptTemplate.from_template(
                "以下是两条内容，可能有重复或冲突，请合并为一条更合理的记忆，并用中文解释合并理由：\n内容1：{content1}\n内容2：{content2}"
            )
            llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            merge_chain = merge_prompt | llm | StrOutputParser()
            merged = merge_chain.invoke({"content1": content1, "content2": content2})
            return {"merged_content": merged, "explanation": "以上为自动融合结果"}
        except Exception as e:
            logger.error(f"[CentralExecutive] 记忆融合失败: {e}")
            return {"merged_content": content1 + "\n---\n" + content2, "explanation": "自动融合失败，采用简单拼接"}

    async def retrieve_memory(self, user_message: str) -> Dict[str, Any]:
        """检索记忆（包装方法）"""
        try:
            return await self.combine_context(user_message)
        except Exception as e:
            logger.error(f"[CentralExecutive] retrieve_memory 失败: {e}", exc_info=True)
            return {
                "related_rules": [],
                "related_working_term": [],
                "related_memories": [],
                "final_context": "",
                "system_context": f"记忆检索失败: {str(e)}"
            }

    async def initialize(self):
        """初始化所有记忆组件"""
        if self.initialized:
            return
        
        logger.info("[CentralExecutive] 开始初始化记忆组件...")
        
        # 确保所有记忆组件都被初始化
        if SECONDME_AVAILABLE:
            # 只初始化各适配器，不再调用 initialize_secondme
            pass
        # 无论是使用适配器还是原生模块，都确保初始化
        await self.secondme_long_term_adapter.initialize()
        await self.secondme_rule_adapter.initialize()
        await self.secondme_working_adapter.initialize()
        
        self.initialized = True
        logger.info("[CentralExecutive] 所有记忆组件初始化完成")

# ✅ 全局实例
central_executive = CentralExecutive()
