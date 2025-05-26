# EVA_backend/db/redis_client.py    

import os
import json
import asyncio
from typing import Optional, Any, Dict, Tuple
import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from logs.logs import logger
from memory_service_app.utils.system_notify import send_system_notification_to_frontend

# Redis配置
REDIS_CONFIG = {
    "connection": {
        "default_url": "redis://localhost:6379/0",
        "docker_url": "redis://127.0.0.1:6379/0",
        "env_var": "REDIS_URL",
        "max_retries": 3,
        "retry_delay": 0.5,  # 秒
    },
    "fallback": {
        "enabled": True,
        "memory_ttl": 3600,  # 本地内存缓存过期时间(秒)
        "max_items": 1000,   # 本地缓存最大条目数
    }
}

class RedisClient:
    """Redis 客户端封装类"""
    
    def __init__(self):
        """初始化 Redis 客户端"""
        self._client = None
        self._pool = None
        self._retry = Retry(ExponentialBackoff(), REDIS_CONFIG["connection"]["max_retries"])
        
        # 从环境变量获取Redis URL
        self._url = os.getenv(
            REDIS_CONFIG["connection"]["env_var"], 
            REDIS_CONFIG["connection"]["default_url"]
        )
        
        # 内存缓存，在Redis不可用时使用
        self._memory_cache = {}
        self._use_memory_fallback = False
        self._cache_stats = {"hits": 0, "misses": 0, "items": 0}
        self._hash_cache = {}  # 哈希表缓存
        logger.info(f"[RedisClient] 初始化，URL: {self._url}")
        
    async def get_client(self) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if not self._client:
            try:
                # 创建连接池
                self._pool = redis.ConnectionPool.from_url(
                    self._url,
                    decode_responses=True,
                    retry=self._retry,
                    retry_on_error=[ConnectionError, TimeoutError]
                )
                
                # 创建客户端
                self._client = redis.Redis.from_pool(self._pool)
                
                # 测试连接
                if not await self._test_connection():
                    # 如果Docker URL连接失败，尝试本地连接
                    if "127.0.0.1" in self._url:
                        local_url = REDIS_CONFIG["connection"]["default_url"]
                        logger.warning(f"Docker Redis连接失败，尝试本地连接: {local_url}")
                        
                        try:
                            # 关闭之前的连接
                            if self._client:
                                await self._client.aclose()
                            if self._pool:
                                await self._pool.aclose()
                                
                            # 尝试本地连接
                            self._pool = redis.ConnectionPool.from_url(
                                local_url,
                                decode_responses=True,
                                retry=self._retry
                            )
                            self._client = redis.Redis.from_pool(self._pool)
                            
                            # 再次测试连接
                            if await self._test_connection():
                                self._url = local_url
                                logger.info("✅ 切换到本地Redis连接成功")
                                await send_system_notification_to_frontend(
                                    message="【系统恢复】Redis 已恢复，记忆功能恢复正常。",
                                    level="success"
                                )
                            else:
                                self._use_memory_fallback = True
                                logger.warning("⚠️ 本地Redis连接也失败，将使用内存缓存")
                                await send_system_notification_to_frontend(
                                    message="【系统告警】本地 Redis 连接失败，系统将使用内存缓存，记忆功能不保证持久。",
                                    level="error"
                                )
                        except Exception as e:
                            logger.warning(f"⚠️ 本地Redis连接初始化失败: {e}")
                            self._use_memory_fallback = True
                            await send_system_notification_to_frontend(
                                message=f"【系统告警】本地 Redis 连接失败：{e}，系统将使用内存缓存。",
                                level="error"
                            )
                
            except Exception as e:
                logger.warning(f"⚠️ Redis 客户端初始化失败，将使用内存缓存: {e}")
                self._use_memory_fallback = True
                await send_system_notification_to_frontend(
                    message=f"【系统告警】Redis 客户端初始化失败：{e}，系统将使用内存缓存。",
                    level="error"
                )
                
        return self._client
    
    async def _test_connection(self) -> bool:
        """测试 Redis 连接"""
        try:
            if self._client:
                await self._client.ping()
                logger.info("✅ Redis 连接测试成功")
                return True
            return False
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接测试失败: {e}")
            self._use_memory_fallback = True
            return False
        
    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.aclose()
            
    def _clean_memory_cache_if_needed(self):
        """清理内存缓存"""
        # 如果缓存项超过限制，移除最旧的项
        if len(self._memory_cache) > REDIS_CONFIG["fallback"]["max_items"]:
            # 按时间戳排序，移除最旧的20%
            items_to_remove = int(REDIS_CONFIG["fallback"]["max_items"] * 0.2)
            sorted_items = sorted(
                self._memory_cache.items(), 
                key=lambda x: x[1].get("timestamp", 0)
            )
            
            for i in range(items_to_remove):
                if i < len(sorted_items):
                    key = sorted_items[i][0]
                    del self._memory_cache[key]
                    
            logger.info(f"已清理内存缓存中的 {items_to_remove} 项")
            
    async def get(self, key: str) -> Optional[str]:
        """获取键值"""
        # 如果使用内存缓存，直接从内存获取
        if self._use_memory_fallback:
            cache_item = self._memory_cache.get(key)
            if cache_item:
                value = cache_item.get("value")
                self._cache_stats["hits"] += 1
                logger.debug(f"Memory GET {key}: Hit")
                return value
            
            self._cache_stats["misses"] += 1
            logger.debug(f"Memory GET {key}: Miss")
            return None
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._get_from_memory(key)
                
            value = await client.get(key)
            if value:
                # 同步到内存缓存
                self._memory_cache[key] = {
                    "value": value,
                    "timestamp": asyncio.get_event_loop().time()
                }
                logger.debug(f"Redis GET {key}: {value[:100]}...")
            return value
        except Exception as e:
            # Redis 操作失败，尝试从内存缓存获取
            logger.warning(f"Redis GET 失败 {key}: {e}，尝试从内存缓存获取")
            self._use_memory_fallback = True
            await send_system_notification_to_frontend(
                message=f"【系统告警】Redis GET 操作失败：{e}，系统将使用内存缓存。",
                level="error"
            )
            return await self._get_from_memory(key)
    
    async def _get_from_memory(self, key: str) -> Optional[str]:
        """从内存缓存获取值"""
        cache_item = self._memory_cache.get(key)
        if cache_item:
            value = cache_item.get("value")
            self._cache_stats["hits"] += 1
            logger.debug(f"Memory GET {key}: Hit")
            return value
            
        self._cache_stats["misses"] += 1
        logger.debug(f"Memory GET {key}: Miss")
        return None
            
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置键值
        
        Args:
            key: 键名
            value: 值（会自动转换为 JSON 字符串）
            ex: 过期时间（秒）
        """
        # 标准化值
        string_value = self._normalize_value(value)
        
        # 如果使用内存缓存，直接写入内存
        if self._use_memory_fallback:
            success = await self._set_to_memory(key, string_value, ex)
            return success
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._set_to_memory(key, string_value, ex)
                
            result = await client.set(key, string_value, ex=ex)
            
            # 同时写入内存缓存，提高性能并作为备份
            await self._set_to_memory(key, string_value, ex)
            logger.debug(f"Redis SET {key}: {string_value[:100]}...")
            return result
        except Exception as e:
            # Redis 操作失败，写入内存缓存
            logger.warning(f"Redis SET 失败 {key}: {e}，尝试写入内存缓存")
            self._use_memory_fallback = True
            await send_system_notification_to_frontend(
                message=f"【系统告警】Redis SET 操作失败：{e}，系统将使用内存缓存。",
                level="error"
            )
            return await self._set_to_memory(key, string_value, ex)
            
    async def _set_to_memory(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """写入内存缓存
        
        Args:
            key: 键名
            value: 字符串值
            ex: 过期时间（秒）
        """
        try:
            timestamp = asyncio.get_event_loop().time()
            self._memory_cache[key] = {
                "value": value,
                "timestamp": timestamp,
                "expires": timestamp + (ex or REDIS_CONFIG["fallback"]["memory_ttl"])
            }
            
            # 清理缓存如需要
            self._clean_memory_cache_if_needed()
            self._cache_stats["items"] = len(self._memory_cache)
            logger.debug(f"Memory SET {key}: {value[:100]}...")
            return True
        except Exception as e:
            logger.error(f"内存缓存写入失败 {key}: {e}")
            return False
            
    def _normalize_value(self, value: Any) -> str:
        """将值标准化为字符串
        
        Args:
            value: 任意类型值
            
        Returns:
            str: 字符串值
        """
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except:
            return str(value)
            
    async def delete(self, key: str) -> bool:
        """删除键值"""
        # 从内存缓存删除
        if key in self._memory_cache:
            del self._memory_cache[key]
            
        if self._use_memory_fallback:
            logger.debug(f"Memory DEL {key}")
            return True
            
        try:
            client = await self.get_client()
            await client.delete(key)
            logger.debug(f"Redis DEL {key}")
            return True
        except Exception as e:
            logger.error(f"Redis DEL 失败 {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        # 检查内存缓存
        if key in self._memory_cache:
            # 检查是否过期
            cache_item = self._memory_cache[key]
            current_time = asyncio.get_event_loop().time()
            if "expires" in cache_item and cache_item["expires"] < current_time:
                # 已过期，删除并返回False
                del self._memory_cache[key]
                return False
            return True
            
        if self._use_memory_fallback:
            return False
            
        try:
            client = await self.get_client()
            return await client.exists(key)
        except Exception as e:
            logger.error(f"Redis EXISTS 失败 {key}: {e}")
            return False
            
    async def publish(self, channel: str, message: Any) -> bool:
        """发布消息到频道"""
        if self._use_memory_fallback:
            logger.warning(f"Redis不可用，无法发布消息到{channel}")
            return False
            
        try:
            client = await self.get_client()
            if not isinstance(message, str):
                message = json.dumps(message, ensure_ascii=False)
            await client.publish(channel, message)
            logger.debug(f"Redis PUBLISH {channel}: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Redis PUBLISH 失败 {channel}: {e}")
            return False
            
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        stats = {
            "memory_mode": self._use_memory_fallback,
            "cache_stats": self._cache_stats,
            "url": self._url
        }
        return stats

    # 哈希表操作
    async def hset(self, name: str, key: str, value: Any) -> int:
        """设置哈希表字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 值
            
        Returns:
            int: 新建字段数
        """
        # 标准化值
        string_value = self._normalize_value(value)
        
        # 内存回退模式
        if self._use_memory_fallback:
            return await self._hset_to_memory(name, key, string_value)
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._hset_to_memory(name, key, string_value)
                
            result = await client.hset(name, key, string_value)
            
            # 同步到内存缓存
            await self._hset_to_memory(name, key, string_value)
            
            logger.debug(f"Redis HSET {name}:{key}")
            return result
        except Exception as e:
            logger.warning(f"Redis HSET 失败 {name}:{key}: {e}")
            self._use_memory_fallback = True
            return await self._hset_to_memory(name, key, string_value)
    
    async def _hset_to_memory(self, name: str, key: str, value: str) -> int:
        """写入内存哈希表缓存
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 值
            
        Returns:
            int: 新建字段数 (0 or 1)
        """
        try:
            # 初始化哈希表
            if name not in self._hash_cache:
                self._hash_cache[name] = {}
                is_new = 1
            else:
                is_new = 0 if key in self._hash_cache[name] else 1
                
            # 写入值
            self._hash_cache[name][key] = value
            logger.debug(f"Memory HSET {name}:{key}")
            
            return is_new
        except Exception as e:
            logger.error(f"内存哈希表写入失败 {name}:{key}: {e}")
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希表字段值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            str: 字段值 (如果存在)
        """
        # 内存回退模式
        if self._use_memory_fallback:
            return await self._hget_from_memory(name, key)
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._hget_from_memory(name, key)
                
            value = await client.hget(name, key)
            
            # 同步到内存缓存
            if value is not None:
                if name not in self._hash_cache:
                    self._hash_cache[name] = {}
                self._hash_cache[name][key] = value
                
            logger.debug(f"Redis HGET {name}:{key}")
            return value
        except Exception as e:
            logger.warning(f"Redis HGET 失败 {name}:{key}: {e}")
            self._use_memory_fallback = True
            return await self._hget_from_memory(name, key)
    
    async def _hget_from_memory(self, name: str, key: str) -> Optional[str]:
        """从内存哈希表缓存获取值
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            str: 字段值 (如果存在)
        """
        try:
            if name not in self._hash_cache:
                return None
                
            value = self._hash_cache[name].get(key)
            if value is not None:
                logger.debug(f"Memory HGET {name}:{key}: Hit")
                self._cache_stats["hits"] += 1
            else:
                logger.debug(f"Memory HGET {name}:{key}: Miss")
                self._cache_stats["misses"] += 1
                
            return value
        except Exception as e:
            logger.error(f"内存哈希表读取失败 {name}:{key}: {e}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """获取哈希表所有字段和值
        
        Args:
            name: 哈希表名
            
        Returns:
            Dict[str, str]: 字段名和值组成的字典
        """
        # 内存回退模式
        if self._use_memory_fallback:
            return await self._hgetall_from_memory(name)
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._hgetall_from_memory(name)
                
            result = await client.hgetall(name)
            
            # 同步到内存缓存
            if result:
                if name not in self._hash_cache:
                    self._hash_cache[name] = {}
                self._hash_cache[name].update(result)
                
            logger.debug(f"Redis HGETALL {name}: {len(result)} 项")
            return result
        except Exception as e:
            logger.warning(f"Redis HGETALL 失败 {name}: {e}")
            self._use_memory_fallback = True
            return await self._hgetall_from_memory(name)
    
    async def _hgetall_from_memory(self, name: str) -> Dict[str, str]:
        """从内存哈希表缓存获取所有值
        
        Args:
            name: 哈希表名
            
        Returns:
            Dict[str, str]: 字段名和值组成的字典
        """
        try:
            if name not in self._hash_cache:
                return {}
                
            result = self._hash_cache[name].copy()
            logger.debug(f"Memory HGETALL {name}: {len(result)} 项")
            self._cache_stats["hits"] += 1
            
            return result
        except Exception as e:
            logger.error(f"内存哈希表读取失败 {name}: {e}")
            return {}
    
    async def hdel(self, name: str, *keys) -> int:
        """删除哈希表字段
        
        Args:
            name: 哈希表名
            *keys: 要删除的字段名
            
        Returns:
            int: 删除的字段数量
        """
        # 从内存缓存删除
        deleted = 0
        if name in self._hash_cache:
            for key in keys:
                if key in self._hash_cache[name]:
                    del self._hash_cache[name][key]
                    deleted += 1
            
        if self._use_memory_fallback:
            logger.debug(f"Memory HDEL {name}: {deleted} 项")
            return deleted
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return deleted
                
            result = await client.hdel(name, *keys)
            logger.debug(f"Redis HDEL {name}: {result} 项")
            return result
        except Exception as e:
            logger.warning(f"Redis HDEL 失败 {name}: {e}")
            self._use_memory_fallback = True
            return deleted
    
    async def hexists(self, name: str, key: str) -> bool:
        """判断哈希表字段是否存在
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            bool: 是否存在
        """
        # 内存回退模式
        if self._use_memory_fallback:
            return await self._hexists_in_memory(name, key)
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._hexists_in_memory(name, key)
                
            result = await client.hexists(name, key)
            logger.debug(f"Redis HEXISTS {name}:{key}: {result}")
            return result
        except Exception as e:
            logger.warning(f"Redis HEXISTS 失败 {name}:{key}: {e}")
            self._use_memory_fallback = True
            return await self._hexists_in_memory(name, key)
    
    async def _hexists_in_memory(self, name: str, key: str) -> bool:
        """判断内存哈希表缓存中字段是否存在
        
        Args:
            name: 哈希表名
            key: 字段名
            
        Returns:
            bool: 是否存在
        """
        try:
            if name not in self._hash_cache:
                return False
                
            result = key in self._hash_cache[name]
            logger.debug(f"Memory HEXISTS {name}:{key}: {result}")
            return result
        except Exception as e:
            logger.error(f"内存哈希表查询失败 {name}:{key}: {e}")
            return False
    
    async def hlen(self, name: str) -> int:
        """获取哈希表字段数量
        
        Args:
            name: 哈希表名
            
        Returns:
            int: 字段数量
        """
        # 内存回退模式
        if self._use_memory_fallback:
            return await self._hlen_from_memory(name)
            
        try:
            client = await self.get_client()
            if self._use_memory_fallback:
                return await self._hlen_from_memory(name)
                
            result = await client.hlen(name)
            logger.debug(f"Redis HLEN {name}: {result}")
            return result
        except Exception as e:
            logger.warning(f"Redis HLEN 失败 {name}: {e}")
            self._use_memory_fallback = True
            return await self._hlen_from_memory(name)
    
    async def _hlen_from_memory(self, name: str) -> int:
        """获取内存哈希表缓存字段数量
        
        Args:
            name: 哈希表名
            
        Returns:
            int: 字段数量
        """
        try:
            if name not in self._hash_cache:
                return 0
                
            result = len(self._hash_cache[name])
            logger.debug(f"Memory HLEN {name}: {result}")
            return result
        except Exception as e:
            logger.error(f"内存哈希表计数失败 {name}: {e}")
            return 0

# 全局 Redis 客户端实例
redis_client = RedisClient()

# 为了兼容旧代码，提供直接调用的函数
async def set_key(key: str, value: Any, ex: Optional[int] = None) -> bool:
    """兼容旧代码的 set_key 函数"""
    return await redis_client.set(key, value, ex)

async def get_key(key: str) -> Optional[str]:
    """兼容旧代码的 get_key 函数"""
    return await redis_client.get(key)

async def init_redis():
    """初始化 Redis 连接"""
    await redis_client.get_client()

async def close_redis():
    """关闭 Redis 连接"""
    await redis_client.close()
