# EVA_backend/llm_manager_app/consumers.py

import asyncio
import json
import uuid
import re  # 新增正则库
from typing import Dict, Optional
from channels.generic.websocket import AsyncWebsocketConsumer
from logs.logs import logger
from llm_manager_app.utils.llm_service import llm_service, Message
from memory_service_app.utils.redis_client import set_key, get_key  # ✅ 引入 Redis 客户端方法
from master_evolution.user_info_manager import user_info_manager
import logging
import time

class LLMConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        logging.debug("【DEBUG】LLMConsumer.__init__ 被调用")
        super().__init__(*args, **kwargs)
        self.llm_service = llm_service
        self.group_name = "llm_group"
        logger.info("🔄 LLMConsumer 初始化完成")

    async def connect(self):
        """建立 WebSocket 连接"""
        try:
            # 加入 llm_group 组
            logger.info("🔄 准备加入 llm_group...")
            if not self.channel_layer:
                raise RuntimeError("channel_layer 未初始化")
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            logger.info(f"✅ 已加入 llm_group: {self.channel_name}")
            
            # 接受连接
            await self.accept()
            logger.info(f"🟢 LLMConsumer 连接成功: {self.channel_name}")
            
            # 发送连接成功消息，type统一为system
            await self.send(text_data=json.dumps({
                "type": "system",
                "message": "LLMConsumer 已连接"
            }))
            
        except Exception as e:
            logger.error(f"❌ LLMConsumer 连接失败: {str(e)}", exc_info=True)
            raise

    async def disconnect(self, close_code):
        """断开 WebSocket 连接"""
        try:
            # 离开 llm_group 组
            logger.info("🔄 准备离开 llm_group...")
            if not self.channel_layer:
                raise RuntimeError("channel_layer 未初始化")
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"✅ 已离开 llm_group: {self.channel_name}")
            logger.info(f"🔴 LLMConsumer 断开连接: {close_code}")
        except Exception as e:
            logger.error(f"❌ LLMConsumer 断开连接失败: {str(e)}", exc_info=True)

    async def receive(self, text_data):
        """接收前端 WebSocket 消息"""
        logging.debug(f"【DEBUG】LLMConsumer.receive 被调用，text_data: {text_data}")
        try:
            logger.info(f"📥 收到原始消息: {text_data}")
            data = json.loads(text_data)
            message_type = data.get("type")

            # 处理心跳消息
            if message_type == "heartbeat":
                logger.debug("💓 收到 WebSocket 心跳")
                await self.send(text_data=json.dumps({"type": "pong"}))
                return

            # 处理用户消息
            if message_type == "message":
                message_id = data.get("message_id", str(uuid.uuid4()))
                user_message = data.get("message", "").strip()
                api_choice = data.get("api_choice", "deepseek")  # 默认使用 deepseek
                need_speech = data.get("need_speech", False)
                voice_index = data.get("voice_index", 0)

                if not user_message:
                    logger.warning("⚠️ 无效的 LLM 请求: 消息为空")
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": "消息不能为空"
                    }))
                    return

                logger.info(f"📩 收到用户输入[{message_id}]: {user_message}")

                try:
                    # 提取并保存用户信息(新增)
                    extracted_info = await user_info_manager.extract_and_save_user_info(user_message)
                    if extracted_info:
                        logger.info(f"✅ 从用户消息中提取到信息: {extracted_info}")

                    # 将用户消息存入 Redis
                    logger.info(f"💾 开始存储用户消息到 Redis (message_id={message_id})")
                    await set_key(f"user_msg:{message_id}", user_message)
                    logger.info(f"✅ 用户消息已存入 Redis (message_id={message_id})")

                    # 向 memory_group 发送消息，请求相关记忆
                    logging.debug(f"【DEBUG】LLMConsumer.group_send memory_group: message_id={message_id}, user_message={user_message}")
                    await self.channel_layer.group_send(
                        "memory_group",
                        {
                            "type": "retrieve_memory",
                            "message_id": message_id,
                            "user_message": user_message
                        }
                    )
                    logger.info(f"✅ 记忆请求已发送到 memory_group (message_id={message_id})")

                    # 等待记忆检索完成
                    logging.debug(f"【DEBUG】LLMConsumer._wait_for_memory 调用: message_id={message_id}")
                    final_context = await self._wait_for_memory(message_id)
                    logger.info(f"✅ 记忆检索完成 (message_id={message_id})")
                    
                    # 生成完整回答
                    logger.info(f"🤖 开始生成 LLM 回答 (message_id={message_id})")
                    response = await self._generate_llm_response({
                        "user_message": user_message,
                        "final_context": final_context,
                        "api_choice": api_choice
                    })
                    logger.info(f"✅ LLM 回答生成完成 (message_id={message_id})")

                    # === 自动过滤括号内容（动作/表情/拟人化）===
                    # 过滤所有中文/英文括号内内容
                    response = re.sub(r"[（(][^）)]*[）)]", "", response)
                    # 去除多余空格
                    response = re.sub(r"\s+", " ", response).strip()
                    logger.info(f"✅ 已过滤括号内容后的回复: {response}")

                    # 如果需要语音
                    logger.info(f"[TTS-DEBUG] need_speech={need_speech}, response={response}, voice_index={voice_index}")
                    speech_url = None
                    if need_speech:
                        try:
                            from speech.speech_manager import SpeechManager
                            speech_manager = SpeechManager()
                            logger.info(f"[TTS-DEBUG] SpeechManager 初始化成功，准备生成语音...")
                            speech_url = await speech_manager.generate_speech(
                                response,
                                voice_index=voice_index
                            )
                            logger.info(f"✅ 语音生成完成: {speech_url}")
                        except Exception as e:
                            logger.error(f"❌ 语音生成失败: {str(e)}", exc_info=True)
                            import traceback
                            logger.error(traceback.format_exc())
                    logger.info(f"[TTS-DEBUG] speech_url={speech_url}")
                    
                    logger.info(f"📤 准备发送响应给用户 (message_id={message_id})")
                    await self.send(text_data=json.dumps({
                        "type": "response",
                        "message_id": message_id,
                        "response": response,
                        "context": final_context,
                        "speech_url": speech_url
                    }))
                    logger.info(f"✅ 响应已发送给用户 (message_id={message_id})")

                    # 将对话发送给 MemoryConsumer 保存到工作记忆
                    logging.debug(f"【DEBUG】LLMConsumer.group_send memory_group: message_id={message_id}, user_message={user_message}, response={response}, final_context={final_context}")
                    await self.channel_layer.group_send(
                        "memory_group",
                        {
                            "type": "save_conversation",
                            "message_id": message_id,
                            "user_message": user_message,
                            "assistant_response": response,
                            "final_context": final_context
                        }
                    )
                    logger.info(f"✅ 对话已发送到 memory_group 等待保存 (message_id={message_id})")

                except Exception as e:
                    logger.error(f"❌ 生成响应失败: {str(e)}", exc_info=True)
                    await self.send(text_data=json.dumps({
                        "type": "error",
                        "message": f"生成响应失败: {str(e)}"
                    }))
            else:
                logger.warning(f"⚠️ 未知的消息类型: {message_type}")
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
                "message": f"消息处理失败: {str(e)}"
            }))

    async def _wait_for_memory(self, message_id: str, timeout: float = 5.0):
        """等待记忆检索完成"""
        logging.debug(f"【DEBUG】LLMConsumer._wait_for_memory 被调用，message_id: {message_id}, timeout: {timeout}")
        try:
            memory_key = f"memory:{message_id}"
            logger.info(f"⏳ 开始等待记忆 (message_id={message_id})")
            start_time = time.time()
            while True:
                logger.debug(f"🔄 尝试获取记忆 (message_id={message_id})")
                memory = await get_key(memory_key)
                logger.info(f"[LLMConsumer] 从 Redis 读取到的记忆内容 (key={memory_key}): {memory}")
                if memory:
                    logger.info(f"✅ 成功获取记忆 (message_id={message_id})")
                    return memory
                if time.time() - start_time > timeout:
                    logger.warning(f"⏳ 记忆检索超时 (message_id={message_id})")
                    return "记忆检索超时，使用默认上下文继续。"
                logger.debug(f"⏳ 记忆尚未就绪，继续等待 (message_id={message_id})")
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ 等待记忆检索失败: {str(e)}", exc_info=True)
            return "记忆检索失败，使用默认上下文继续。"

    async def _generate_llm_response(self, data: Dict) -> str:
        """生成LLM回答，自动解析final_context并分块注入prompt"""
        try:
            user_message = data["user_message"]
            # 获取用户个性化信息
            try:
                user_info = await user_info_manager.get_flat_user_info()
                if user_info:
                    logger.info(f"✅ 已获取用户扁平化信息用于个性化对话：{list(user_info.keys())}")
            except Exception as e:
                logger.warning(f"⚠️ 获取扁平化用户信息失败，将使用默认对话风格: {str(e)}")
                user_info = {}

            # 解析 final_context，分块注入
            final_context = data.get("final_context", "")
            rules_block = ""
            conversation_block = ""
            memory_block = ""
            # 用正则分块提取
            import re
            rules_match = re.search(r"【系统规则】([\s\S]*?)(?=【|$)", final_context)
            if rules_match:
                rules_block = rules_match.group(1).strip()
            conversation_match = re.search(r"【最近对话】([\s\S]*?)(?=【|$)", final_context)
            if conversation_match:
                conversation_block = conversation_match.group(1).strip()
            memory_match = re.search(r"【相关记忆】([\s\S]*?)(?=【|$)", final_context)
            if memory_match:
                memory_block = memory_match.group(1).strip()

            # 组装 prompt
            from prompts.prompt import build_eva_prompt
            context = await build_eva_prompt(
                user_message=user_message,
                conversation_history=conversation_block,
                memory_context=memory_block,
                user_info=user_info
            )
            # 如有规则，拼进 constraints
            if rules_block:
                context = f"系统规则：\n{rules_block}\n\n" + context

            logger.info(f"[DEBUG] 传递给 LLM 的 system prompt 内容: {context}")
            messages = [Message(role="user", content=user_message)]
            messages.insert(0, Message(role="system", content=context))
            api_choice = data.get("api_choice", "deepseek")
            self.llm_service.current_provider = api_choice
            logger.info(f"🔄 设置LLM提供商: {api_choice}")
            logger.info(f"📝 发送给 LLM 的 prompt: {[m.to_dict() for m in messages]}")
            response = await self.llm_service.generate(messages=messages)
            if isinstance(response, dict) and "content" in response:
                return response.get("content", "暂时无法回答") 
            elif hasattr(response, "generations") and response.generations:
                return response.generations[0].message.content
            else:
                logger.warning(f"⚠️ 未知的响应格式: {type(response)}")
                return "暂时无法回答(响应格式错误)"
        except Exception as e:
            logger.error(f"❌ 生成LLM回答失败: {str(e)}", exc_info=True)
            raise

    # 处理 memory_group 返回的记忆检索结果
    async def process_memory_response(self, event):
        """
        处理来自 memory_group 的记忆检索结果
        """
        logging.debug(f"【DEBUG】LLMConsumer.process_memory_response 被调用，event: {event}")
        logger.info(f"📥 收到 memory_group 的记忆检索结果: {event}")
        # 这里可以根据实际业务需求处理 event 内容
        await self.send(text_data=json.dumps({
            "type": "memory_response",
            "final_context": event.get("final_context", ""),
            "message_id": event.get("message_id", "")
        }))
        
    # 处理 memory_ready 消息
    async def memory_ready(self, event):
        """
        处理来自 memory_group 的 memory_ready 消息
        在 MemoryConsumer 中通过 memory_ready 消息通知 LLMConsumer 记忆已准备好
        """
        logging.debug(f"【DEBUG】LLMConsumer.memory_ready 被调用，event: {event}")
        logger.info(f"📥 收到 memory_ready 消息: {event}")
        message_id = event.get("message_id")
        final_context = event.get("final_context")
        
        # 将记忆内容写入Redis
        memory_key = f"memory:{message_id}"
        await set_key(memory_key, final_context, ex=3600)
        
        logger.info(f"✅ 记忆已准备就绪 (message_id={message_id})")
        
        # 可以选择通知前端记忆已就绪
        # await self.send(text_data=json.dumps({
        #     "type": "memory_ready",
        #     "message_id": message_id
        # }))

    async def system_message(self, event):
        """处理后端推送的系统通知，直接转发到前端聊天窗口（如红色系统消息）"""
        await self.send(text_data=json.dumps({
            "type": "system",
            "message": event.get("message", "系统通知"),
            "level": event.get("level", "info")
        }))
