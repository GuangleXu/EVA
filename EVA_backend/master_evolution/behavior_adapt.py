# -*- coding: utf-8 -*-
"""
行为自适应模块
根据用户画像、记忆标签等，动态调整EVA的对话风格、推荐策略、决策逻辑
"""
from typing import Dict, Any
from logs.logs import logger

class BehaviorAdapt:
    """
    行为自适应主控模块
    """
    def __init__(self):
        # 可扩展：加载行为策略模板、规则等
        self.default_strategy = {
            "reply_style": "normal",  # normal/concise/friendly/strict
            "recommendation": "default",  # default/personalized
            "decision_mode": "standard"  # standard/conservative/aggressive
        }

    def get_behavior_strategy(self, user_profile: Dict[str, Any]) -> Dict[str, str]:
        """
        根据用户画像动态生成行为策略
        :param user_profile: 用户画像字典
        :return: 行为策略字典，格式如{"reply_style": "normal", ...}
        """
        strategy: Dict[str, str] = self.default_strategy.copy()
        tags = user_profile.get("tags", [])
        # 优先级：简洁 > 友好 > 严格 > 推荐
        if any("简洁" in tag for tag in tags):
            strategy["reply_style"] = "concise"
        elif any("友好" in tag for tag in tags):
            strategy["reply_style"] = "friendly"
        if any("严格" in tag or "底线" in tag for tag in tags):
            strategy["decision_mode"] = "conservative"
        if any("喜欢推荐" in tag for tag in tags):
            strategy["recommendation"] = "personalized"
        return strategy

    async def get_behavior_strategy_by_llm(self, user_profile: Dict[str, Any], llm_service) -> str:
        """
        用 LLM 根据用户画像生成更智能的行为策略建议（异步接口）
        :param user_profile: 用户画像字典
        :param llm_service: LLM服务实例，需支持 async/await
        :return: 智能行为策略建议文本
        """
        import json
        prompt = (
            "请根据以下用户画像，推荐最适合的对话风格和行为策略，简要说明理由：\n"
            f"{json.dumps(user_profile, ensure_ascii=False)}"
        )
        result = await llm_service.generate([{"role": "user", "content": prompt}])
        return result.get("content", "")

    # 示例：如何异步调用 get_behavior_strategy_by_llm
    # import asyncio
    # adapt = BehaviorAdapt()
    # strategy = asyncio.run(adapt.get_behavior_strategy_by_llm(user_profile, llm_service))
    # print(strategy) 