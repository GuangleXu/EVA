# -*- coding: utf-8 -*-
"""
记忆归纳总结模块
用于对用户的长期记忆、规则记忆等内容做自动归纳、聚类、标签提取
"""
from typing import List, Dict, Any
import json
import asyncio
from logs.logs import logger

class MemorySummary:
    """
    记忆归纳总结模块
    用于对用户的长期记忆、规则记忆等内容做自动归纳、聚类、标签提取
    """
    def __init__(self, llm_service):
        """
        初始化，传入大语言模型服务实例
        """
        self.llm_service = llm_service

    async def summarize_memories(self, memories: List[str]) -> Dict[str, Any]:
        """
        对记忆内容做摘要、聚类、标签提取（异步调用LLM）
        :param memories: 记忆内容列表
        :return: 归纳结果，包括摘要、标签、兴趣、规则等
        """
        try:
            text = "\n".join(memories)
            prompt = (
                "请对以下用户记忆内容做归纳总结，提取兴趣、习惯、底线规则、偏好、常用表达等标签：\n"
                f"{text}\n"
                "请用简洁的中文输出，格式为：\n"
                "兴趣: ...\n习惯: ...\n底线规则: ...\n偏好: ...\n常用表达: ...\n"
            )
            # 增加超时处理
            result = await asyncio.wait_for(self.llm_service.generate([{"role": "user", "content": prompt}]), timeout=10)
            summary_text = result.get("content", "")
            tags = self.extract_tags(summary_text)
            return {
                "summary": summary_text,
                "tags": tags
            }
        except asyncio.TimeoutError:
            logger.error("❌ 记忆归纳超时")
            return {"summary": "", "tags": []}
        except Exception as e:
            logger.error(f"❌ 记忆归纳失败: {e}")
            return {"summary": "", "tags": []}

    def extract_tags(self, summary_text: str) -> List[str]:
        """
        从 LLM 归纳文本中提取标签
        :param summary_text: LLM输出的归纳文本
        :return: 标签列表
        """
        tags = []
        for line in summary_text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                tags.append(f"{key.strip()}:{value.strip()}")
        return tags

    def save_summary(self, user_id: str, summary: Dict[str, Any]):
        """
        保存归纳结果（可存数据库或本地文件）
        :param user_id: 用户ID
        :param summary: 归纳结果
        """
        with open(f"user_{user_id}_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    # 示例：如何异步调用 summarize_memories
    # import asyncio
    # summary = MemorySummary(llm_service)
    # result = asyncio.run(summary.summarize_memories(["记忆1", "记忆2"]))
    # print(result) 