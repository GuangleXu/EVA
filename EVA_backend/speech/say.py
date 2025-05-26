# speech/say.py
from speech.speech_manager import SpeechManager
from logs.logs import logger

async def say_text(text: str) -> str:
    """
    生成语音并返回 URL（确保返回的是字符串）。
    """
    try:
        speech_manager = SpeechManager()
        audio_url = await speech_manager.generate_speech(text)  # ✅ 确保 `await`
        logger.debug(f"say_text: 语音已生成，URL: {audio_url}, 类型: {type(audio_url)}")  # ✅ 记录类型
        return str(audio_url)  # ✅ 确保返回的是 `str`
    except Exception as e:
        logger.error(f"say_text: 语音生成失败 - {e}")
        return ""
