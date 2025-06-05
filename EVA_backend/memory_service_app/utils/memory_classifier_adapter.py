import os
import httpx
from logs.logs import logger


class SecondMeMemoryAdapter:
    """
    🧠 SecondMe 记忆系统适配器
    用于统一对接 SecondMe 的嵌入式记忆 API（包括存储与检索）
    """

    def __init__(self):
        self.api_host = os.environ.get("SECONDME_API_URL", "http://localhost:8002")
        self.chat_url = f"{self.api_host}/api/kernel2/chat"
        self.search_url = f"{self.api_host}/api/memory/search"
        logger.info(f"[SecondMeAdapter] 初始化成功，Chat 接口: {self.chat_url}")

    async def add_memory(self, user_input: str, system_prompt: str = "你是一个有记忆的助手。"):
        """
        将用户输入通过对话格式写入 SecondMe 系统，让其自动融合上下文并学习。
        :param user_input: 用户内容
        :param system_prompt: 系统提示词（可选）
        :return: 响应结果（生成内容或写入结果）
        """
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            "stream": False
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.chat_url, json=data, timeout=15)
                resp.raise_for_status()
                logger.debug(f"[SecondMeAdapter] ✅ 添加记忆成功: {user_input[:30]}...")
                return resp.json()
        except Exception as e:
            logger.error(f"[SecondMeAdapter] ❌ 添加记忆失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_memory(self, query: str, top_k: int = 5):
        """
        从 SecondMe 系统中检索语义相似记忆内容
        :param query: 查询文本
        :param top_k: 返回结果数
        :return: 检索结果列表
        """
        params = {"query": query, "top_k": top_k}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.search_url, params=params, timeout=10)
                resp.raise_for_status()
                logger.debug(f"[SecondMeAdapter] ✅ 检索记忆成功: {query}")
                return resp.json()
        except Exception as e:
            logger.error(f"[SecondMeAdapter] ❌ 检索记忆失败: {e}")
            return {"success": False, "error": str(e)}

# 兼容旧代码的类名别名
MemoryClassifierAdapter = SecondMeMemoryAdapter
