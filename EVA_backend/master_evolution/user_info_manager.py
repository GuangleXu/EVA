#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户信息管理器

用于存储和检索用户个性化信息，提升对话的自然性和个人化体验。
主要功能：
1. 提供用户基本信息存储（姓名、性别、年龄等）- 永久保存
2. 提供用户偏好信息存储（喜好、习惯等）- 自动分类
3. 提供用户交互风格设置（正式、随意等）
4. 支持动态扩展用户信息属性
"""

import json
import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple, Set
from logs.logs import logger
from memory_service_app.utils.redis_client import set_key, get_key
import os

# 默认永久保存
DEFAULT_EXPIRY = None

class UserInfoManager:
    """用户信息管理器，提供异步API接口"""
    
    def __init__(self):
        """初始化用户信息管理器"""
        self.user_info_key = "user_info"
        # 动态加载用户信息分类和提取规则
        config_dir = os.path.join(os.path.dirname(__file__), 'user_info_config')
        try:
            with open(os.path.join(config_dir, 'info_categories.json'), 'r', encoding='utf-8') as f:
                self.info_categories = json.load(f)
            with open(os.path.join(config_dir, 'extraction_patterns.json'), 'r', encoding='utf-8') as f:
                self.extraction_patterns = json.load(f)
        except Exception as e:
            # 加载失败时使用默认配置
            self.info_categories = {
                "basic": ["name", "gender", "age", "birthday", "occupation", "location"],
                "contact": ["phone", "email", "address", "wechat", "qq"],
                "preferences": ["food", "color", "music", "movie", "book", "hobby", "sport", "pet", "travel"],
                "style": ["communication_style", "humor_level", "formality"],
                "health": ["allergies", "conditions", "diet_restrictions"],
                "device": ["device_type", "os", "browser"],
                "custom": []
            }
            self.extraction_patterns = {}
            print(f"[警告] 用户信息配置加载失败: {e}")
    
    async def save_user_info(self, user_info: Dict[str, Any], expiry: int = DEFAULT_EXPIRY) -> bool:
        """
        永久保存用户信息到Redis
        
        Args:
            user_info: 用户信息字典
            expiry: 过期时间（秒），默认None表示永久保存
            
        Returns:
            保存成功返回True，否则返回False
        """
        try:
            # 增加判空处理，防止 existing_info 为 None
            existing_info = await asyncio.wait_for(self.get_user_info(), timeout=5)
            if existing_info is None:
                existing_info = {}
            categorized_info = self._categorize_info(user_info)
            for category, fields in categorized_info.items():
                if category not in existing_info:
                    existing_info[category] = {}
                for field, value in fields.items():
                    if field in existing_info[category] and existing_info[category][field] == value:
                        continue
                    existing_info[category][field] = value
            await set_key(self.user_info_key, json.dumps(existing_info, ensure_ascii=False), expiry)
            logger.info(f"✅ 用户信息保存成功: {user_info}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存用户信息失败: {str(e)}")
            return False
    
    def _categorize_info(self, user_info: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """将用户信息分类到不同类别"""
        categorized = {}
        for key, value in user_info.items():
            category = None
            # 优先 occupation 字段归入 occupation 类别
            if key == "occupation":
                category = "occupation"
            else:
                for cat, fields in self.info_categories.items():
                    if key in fields:
                        category = cat
                        break
            if not category:
                category = "custom"
                if isinstance(self.info_categories["custom"], list):
                    self.info_categories["custom"].append(key)
                else:
                    self.info_categories["custom"].add(key)
            if category not in categorized:
                categorized[category] = {}
            categorized[category][key] = value
        return categorized
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        从Redis获取用户信息
        
        Returns:
            用户信息字典，不存在则返回None
        """
        try:
            user_info_str = await get_key(self.user_info_key)
            if user_info_str:
                return json.loads(user_info_str)
            return None
        except Exception as e:
            logger.error(f"❌ 获取用户信息失败: {str(e)}")
            return None
    
    async def get_flat_user_info(self) -> Dict[str, Any]:
        """获取扁平化的用户信息（用于对话生成）"""
        try:
            info = await self.get_user_info()
            if not info:
                return {}
                
            # 扁平化信息
            flat_info = {}
            for category, fields in info.items():
                flat_info.update(fields)
            
            return flat_info
        except Exception as e:
            logger.error(f"❌ 获取扁平化用户信息失败: {str(e)}")
            return {}
    
    async def update_user_info(self, category: str, key: str, value: Any) -> bool:
        """
        更新用户信息的特定字段
        
        Args:
            category: 信息类别（如basic, preferences等）
            key: 信息字段名
            value: 信息值
            
        Returns:
            更新成功返回True，否则返回False
        """
        try:
            user_info = await self.get_user_info() or {}
            
            # 确保类别存在
            if category not in user_info:
                user_info[category] = {}
                
            # 更新字段值
            user_info[category][key] = value
            
            # 添加新字段到相应类别集合中
            if category in self.info_categories and key not in self.info_categories[category]:
                if category == "custom":
                    self.info_categories["custom"].add(key)
                
            # 永久保存信息
            return await set_key(self.user_info_key, json.dumps(user_info))
        except Exception as e:
            logger.error(f"❌ 更新用户信息失败: {str(e)}")
            return False
    
    async def add_preference(self, preference_type: str, value: str) -> bool:
        """
        添加用户偏好
        
        Args:
            preference_type: 偏好类型（如food, music等）
            value: 偏好值
            
        Returns:
            添加成功返回True，否则返回False
        """
        try:
            user_info = await self.get_user_info() or {}
            
            # 确保preferences类别存在
            if "preferences" not in user_info:
                user_info["preferences"] = {}
                
            # 对于偏好，我们保存为列表，以支持多个值
            if preference_type not in user_info["preferences"]:
                user_info["preferences"][preference_type] = []
                
            # 如果偏好值不在列表中，则添加
            if value not in user_info["preferences"][preference_type]:
                user_info["preferences"][preference_type].append(value)
                
            # 更新类别集合
            if preference_type not in self.info_categories["preferences"]:
                self.info_categories["preferences"].add(preference_type)
                
            # 永久保存信息
            return await set_key(self.user_info_key, json.dumps(user_info))
        except Exception as e:
            logger.error(f"❌ 添加用户偏好失败: {str(e)}")
            return False
    
    async def extract_user_info_from_message(self, message: str, llm_service=None) -> Dict[str, Any]:
        """
        从用户消息中提取可能的用户信息
        优先调用 LLM 结构化抽取，失败时再用规则兜底
        :param message: 用户消息
        :param llm_service: 可选，外部传入的大模型服务实例
        :return: 提取到的信息字典
        """
        # 1. 优先用 LLM 结构化抽取
        if llm_service is not None:
            try:
                prompt = (
                    "请从下面这段用户自述中，提取出所有能反映其身份、兴趣、职业、性格、偏好等信息，"
                    "并以JSON格式输出，字段包括：name, age, gender, occupation, hobby, personality, preference, ...。"
                    "如果没有某项信息可省略。例如：\n"
                    "用户自述：" + message + "\n"
                    "输出示例：{\"name\":\"托尼·斯塔克\",\"occupation\":\"发明家\",\"hobby\":\"研发高科技装备\",...}"
                )
                llm_result = await llm_service.generate([
                    {"role": "user", "content": prompt}
                ])
                # 解析 LLM 返回的 JSON
                import json
                content = llm_result.get("content", "")
                info = json.loads(content)
                if isinstance(info, dict) and info:
                    return info
            except Exception as e:
                logger.warning(f"[LLM抽取失败，回退规则] {e}")
        # 2. 规则兜底
        info = {}
        for field, patterns_list in self.extraction_patterns.items():
            for pattern_dict in patterns_list:
                patterns = pattern_dict.get("patterns", [])
                max_length = pattern_dict.get("max_length", 30)
                suffixes = pattern_dict.get("suffixes", [""])
                type_check = pattern_dict.get("type", None)
                keywords = pattern_dict.get("keywords", [])
                for pattern in patterns:
                    if pattern in message:
                        parts = message.split(pattern, 1)
                        if len(parts) <= 1:
                            continue
                        text_part = parts[1]
                        if keywords:
                            found_keyword = False
                            for keyword in keywords:
                                if keyword in text_part:
                                    if field == "gender":
                                        if keyword in ["男生", "男人", "男的"]:
                                            info[field] = "male"
                                        elif keyword in ["女生", "女人", "女的"]:
                                            info[field] = "female"
                                    else:
                                        info[field] = keyword
                                    found_keyword = True
                                    break
                            if found_keyword:
                                break
                            continue
                        value = text_part.split("，")[0].split("。")[0].split(",")[0].split(".")[0].strip()
                        if suffixes != [""]:
                            has_suffix = False
                            for suffix in suffixes:
                                if suffix in value:
                                    value = value.split(suffix)[0].strip()
                                    has_suffix = True
                                    break
                            if not has_suffix:
                                continue
                        if type_check == "number":
                            try:
                                num_match = re.search(r'\d+', value)
                                if num_match:
                                    num_value = int(num_match.group())
                                    max_value = pattern_dict.get("max_value", float('inf'))
                                    if num_value <= max_value:
                                        info[field] = num_value
                            except ValueError:
                                continue
                        elif type_check == "date":
                            date_pattern = r'\d{1,4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'
                            date_match = re.search(date_pattern, value)
                            if date_match:
                                info[field] = date_match.group()
                        else:
                            if 1 <= len(value) <= max_length:
                                info[field] = value
                                break
        return info
        
    async def extract_and_save_user_info(self, message: str) -> Dict[str, Any]:
        """
        从消息中提取用户信息并永久保存
        
        Args:
            message: 用户消息
            
        Returns:
            提取并保存的信息
        """
        info = await self.extract_user_info_from_message(message)
        if info:
            await self.save_user_info(info)
            logger.info(f"✅ 从消息中提取并永久保存了用户信息: {info}")
        return info
    
    async def clear_user_info(self) -> bool:
        """清除用户信息（仅用于测试）"""
        try:
            await set_key(self.user_info_key, "", 1)  # 设置为空并在1秒后过期
            return True
        except Exception as e:
            logger.error(f"❌ 清除用户信息失败: {str(e)}")
            return False
    
    async def export_user_info(self) -> str:
        """导出用户信息为JSON字符串"""
        user_info = await self.get_user_info()
        if user_info:
            return json.dumps(user_info, ensure_ascii=False, indent=2)
        return "{}"
    
    async def import_user_info(self, json_str: str) -> bool:
        """从JSON字符串导入用户信息"""
        try:
            user_info = json.loads(json_str)
            return await self.save_user_info(user_info)
        except Exception as e:
            logger.error(f"❌ 导入用户信息失败: {str(e)}")
            return False

# 单例模式
user_info_manager = UserInfoManager() 