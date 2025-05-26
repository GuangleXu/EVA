# -*- coding: utf-8 -*-
"""
定时任务模块
负责定时自动归纳记忆、更新用户画像、行为策略等（推荐Celery调度）
"""
from celery import shared_task
from master_evolution.memory_summary import MemorySummary
from master_evolution.user_info_manager import UserInfoManager
from master_evolution.behavior_adapt import BehaviorAdapt
from master_evolution.master_improvement import MasterImprovement
from llm_manager_app.utils.llm_service import llm_service
import asyncio
from logs.logs import logger

@shared_task(bind=True)
def summarize_and_update_profile(self, user_ids: list):
    """
    定时批量归纳多个用户记忆并更新画像的Celery任务
    :param user_ids: 用户ID列表
    """
    # 1. 批量拉取用户记忆（实际应查数据库，这里用假数据）
    user_memories = {uid: ["我喜欢喝咖啡", "遇到紧急情况必须先报警", "请记住我喜欢安静的环境"] for uid in user_ids}

    # 2. 归纳记忆（异步调用 LLM，支持缓存）
    async def async_flow():
        summary = MemorySummary(llm_service)
        user_manager = UserInfoManager()
        for user_id, memories in user_memories.items():
            try:
                # 可在此处增加LLM调用缓存机制，避免重复归纳
                result = await summary.summarize_memories(memories)
                # 3. 更新用户画像
                user_profile = user_manager.get_user_profile(user_id)
                user_profile.update(result)  # 合并归纳标签
                user_manager.save_user_profile(user_id, user_profile)
                # 4. 行为策略自适应（异步 LLM）
                behavior = BehaviorAdapt()
                strategy = await behavior.get_behavior_strategy_by_llm(user_profile, llm_service)
                # 5. 检查画像空白并生成提问（异步 LLM）
                improvement = MasterImprovement()
                questions = await improvement.generate_questions_by_llm(user_profile, llm_service)
                # 6. 可将策略和提问结果写入数据库或推送给用户
                print(f"用户{user_id}画像已更新，当前策略: {strategy}，待补全: {questions}")
            except Exception as e:
                # 记录异常日志，可集成告警系统
                print(f"[告警] 用户{user_id}画像处理异常: {e}")
                # 可在此处集成邮件/短信/钉钉等告警通知
    # 启动异步流程
    asyncio.run(async_flow())

# 示例：如何在 Celery 任务中异步调用 LLM 相关方法
# summarize_and_update_profile.delay('user123')
# 任务会自动异步归纳记忆、更新画像、生成行为策略和提问 