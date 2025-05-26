"""Second-Me规则记忆适配器

该适配器将Second-Me的功能适配到EVA的规则记忆接口。
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union

# EVA导入
from logs.logs import logger

# Second-Me导入
try:
    # 尝试导入Second-Me的模块
    from lpm_kernel.L2.utils import get_embedding 
    from lpm_kernel.L0.l0_generator import L0Generator
    
    SECOND_ME_IMPORTED = True
except ImportError as e:
    logger.warning(f"Second-Me导入失败: {e}")
    SECOND_ME_IMPORTED = False

# 规则文件路径
from .config import load_config
config = load_config()
DATA_PATH = config.get("data_path", "/app/data")
RULE_FILE_PATH = os.path.join(DATA_PATH, "rules", "rules.json")

def _load_rules():
    """加载所有规则（本地JSON文件）"""
    if not os.path.exists(RULE_FILE_PATH):
        return []
    try:
        with open(RULE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载规则文件失败: {str(e)}")
        return []

def _save_rules(rules):
    logger.info(f"[DEBUG][rule_adapter] _save_rules 被调用，rules 长度: {len(rules)}，内容预览: {str(rules)[:200]}")
    os.makedirs(os.path.dirname(RULE_FILE_PATH), exist_ok=True)
    try:
        with open(RULE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        logger.info(f"[DEBUG][rule_adapter] 写入成功: {RULE_FILE_PATH}")
    except Exception as e:
        logger.warning(f"[DEBUG][rule_adapter] 保存规则文件失败: {str(e)}")
        print(f"[DEBUG][rule_adapter] 写入异常: {e}")

# 新增：统一规则条目为 second-me 标准字典格式

def to_standard_rule_dict(item):
    """
    将字符串、旧字典等全部转为标准格式：
    {'role': 'rule', 'content': ..., 'metadata': {...}}
    """
    if isinstance(item, dict):
        if 'role' in item and 'content' in item:
            if 'metadata' not in item:
                item['metadata'] = {}
            return item
        # 兼容旧格式
        return {
            'role': 'rule',
            'content': item.get('text', item.get('content', '')),
            'metadata': item.get('metadata', {})
        }
    if isinstance(item, str):
        return {'role': 'rule', 'content': item, 'metadata': {}}
    return {'role': 'rule', 'content': str(item), 'metadata': {}}

class SecondMeRuleAdapter:
    """适配Second-Me的规则系统到EVA接口"""
    
    def __init__(self):
        """初始化Second-Me规则适配器"""
        self.initialized = False
        self.rules = []
        self.rule_file_path = RULE_FILE_PATH
        self.lock = asyncio.Lock()
        
        # 检查Second-Me是否可用
        if not SECOND_ME_IMPORTED:
            logger.warning("Second-Me模块未成功导入，部分功能可能不可用")
    
    async def initialize(self):
        """初始化Second-Me的规则组件（本地JSON实现）"""
        if self.initialized:
            return
        
        async with self.lock:
            if self.initialized:  # 双重检查锁定
                return
                
            try:
                logger.info("[SecondMeRuleAdapter] 正在初始化Second-Me规则组件...")
                
                # 加载现有规则（如果有）
                self.rules = _load_rules()
                logger.info(f"[SecondMeRuleAdapter] 加载了 {len(self.rules)} 条规则")
                
                logger.info("[SecondMeRuleAdapter] Second-Me规则组件初始化成功")
                self.initialized = True
                
            except Exception as e:
                logger.error(f"[SecondMeRuleAdapter] 初始化失败: {str(e)}")
                raise RuntimeError(f"无法初始化Second-Me规则系统: {str(e)}")
    
    def ensure_initialized(self):
        """确保组件已初始化"""
        if not self.initialized:
            raise RuntimeError("Second-Me规则适配器尚未初始化")
    
    def _extract_entities_relations_tags(self, text: str):
        """
        简单实体、关系、标签抽取（可扩展为L0/L1层调用）
        返回：entities, relations, tags
        """
        entities = []
        relations = []
        tags = []
        import re
        match = re.match(r"(我|小明|小红)?(必须|应该|禁止|优先|避免|需要|可以|建议|提醒|允许)(.+)", text)
        if match:
            subject = match.group(1) or "我"
            predicate = match.group(2)
            obj = match.group(3).strip()
            entities = [subject, obj]
            relations = [{"subject": subject, "predicate": predicate, "object": obj}]
            tags = [predicate]
        return entities, relations, tags

    async def store_rule(self, rule_text: str, metadata: Optional[Dict[str, Any]] = None) -> dict:
        """存储规则，输出标准格式，优先用L0/L1深度语义分析自动抽取结构化信息"""
        await self.initialize()
        self.ensure_initialized()
        if metadata is None:
            metadata = {}
        try:
            rule_id = f"rule_{len(self.rules) + 1}"
            priority = metadata.get("priority", 0.5)
            source = metadata.get("source", "user")
            timestamp = self._get_timestamp()
            # 优先用L0/L1深度语义分析
            entities, relations, tags, interests, events = [], [], [], [], []
            try:
                if hasattr(self, 'l0_generator') and self.l0_generator:
                    l0_result = await self.l0_generator.process_text(rule_text)
                    entities = l0_result.get("entities", [])
                    tags = l0_result.get("tags", [])
                if hasattr(self, 'l1_generator') and self.l1_generator:
                    l1_result = await self.l1_generator.analyze_text(rule_text)
                    relations = l1_result.get("relations", [])
                    interests = l1_result.get("interests", [])
                    events = l1_result.get("events", [])
            except Exception as l_err:
                logger.warning(f"[SecondMeRuleAdapter] L0/L1分析失败，回退正则: {str(l_err)}")
                entities, relations, tags = self._extract_entities_relations_tags(rule_text)
            rule_data = {
                "id": rule_id,
                "text": rule_text,
                "created_at": timestamp,
                "updated_at": timestamp,
                "metadata": {
                    "priority": float(priority),
                    "source": source,
                    "entities": entities,
                    "relations": relations,
                    "tags": tags,
                    "interests": interests,
                    "events": events,
                    **metadata
                }
            }
            self.rules.append(rule_data)
            _save_rules(self.rules)
            logger.info(f"[SecondMeRuleAdapter] 成功存储规则: {rule_id}，实体: {entities}，关系: {relations}，标签: {tags}，兴趣: {interests}，事件: {events}")
            # 返回标准格式
            return to_standard_rule_dict(rule_data)  # 中文注释：强制标准格式输出
        except Exception as e:
            logger.error(f"[SecondMeRuleAdapter] 存储规则失败: {str(e)}")
            # 返回标准格式，标记失败
            return to_standard_rule_dict({
                "role": "rule",
                "content": rule_text,
                "metadata": {"error": str(e), **(metadata or {})}
            })
    
    async def retrieve_rules(self, query: str = None, top_k: int = 5) -> list:
        """
        检索规则：
        - 仅用内容、规则名、优先级等多维条件
        - 完全忽略 embedding
        - 返回标准格式
        """
        await self.initialize()
        self.ensure_initialized()
        try:
            all_rules = self.rules.copy()
            results = []
            if query:
                query_lower = query.lower()
                for rule in all_rules:
                    content = rule.get('text', '').lower()
                    meta = rule.get('metadata', {})
                    name = meta.get('name', '').lower()
                    if query_lower in content or query_lower in name:
                        results.append(rule)
            else:
                results = all_rules
            # 按优先级、时间排序
            def sort_key(rule):
                meta = rule.get('metadata', {})
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
            logger.error(f"[SecondMeRuleAdapter] 检索规则失败: {str(e)}")
            return []
    
    async def update_rule(self, rule_id: str, rule_text: str, metadata: Optional[Dict[str, Any]] = None) -> dict:
        """更新规则，输出标准格式"""
        await self.initialize()
        self.ensure_initialized()
        if metadata is None:
            metadata = {}
        try:
            found = False
            for rule in self.rules:
                # 跳过无 id 字段的条目，保证健壮性
                if not isinstance(rule, dict) or 'id' not in rule and not rule.get('metadata', {}).get('id'):
                    continue
                # 兼容两种格式
                rid = rule.get('id') or rule.get('metadata', {}).get('id')
                if rid == rule_id:
                    if 'text' in rule:
                        rule['text'] = rule_text
                    if 'content' in rule:
                        rule['content'] = rule_text
                    rule['updated_at'] = self._get_timestamp()
                    if 'metadata' not in rule:
                        rule['metadata'] = {}
                    for key, value in metadata.items():
                        rule['metadata'][key] = value
                    found = True
                    break
            if not found:
                logger.warning(f"[SecondMeRuleAdapter] 规则ID不存在: {rule_id}")
                # 返回标准格式，标记失败
                return to_standard_rule_dict({
                    "role": "rule",
                    "content": rule_text,
                    "metadata": {"error": f"规则ID不存在: {rule_id}", **(metadata or {})}
                })
            _save_rules(self.rules)
            logger.info(f"[SecondMeRuleAdapter] 成功更新规则: {rule_id}")
            # 返回标准格式
            return to_standard_rule_dict(rule)
        except Exception as e:
            logger.error(f"[SecondMeRuleAdapter] 更新规则失败: {str(e)}")
            # 返回标准格式，标记失败
            return to_standard_rule_dict({
                "role": "rule",
                "content": rule_text,
                "metadata": {"error": str(e), **(metadata or {})}
            })
    
    async def delete_rule(self, rule_id: str) -> dict:
        """删除规则，输出标准格式"""
        await self.initialize()
        self.ensure_initialized()
        try:
            # 查找规则
            original_count = len(self.rules)
            # 只保留 id 不等于 rule_id 的条目，兼容所有格式
            def get_rule_id(rule):
                if not isinstance(rule, dict):
                    return None
                return rule.get('id') or rule.get('metadata', {}).get('id')
            self.rules = [rule for rule in self.rules if get_rule_id(rule) != rule_id]
            if len(self.rules) == original_count:
                logger.warning(f"[SecondMeRuleAdapter] 规则ID不存在: {rule_id}")
                # 返回标准格式，标记失败
                return to_standard_rule_dict({
                    "role": "rule",
                    "content": "",
                    "metadata": {"id": rule_id, "deleted": False}
                })
            # 保存更新的规则
            _save_rules(self.rules)
            logger.info(f"[SecondMeRuleAdapter] 成功删除规则: {rule_id}")
            # 返回标准格式，标记已删除
            return to_standard_rule_dict({
                "role": "rule",
                "content": "",
                "metadata": {"id": rule_id, "deleted": True}
            })
        except Exception as e:
            logger.error(f"[SecondMeRuleAdapter] 删除规则失败: {str(e)}")
            # 返回标准格式，标记失败
            return to_standard_rule_dict({
                "role": "rule",
                "content": "",
                "metadata": {"id": rule_id, "deleted": False, "error": str(e)}
            })
    
    async def retrieve_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """兼容测试用例，按ID查找规则，输出标准格式"""
        await self.initialize()
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return to_standard_rule_dict(rule)  # 强制标准格式
        return None
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def _find_similar_rule(self, rule_text: str, threshold: float = 0.85) -> Optional[Dict[str, Any]]:
        """查找与给定规则文本相似的规则
        
        Args:
            rule_text: 规则文本
            threshold: 相似度阈值
            
        Returns:
            Optional[Dict]: 找到的相似规则，如果不存在则返回None
        """
        # 获取规则文本的嵌入向量
        query_embedding = get_embedding(rule_text)
        
        # 查找相似规则
        most_similar_rule = None
        highest_similarity = 0.0
        
        for rule in self.rules:
            rule_embedding = rule.get("embedding", [])
            if rule_embedding:
                similarity = self._calculate_similarity(query_embedding, rule_embedding)
                
                if similarity > highest_similarity and similarity >= threshold:
                    highest_similarity = similarity
                    most_similar_rule = rule
        
        return most_similar_rule
    
    async def _merge_rules(self, rule1: str, rule2: str) -> str:
        """智能合并两条规则
        
        Args:
            rule1: 第一条规则文本
            rule2: 第二条规则文本
            
        Returns:
            str: 合并后的规则文本
        """
        try:
            # 简单合并规则
            # 在实际应用中，可以使用更复杂的方法
            # 例如使用LLM生成更好的合并结果
            
            # 方案1：简单拼接
            merged = f"{rule1}\n---\n{rule2}"
            
            # 方案2：使用L0/L1层更智能地合并（目前使用简单方法）
            # TODO: 实现更智能的合并方法
            
            return merged
            
        except Exception as e:
            logger.warning(f"[SecondMeRuleAdapter] 合并规则失败: {str(e)}")
            # 失败时简单拼接
            return f"{rule1}\n---\n{rule2}"

    async def add_rule(self, rule_text: str, metadata: Optional[Dict[str, Any]] = None) -> dict:
        """兼容旧接口，等价于 store_rule，输出标准格式"""
        return await self.store_rule(rule_text, metadata) 