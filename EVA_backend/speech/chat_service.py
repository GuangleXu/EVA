# speech/chat_service.py
from logs.logs import logger
from llm_manager_app.utils.llm_service import llm_service, Message
from speech.speech_manager import SpeechManager
from django.conf import settings
import traceback
import json

async def process_message(self, user_message):
    """
    处理用户消息并生成文本和语音回复。
    """
    try:
        # 初始化LLM服务
        await llm_service.initialize()
        
        # 构建消息并生成回复
        messages = [
            Message(role="user", content=user_message)
        ]
        response = await llm_service.generate(
            messages=messages,
            provider="siliconflow"
        )
        response_text = response.get("content", "暂时无法回答")
        logger.debug(f"[WebSocket] 模型生成的文本回复: {response_text}")

        # 直接用这个文本生成语音
        audio_url = None
        if settings.USE_CHAT_TTS:
            logger.debug("process_message: Generating TTS...")
            speech_manager = SpeechManager()
            audio_url = await speech_manager.generate_speech(response_text)
            logger.debug(f"[WebSocket] 成功生成语音: {audio_url}, 类型: {type(audio_url)}")

        # 发送 JSON 消息
        response_data = {"type": "response", "text": response_text, "audio_url": audio_url}
        await self.send(text_data=json.dumps(response_data))

    except Exception as e:
        logger.error(f"处理消息时发生错误: {e}")
        logger.error(traceback.format_exc())
        response_data = {"type": "error", "text": "服务暂时不可用，请稍后再试。", "audio_url": None}
        await self.send(text_data=json.dumps(response_data))
