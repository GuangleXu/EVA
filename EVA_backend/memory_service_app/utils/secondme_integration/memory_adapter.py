"""Second-Me长期记忆适配器

该适配器将Second-Me的L2层记忆功能适配到EVA的长期记忆接口。
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI

# EVA导入
from logs.logs import logger

# Second-Me导入
try:
    # 尝试导入Second-Me的模块
    from lpm_kernel.L2.memory_manager import get_memory_manager
    from lpm_kernel.L2.data import L2DataProcessor
    from lpm_kernel.L2.utils import get_embedding
    from lpm_kernel.L0.l0_generator import L0Generator
    from lpm_kernel.api.domains.kernel2.services.knowledge_service import L0KnowledgeRetriever, L1KnowledgeRetriever
    from lpm_kernel.file_data.embedding_service import EmbeddingService
    
    SECOND_ME_IMPORTED = True
except ImportError as e:
    logger.warning(f"Second-Me导入失败: {e}")
    SECOND_ME_IMPORTED = False

# 从config中加载数据路径
from .config import load_config
config = load_config()
DATA_PATH = config.get("data_path", "/app/data")
MEMORY_FILE_PATH = os.path.join(DATA_PATH, "memories", "memories.json")

try:
    from graphrag.query.structured_search.local_search.search import LocalSearch
    L2_AVAILABLE = True
except ImportError:
    L2_AVAILABLE = False

def _convert_to_standard_dict(memory):
    """
    将旧格式的记忆条目（如只有 text 字段）转换为 second-me 标准字典格式。
    标准格式：{'role': 'user', 'content': 'xxx', 'metadata': {...}}
    内容字段优先级：content > text > value > ''
    """
    content = memory.get('content') or memory.get('text') or memory.get('value') or ''
    return {
        'role': memory.get('source', 'user'),
        'content': content,
        'metadata': {
            'id': memory.get('id', ''),
            'priority': memory.get('priority', 0.5),
            'timestamp': memory.get('timestamp', ''),
            **memory.get('metadata', {})
        }
    }

def _load_memories():
    """加载所有记忆（本地JSON文件），自动转换为标准字典格式"""
    if not os.path.exists(MEMORY_FILE_PATH):
        return []
    try:
        with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            # 自动转换为标准格式
            return [_convert_to_standard_dict(m) for m in raw]
    except Exception as e:
        logger.warning(f"加载记忆文件失败: {str(e)}")
        return []

def _save_memories(memories):
    # 写入前打印最后3条内容
    preview = memories[-3:] if len(memories) >= 3 else memories
    logger.info(f"[DEBUG][memory_adapter] 即将写入路径: {MEMORY_FILE_PATH}，写入条数: {len(memories)}，预览最后3条: {preview}")
    os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
    try:
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        # 写入后再次打印最后3条内容
        logger.info(f"[DEBUG][memory_adapter] 写入成功: {MEMORY_FILE_PATH}，预览最后3条: {preview}")
    except Exception as e:
        import traceback
        logger.warning(f"[DEBUG][memory_adapter] 保存记忆文件失败: {str(e)}\n{traceback.format_exc()}")
        print(f"[DEBUG][memory_adapter] 写入异常: {e}\n{traceback.format_exc()}")

def _get_current_timestamp():
    from datetime import datetime
    return datetime.now().isoformat()

class SecondMeMemoryAdapter(object):
    """适配Second-Me的长期记忆系统到EVA接口"""
    
    def __init__(self):
        """初始化Second-Me记忆适配器"""
        self.initialized = False
        self.memory_manager = None
        self.data_manager = None  # 不再用DataManager
        self.l0_generator = None
        self.lock = asyncio.Lock()
        self.l0_retriever = None
        self.l1_retriever = None
        self.l2_retriever = None  # 新增L2检索器
        if not SECOND_ME_IMPORTED:
            logger.warning("Second-Me模块未成功导入，部分功能可能不可用")
    
    async def initialize(self):
        """初始化Second-Me的记忆组件"""
        if self.initialized:
            return
        async with self.lock:
            if self.initialized:
                return
            try:
                logger.info("[SecondMeMemoryAdapter] 正在初始化Second-Me记忆组件...")
                self.memory_manager = get_memory_manager() if SECOND_ME_IMPORTED else None
                self.l0_generator = L0Generator() if SECOND_ME_IMPORTED else None
                self.l0_retriever = L0KnowledgeRetriever(embedding_service=EmbeddingService(), similarity_threshold=0.7, max_chunks=5)
                self.l1_retriever = L1KnowledgeRetriever(embedding_service=EmbeddingService(), similarity_threshold=0.7, max_shades=5)
                # L2层：GraphRAG官方LocalSearch检索器（需补充数据配置）
                if L2_AVAILABLE:
                    try:
                        # ======【GraphRAG L2智能检索参数自动补全-OpenAI专用】======
                        import pandas as pd
                        from openai import OpenAI
                        from graphrag.query.structured_search.local_search.search import LocalSearch
                        import tiktoken
                        
                        # 加载parquet数据
                        entities = pd.read_parquet("EVA/EVA_backend/Second-Me/resources/L1/graphrag_indexing_output/subjective/entities.parquet")
                        relationships = pd.read_parquet("EVA/EVA_backend/Second-Me/resources/L1/graphrag_indexing_output/subjective/relationships.parquet")
                        text_units = pd.read_parquet("EVA/EVA_backend/Second-Me/resources/L1/graphrag_indexing_output/subjective/text_units.parquet")
                        # 如有 entity_text_embeddings.parquet 也请一并加载
                        entity_text_embeddings = None  # 如有请补全
                        
                        # 初始化OpenAI embedding对象，API Key 从环境变量读取
                        openai_api_key = os.environ.get("OPENAI_API_KEY", "")  # 从环境变量读取OpenAI密钥
                        openai_client = OpenAI(api_key=openai_api_key)  # 用环境变量初始化OpenAI客户端
                        
                        def openai_embedder(texts):
                            # 批量获取embedding
                            response = openai_client.embeddings.create(
                                input=texts,
                                model="text-embedding-ada-002"
                            )
                            return [item.embedding for item in response.data]
                        
                        # tokenizer用cl100k_base（tiktoken库）
                        tokenizer = tiktoken.get_encoding("cl100k_base")
                        
                        # 初始化L2检索器
                        self.l2_retriever = LocalSearch(
                            community_reports=None,
                            text_units=text_units,
                            entities=entities,
                            relationships=relationships,
                            entity_text_embeddings=entity_text_embeddings,  # 如有embedding文件请补全
                            text_embedder=openai_embedder,
                            token_encoder=tokenizer
                        )
                        logger.info("[SecondMeMemoryAdapter] L2检索器(LocalSearch)已自动完成OpenAI embedding/tokenizer集成")
                    except Exception as l2e:
                        logger.warning(f"[SecondMeMemoryAdapter] L2检索器初始化失败: {l2e}")
                os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
                logger.info("[SecondMeMemoryAdapter] Second-Me记忆组件初始化成功")
                self.initialized = True
            except Exception as e:
                logger.error(f"[SecondMeMemoryAdapter] 初始化失败: {str(e)}")
                raise RuntimeError(f"无法初始化Second-Me记忆系统: {str(e)}")

    def ensure_initialized(self):
        if not self.initialized:
            raise RuntimeError("Second-Me记忆适配器尚未初始化")

    def _extract_entities_relations_tags(self, text: str):
        """
        简单实体、关系、标签抽取（可扩展为L0/L1层调用）
        返回：entities, relations, tags
        """
        entities = []
        relations = []
        tags = []
        # 示例：我喜欢苹果
        import re
        match = re.match(r"(我|小明|小红)?(喜欢|讨厌|需要|拥有|吃|喝|去|看|玩|学|买|用)(.+)", text)
        if match:
            subject = match.group(1) or "我"
            predicate = match.group(2)
            obj = match.group(3).strip()
            entities = [subject, obj]
            relations = [{"subject": subject, "predicate": predicate, "object": obj}]
            tags = [predicate]
        # 可扩展：调用L0/L1层更智能抽取
        return entities, relations, tags

    async def store_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"【DEBUG】已进入 store_memory，text: {text}, metadata: {metadata}")
        await self.initialize()
        self.ensure_initialized()
        if metadata is None:
            metadata = {}
        try:
            logger.info(f"【DEBUG】调用 store_memory，目标路径: {MEMORY_FILE_PATH}")
            priority = metadata.get("priority", 0.5)
            source = metadata.get("source", "user")
            memories = _load_memories()
            memory_id = f"mem_{len(memories) + 1}"
            # 优先用L0/L1深度语义分析
            entities, relations, tags, interests, events = [], [], [], [], []
            try:
                if self.l0_generator:
                    l0_result = await self.l0_generator.process_text(text)
                    entities = l0_result.get("entities", [])
                    tags = l0_result.get("tags", [])
                if hasattr(self, 'l1_generator') and self.l1_generator:
                    l1_result = await self.l1_generator.analyze_text(text)
                    relations = l1_result.get("relations", [])
                    interests = l1_result.get("interests", [])
                    events = l1_result.get("events", [])
            except Exception as l_err:
                logger.warning(f"[SecondMeMemoryAdapter] L0/L1分析失败，回退正则: {str(l_err)}")
                entities, relations, tags = self._extract_entities_relations_tags(text)
            # 构造标准格式
            memory_data = {
                'role': source,
                'content': text,
                'metadata': {
                    'id': memory_id,
                    'priority': float(priority),
                    'timestamp': metadata.get('timestamp', _get_current_timestamp()),
                    'entities': entities,
                    'relations': relations,
                    'tags': tags,
                    'interests': interests,
                    'events': events,
                    **metadata
                }
            }
            memories.append(memory_data)
            _save_memories(memories)
            logger.info(f"[SecondMeMemoryAdapter] 成功存储记忆: {memory_id}，实体: {entities}，关系: {relations}，标签: {tags}，兴趣: {interests}，事件: {events}")
            return {"success": True, "memory_id": memory_id, "message": "记忆已成功存储到Second-Me系统"}
        except Exception as e:
            logger.error(f"[SecondMeMemoryAdapter] 存储记忆失败: {str(e)}")
            return {"success": False, "error": str(e), "message": "记忆存储失败"}

    async def retrieve_memory(self, query: str, top_k: int = 5, **kwargs) -> list:
        logger.info(f"【DEBUG】已进入 retrieve_memory，query: {query}, top_k: {top_k}")
        await self.initialize()
        self.ensure_initialized()
        try:
            # 1. L2层（多模态/图谱/embedding综合检索，GraphRAG官方推荐）
            if self.l2_retriever:
                try:
                    # LocalSearch官方推荐用法
                    l2_result = await self.l2_retriever.search(query)
                    if l2_result and getattr(l2_result, 'response', None):
                        logger.info(f"[SecondMeMemoryAdapter] L2智能检索命中，内容: {l2_result.response}")
                        return [{
                            'role': 'user',
                            'content': l2_result.response,
                            'metadata': {'score': 1.0, 'source': 'secondme_l2'}
                        }]
                except Exception as l2e:
                    logger.warning(f"[SecondMeMemoryAdapter] L2检索异常: {l2e}")
            # 2. L1层（全局知识/标签/关系）
            if self.l1_retriever:
                l1_result = self.l1_retriever.retrieve(query)
                if l1_result:
                    logger.info(f"[SecondMeMemoryAdapter] L1智能检索命中，内容: {l1_result}")
                    return [{
                        'role': 'user',
                        'content': l1_result,
                        'metadata': {'score': 0.9, 'source': 'secondme_l1'}
                    }]
            # 3. L0层（embedding语义检索）
            if self.l0_retriever:
                l0_result = self.l0_retriever.retrieve(query)
                if l0_result:
                    logger.info(f"[SecondMeMemoryAdapter] L0智能检索命中，内容: {l0_result}")
                    return [{
                        'role': 'user',
                        'content': l0_result,
                        'metadata': {'score': 0.8, 'source': 'secondme_l0'}
                    }]
            logger.info("[SecondMeMemoryAdapter] L0/L1/L2均未命中，返回空")
            return []
        except Exception as e:
            logger.error(f"[SecondMeMemoryAdapter] 智能检索记忆失败: {str(e)}")
            return []

    async def update_memory(self, memory_id: str, new_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """更新Second-Me系统中的记忆（本地JSON实现），统一为标准字典格式"""
        await self.initialize()
        self.ensure_initialized()
        if metadata is None:
            metadata = {}
        try:
            logger.info(f"【DEBUG】调用 update_memory，目标路径: {MEMORY_FILE_PATH}")
            memories = _load_memories()
            updated = False
            for memory in memories:
                if memory['metadata'].get('id') == memory_id:
                    memory['content'] = new_text
                    for key, value in metadata.items():
                        memory['metadata'][key] = value
                    updated = True
                    break
            if updated:
                _save_memories(memories)
                logger.info(f"[SecondMeMemoryAdapter] 成功更新记忆: {memory_id}")
                return {"success": True, "memory_id": memory_id, "message": "记忆已成功更新"}
            else:
                logger.warning(f"[SecondMeMemoryAdapter] 记忆ID不存在: {memory_id}")
                return {"success": False, "error": f"记忆ID不存在: {memory_id}", "message": "记忆更新失败"}
        except Exception as e:
            logger.error(f"[SecondMeMemoryAdapter] 更新记忆失败: {str(e)}")
            return {"success": False, "error": str(e), "message": "记忆更新失败"}

    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        从Second-Me系统删除记忆（本地JSON实现）
        自动查找并删除所有内容中包含用户原始关键词（如"巧克力"）且时间戳与用户内容接近（1分钟内）的AI回复，保证一轮对话完整删除，避免误删历史内容。
        """
        await self.initialize()
        self.ensure_initialized()
        try:
            logger.info(f"【DEBUG】调用 delete_memory，目标路径: {MEMORY_FILE_PATH}")
            from datetime import datetime, timedelta
            memories = _load_memories()
            def get_mem_id(m):
                if not isinstance(m, dict):
                    return None
                return m.get('id') or m.get('metadata', {}).get('id')
            # 找到要删除的用户记忆的下标和内容、时间戳
            idx_to_del = None
            user_content = None
            user_ts = None
            for idx, m in enumerate(memories):
                if get_mem_id(m) == memory_id:
                    idx_to_del = idx
                    user_content = m.get('content', '')
                    user_ts = m.get('metadata', {}).get('timestamp', '')
                    break
            if idx_to_del is not None:
                # 取用户内容中的关键词（如"巧克力"）
                keyword = ''
                if user_content:
                    import re
                    match = re.search(r"喜欢([\u4e00-\u9fa5A-Za-z0-9]+)", user_content)
                    if match:
                        keyword = match.group(1)
                    else:
                        keyword = user_content.strip()
                # 解析用户时间戳
                user_dt = None
                if user_ts:
                    try:
                        user_dt = datetime.fromisoformat(user_ts)
                    except Exception:
                        user_dt = None
                # 删除所有包含关键词且时间戳接近的AI回复
                def is_related_ai(m):
                    if m.get('role') != 'assistant' or not keyword:
                        return False
                    if keyword not in m.get('content', ''):
                        return False
                    ai_ts = m.get('metadata', {}).get('timestamp', '')
                    if user_dt and ai_ts:
                        try:
                            ai_dt = datetime.fromisoformat(ai_ts)
                            # 时间差小于1分钟
                            if abs((ai_dt - user_dt).total_seconds()) <= 60:
                                return True
                        except Exception:
                            return False
                    return False
                new_memories = [m for i, m in enumerate(memories) if i != idx_to_del and not is_related_ai(m)]
                _save_memories(new_memories)
                logger.info(f"[SecondMeMemoryAdapter] 成功删除记忆: {memory_id} 及其相关AI回复（关键词：{keyword}，时间戳比对）")
                return {"success": True, "memory_id": memory_id, "message": "记忆及相关AI回复已成功删除"}
            else:
                logger.warning(f"[SecondMeMemoryAdapter] 记忆ID不存在: {memory_id}")
                return {"success": False, "error": f"记忆ID不存在: {memory_id}", "message": "记忆删除失败"}
        except Exception as e:
            logger.error(f"[SecondMeMemoryAdapter] 删除记忆失败: {str(e)}")
            return {"success": False, "error": str(e), "message": "记忆删除失败"}

    async def _process_with_l0(self, text: str) -> Dict[str, Any]:
        """使用Second-Me的L0层处理文本"""
        try:
            if self.l0_generator:
                result = await self.l0_generator.process_text(text)
                return result
            else:
                return {"processed_text": text, "text": text}
        except Exception as e:
            logger.warning(f"[SecondMeMemoryAdapter] L0处理失败，使用简单处理: {str(e)}")
            return {"processed_text": text, "text": text}

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

    async def store_dialog(self, user_text: str, assistant_text: str, user_metadata: Optional[Dict[str, Any]] = None, assistant_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        一次性存储一轮完整对话（用户+AI），分别以 role:user 和 role:assistant 存储到 memories.json
        user_text: 用户输入内容
        assistant_text: AI助手回复内容
        user_metadata/assistant_metadata: 可选元数据，分别用于两条内容
        返回：{'success': True/False, 'user_memory_id': ..., 'assistant_memory_id': ...}
        """
        await self.initialize()
        self.ensure_initialized()
        if user_metadata is None:
            user_metadata = {}
        if assistant_metadata is None:
            assistant_metadata = {}
        try:
            logger.info(f"【DEBUG】调用 store_dialog，目标路径: {MEMORY_FILE_PATH}")
            memories = _load_memories()
            # 存储用户内容
            user_id = f"mem_{len(memories) + 1}"
            user_data = {
                'role': 'user',
                'content': user_text,
                'metadata': {
                    'id': user_id,
                    'priority': float(user_metadata.get('priority', 0.5)),
                    'timestamp': user_metadata.get('timestamp', _get_current_timestamp()),
                    **user_metadata
                }
            }
            memories.append(user_data)
            # 存储AI内容
            assistant_id = f"mem_{len(memories) + 1}"
            assistant_data = {
                'role': 'assistant',
                'content': assistant_text,
                'metadata': {
                    'id': assistant_id,
                    'priority': float(assistant_metadata.get('priority', 0.5)),
                    'timestamp': assistant_metadata.get('timestamp', _get_current_timestamp()),
                    **assistant_metadata
                }
            }
            memories.append(assistant_data)
            _save_memories(memories)
            logger.info(f"[SecondMeMemoryAdapter] 成功存储一轮对话: user_id={user_id}, assistant_id={assistant_id}")
            return {"success": True, "user_memory_id": user_id, "assistant_memory_id": assistant_id}
        except Exception as e:
            logger.error(f"[SecondMeMemoryAdapter] 存储一轮对话失败: {str(e)}")
            return {"success": False, "error": str(e)} 