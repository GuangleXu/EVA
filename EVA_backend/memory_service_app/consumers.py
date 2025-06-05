# EVA_backend/memory_service_app/consumers.py

import json
import asyncio
from typing import Dict, Optional, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from logs.logs import logger
from memory_service_app.utils.central_executive import central_executive, CentralExecutive
from memory_service_app.utils.redis_client import get_key, set_key, redis_client
from channels.layers import get_channel_layer
from channels.layers import BaseChannelLayer as ChannelLayerWrapper
from datetime import datetime

class MemoryConsumer(AsyncWebsocketConsumer):
    """记忆系统 WebSocket 消费者"""
    
    def __init__(self, *args, **kwargs):
        logger.info("🔄 MemoryConsumer 初始化完成")
        super().__init__(*args, **kwargs)
        self.channel_layer: Optional[ChannelLayerWrapper] = None
        self.central_executive = central_executive
        self.memory_lock = asyncio.Lock()
        self.group_name = "memory_group"  # 添加组名属性
        self.channel_layer = get_channel_layer()  # 显式初始化

    async def connect(self):
        """建立 WebSocket 连接"""
        try:
            await self.accept()
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            logger.info("✅ WebSocket 连接已建立")
        except Exception as e:
            logger.error(f"❌ WebSocket 连接失败: {e}")
            await self.close()

    async def disconnect(self, close_code):
        """断开 WebSocket 连接"""
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info("WebSocket 连接已断开")
        except Exception as e:
            logger.error(f"断开 WebSocket 连接时发生错误: {e}")

    async def receive(self, text_data):
        logger.info(f"📥 收到原始消息: {text_data}")
        try:
            data = json.loads(text_data)
            message_type = data.get("type")
            message_id = data.get("message_id", "unknown")

            if message_type == "retrieve_memory":
                user_message = data.get("user_message", "")
                logger.info(f"📩 收到记忆检索请求[{message_id}]: {user_message}")

                try:
                    # 使用锁防止并发检索
                    async with self.memory_lock:
                        # 检查是否已存在检索结果
                        memory_key = f"memory:{message_id}"
                        memory = await get_key(memory_key)
                        if memory:
                            logger.info(f"✅ 使用缓存的记忆[{message_id}]: {memory}")
                        else:
                            # 调用记忆检索
                            memory = await self._retrieve_memory_with_retry(message_id, user_message)
                            logger.info(f"✅ 记忆检索成功[{message_id}]: {memory}")

                        # 发送响应
                        await self.send(text_data=json.dumps({
                            "type": "memory_response",
                            "message_id": message_id,
                            "memory": memory
                        }))
                    
                except Exception as e:
                    logger.error(f"❌ 记忆检索失败[{message_id}]: {str(e)}", exc_info=True)
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message_id": message_id,
                        "error": f"记忆检索失败: {str(e)}"
                    }))

            elif message_type == "save_conversation":
                user_message = data.get("user_message", "")
                assistant_response = data.get("assistant_response", "")
                final_context = data.get("final_context", "")
                
                logger.info(f"💾 收到保存对话请求[{message_id}]")
                
                try:
                    # 构建对话上下文
                    conversation_context = {
                        "user_message": user_message,
                        "assistant_response": assistant_response,
                        "final_context": final_context,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 直接调用工作记忆模块保存对话
                    # await working_term_memory.add_messages(
                    #     input_text=conversation_context["user_message"],
                    #     response_text=conversation_context["assistant_response"]
                    # )
                    logger.info(f"✅ 对话保存成功[{message_id}]")
                    
                    await self.send(text_data=json.dumps({
                        "type": "save_success",
                        "message_id": message_id
                    }))
                    
                except Exception as e:
                    logger.error(f"❌ 对话保存失败[{message_id}]: {str(e)}", exc_info=True)
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message_id": message_id,
                        "error": f"对话保存失败: {str(e)}"
                    }))
            
            else:
                logger.warning(f"⚠️ 未知的消息类型[{message_id}]: {message_type}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "未知的消息类型"
                }))

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {str(e)}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "无效的消息格式"
            }))
        except Exception as e:
            logger.error(f"❌ 消息处理失败: {str(e)}", exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "消息处理失败"
            }))
    
    # 处理从llm_group发送过来的retrieve_memory事件
    async def retrieve_memory(self, event):
        logger.info(f"📩 收到channel层记忆检索请求[{event.get('message_id', 'unknown')}]: {event.get('user_message', '')}")
        
        try:
            message_id = event.get("message_id", "unknown")
            user_message = event.get("user_message", "")
            
            # 调试：特殊命令处理
            if "修复偏好记忆" in user_message or "重置偏好" in user_message:
                try:
                    # 提取用户想要记住的内容，默认使用示例
                    preference_content = "记住我的偏好"
                    if "记住" in user_message and "，" in user_message:
                        # 尝试提取"记住..."之后的内容作为偏好内容
                        parts = user_message.split("记住", 1)
                        if len(parts) > 1:
                            preference_content = f"记住{parts[1].strip()}"
                    else:
                        # 使用通用示例
                        preference_content = "记住我的重要偏好"
                    
                    metadata = {
                        "source": "user",
                        "priority": 0.9,
                        "emotion": json.dumps({"label": "喜爱", "intensity": 0.8})
                    }
                    
                    # 创建新规则
                    rule_id = await self.central_executive.rule_manager.store_rule(preference_content, metadata)
                    logger.info(f"✅ 创建新偏好规则: {rule_id}")
                    
                    # 生成响应
                    final_context = f"【系统维护】偏好规则已更新。现在系统记住了：{preference_content}"
                    
                    # 保存到Redis并通知LLM消费者
                    memory_key = f"memory:{message_id}"
                    await set_key(memory_key, final_context, ex=3600)
                    
                    # 通知LLM消费者规则已就绪
                    await self.channel_layer.group_send(
                        "llm_group",
                        {
                            "type": "memory_ready",
                            "message_id": message_id,
                            "final_context": final_context
                        }
                    )
                    # 跳过常规处理
                    return
                except Exception as e:
                    logger.error(f"❌ 创建偏好规则失败: {str(e)}", exc_info=True)
            
            # 使用锁防止并发检索
            async with self.memory_lock:
                # 检查是否已存在检索结果
                memory_key = f"memory:{message_id}"
                memory = await get_key(memory_key)
                if memory:
                    logger.info(f"✅ 使用缓存的记忆[{message_id}]: {memory}")
                    result = memory
                else:
                    # 调用记忆检索
                    try:
                        final_context = await self._retrieve_memory_with_retry(message_id, user_message)
                        logger.info(f"✅ 记忆检索成功[{message_id}]: {final_context[:50]}...")
                        result = final_context
                    except Exception as e:
                        logger.error(f"❌ 记忆检索失败[{message_id}]: {str(e)}", exc_info=True)
                        # 在失败的情况下，不阻止整个流程，返回空记忆
                        result = "系统记忆暂时不可用，将仅使用当前对话响应。"
                
                # 通知LLM消费者
                await self.channel_layer.group_send(
                    "llm_group",
                    {
                        "type": "memory_ready",
                        "message_id": message_id,
                        "final_context": result
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ 处理retrieve_memory事件失败: {str(e)}", exc_info=True)

    async def _retrieve_memory_with_retry(self, message_id: str, user_message: str, max_retries: int = 2) -> str:
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # 保存用户消息到 Redis
                user_msg_key = f"user_msg:{message_id}"
                await set_key(user_msg_key, user_message, ex=3600)
                
                # SecondMe 已替换原有记忆系统，此处 combine_context 调用已移除，无需再拼接上下文
                final_context = "系统记忆暂时不可用，将仅使用当前对话响应。"
                if not final_context:
                    logger.warning(f"[MemoryConsumer] 最终上下文为空")
                    return "系统记忆暂时不可用，将仅使用当前对话响应。"

                # 写入 Redis
                memory_key = f"memory:{message_id}"
                await set_key(memory_key, final_context, ex=3600)
                
                logger.info(f"[MemoryConsumer] 记忆检索成功，返回上下文大小: {len(final_context)} 字符")
                return final_context
                
            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning(f"[MemoryConsumer] 记忆检索失败 (尝试 {retry_count}/{max_retries+1}): {str(e)}")
                if retry_count <= max_retries:
                    await asyncio.sleep(0.5 * retry_count)  # 指数退避
                    
        # 所有重试都失败了
        logger.error(f"[MemoryConsumer] 记忆检索失败，已达到最大重试次数: {last_error}")
        
        # 返回一个基础上下文
        return "系统记忆暂时不可用，将仅使用当前对话响应。"

    async def save_conversation(self, event):
        logger.info(f"[DEBUG][save_conversation] 方法被调用，event: {event}")

        try:
            message_id = event.get("message_id", "")
            user_message = event.get("user_message", "")
            assistant_response = event.get("assistant_response", "")
            system_context = event.get("system_context", "")

            logger.info(f"[DEBUG][save_conversation] 参数: message_id={message_id}, user_message={user_message}, assistant_response={assistant_response}, system_context={system_context}")

            # 构建对话上下文
            conversation_context = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "system_context": system_context,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"[DEBUG][save_conversation] conversation_context: {conversation_context}")

            # 保存到工作记忆（如有需要可恢复）
            # await working_term_memory.add_messages(
            #     input_text=conversation_context["user_message"],
            #     response_text=conversation_context["assistant_response"]
            # )
            logger.info(f"[DEBUG][save_conversation] 即将调用 central_executive.process_input")
            try:
                process_result = await self.central_executive.process_input(user_message)
                logger.info(f"[DEBUG][save_conversation] central_executive.process_input 返回: {process_result}")
                if process_result:
                    stage = process_result.get("stage", "unknown")
                    logger.info(f"✅ 中央执行器处理完成 (message_id={message_id}), 阶段={stage}")
                else:
                    logger.warning(f"[DEBUG][save_conversation] process_input 返回 None 或空")
            except Exception as e:
                logger.error(f"❌ central_executive.process_input 调用异常: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"❌ save_conversation 主流程异常: {str(e)}", exc_info=True)

    def _format_memory_context(self, memory_result: Dict) -> str:
        """将记忆结果格式化为系统上下文（已废弃，仅保留兼容）"""
        try:
            return str(memory_result)
        except Exception as e:
            logger.error(f"❌ 记忆格式化失败: {str(e)}")
            return "记忆格式化失败，使用空上下文继续。"
