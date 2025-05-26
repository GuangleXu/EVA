# -*- coding: utf-8 -*-
"""
主控自我优化模块
负责定期检测画像空白、知识盲区，主动生成提问或自我补全任务，记录反馈并自我优化
"""
from typing import Dict, Any, List
from logs.logs import logger

class MasterImprovement:
    """
    主控自我优化与主动学习模块
    """
    def __init__(self):
        pass

    def find_profile_gaps(self, user_profile: Dict[str, Any]) -> List[str]:
        """
        检测用户画像中的空白点或模糊点
        :param user_profile: 用户画像字典，格式如{"兴趣": "...", "习惯": "..."}
        :return: 需要补全的标签列表
        """
        required_tags: List[str] = ["兴趣", "习惯", "底线规则", "偏好"]
        gaps: List[str] = []
        for tag in required_tags:
            if tag not in user_profile or not user_profile[tag]:
                gaps.append(tag)
        return gaps

    def generate_questions(self, gaps: List[str]) -> List[str]:
        """
        针对画像空白点生成主动提问
        :param gaps: 需要补全的标签列表
        :return: 提问列表，每个元素为字符串
        """
        questions: List[str] = []
        for gap in gaps:
            if gap == "兴趣":
                questions.append("你平时有什么兴趣爱好吗？")
            elif gap == "习惯":
                questions.append("你有哪些日常习惯或作息规律？")
            elif gap == "底线规则":
                questions.append("你有哪些原则或底线是我必须遵守的？")
            elif gap == "偏好":
                questions.append("你在饮食、娱乐等方面有什么特别偏好吗？")
        return questions

    def record_feedback(self, user_profile: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        记录用户反馈，自动补全或优化画像
        :param user_profile: 用户画像字典
        :param feedback: 用户补全/纠正内容
        :return: 更新后的用户画像
        """
        for key, value in feedback.items():
            user_profile[key] = value
        return user_profile

    async def generate_questions_by_llm(self, user_profile: Dict[str, Any], llm_service) -> list:
        """
        用 LLM 根据用户画像生成更智能的主动提问（异步接口）
        :param user_profile: 用户画像字典
        :param llm_service: LLM服务实例，需支持 async/await
        :return: 智能提问列表
        """
        import json
        prompt = (
            "请根据以下用户画像，列出你还想进一步了解的5个问题，问题要简洁明了：\n"
            f"{json.dumps(user_profile, ensure_ascii=False)}"
        )
        result = await llm_service.generate([{"role": "user", "content": prompt}])
        content = result.get("content", "")
        # 按行分割为问题列表
        questions = [line.strip() for line in content.splitlines() if line.strip()]
        return questions

    # 示例：如何异步调用 generate_questions_by_llm
    # import asyncio
    # improvement = MasterImprovement()
    # questions = asyncio.run(improvement.generate_questions_by_llm(user_profile, llm_service))
    # print(questions) 