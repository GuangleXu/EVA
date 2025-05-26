from speech.edge_tts_voice import EdgeTTSVoice
from logs.logs import logger
import os
import uuid
from django.conf import settings
from typing import List, Optional
import time
import traceback

class SpeechManager:
    def __init__(self):
        """初始化 TTS 引擎"""
        self.tts_engine = EdgeTTSVoice()
        self.voices = self._get_available_voices()
        logger.info(f"✅ 初始化语音管理器成功，可用语音数: {len(self.voices)}")

    def _get_available_voices(self) -> List[str]:
        """获取可用的语音列表"""
        try:
            # 目前仅支持中文语音
            return [
                "zh-CN",  # 女声
                "en-US",  # 男声
            ]
        except Exception as e:
            logger.error(f"❌ 获取可用语音失败: {str(e)}")
            return ["zh-CN"]  # 默认使用中文

    async def generate_speech(self, text: str, voice_index: int = 0) -> Optional[str]:
        """
        生成语音文件
        
        Args:
            text: 要转换的文本
            voice_index: 语音索引,默认为0

        Returns:
            生成的音频文件URL,如果失败则返回None
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 确保voice_index在有效范围内
                if not 0 <= voice_index < len(self.voices):
                    voice_index = 0
                    logger.warning(f"⚠️ 无效的voice_index: {voice_index}, 使用默认语音")
                voice = self.voices[voice_index]
                logger.info(f"🎙️ 使用语音: {voice}")
                if not text or len(text.strip()) < 2:
                    raise ValueError("输入文本过短")
                logger.debug(f"SpeechManager: 生成语音，文本长度: {len(text)}字符")
                logger.info(f"[TTS] SpeechManager: 生成语音请求，文本: '{text}', voice_index: {voice_index}, voice: {voice}")
                audio_data = await self.tts_engine.generate_audio(
                    text,
                    rate="+0%",
                    voice=voice
                )
                logger.info(f"[TTS] SpeechManager: 语音合成返回数据大小: {len(audio_data) if isinstance(audio_data, bytes) else '无效'} bytes")
                if not isinstance(audio_data, bytes) or len(audio_data) < 2048:
                    raise ValueError("无效的音频数据或文件过小")
                file_name = f"{uuid.uuid4()}.mp3"  # 统一保存为 .mp3 文件
                file_path = os.path.join(settings.TTS_OUTPUT_DIR, file_name)
                with open(file_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"[TTS] SpeechManager: 音频文件已写入: {file_path}")
                start = time.time()
                while not os.path.exists(file_path):
                    if time.time() - start > 2.0:
                        logger.error(f"SpeechManager: 语音文件写入超时: {file_path}")
                        return None
                    time.sleep(0.1)
                file_size = os.path.getsize(file_path)
                if file_size < 2048:
                    raise ValueError(f"[TTS] SpeechManager: 语音文件过小，路径: {file_path}，大小: {file_size} 字节")
                audio_url = os.path.join(settings.TTS_URL_PREFIX, file_name)
                logger.info(f"[TTS] SpeechManager: 音频文件已保存，URL: {audio_url}，路径: {file_path}，大小: {file_size} 字节，输入文本: {text}，voice_index: {voice_index}，voice: {voice}")
                return str(audio_url)
            except Exception as e:
                logger.error(f"[TTS] SpeechManager: 语音生成失败（第{attempt+1}次）- {str(e)}")
                logger.error(traceback.format_exc())
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    return None

    async def save_to_file(self, audio_data: bytes) -> str:
        """
        存储音频数据到文件并返回文件的 URL。
        """
        try:
            # ✅ 确保 `TTS_OUTPUT_DIR` 目录存在
            os.makedirs(settings.TTS_OUTPUT_DIR, exist_ok=True)

            # ✅ 创建 `.mp3` 文件路径
            file_name = f"{uuid.uuid4()}.mp3"
            file_path = os.path.join(settings.TTS_OUTPUT_DIR, file_name)

            # ✅ 存储音频数据
            with open(file_path, "wb") as f:
                f.write(audio_data)

            # ✅ 生成 **正确的 URL**（统一为 .mp3）
            audio_url = f"{settings.TTS_URL_PREFIX}{file_name}"
            logger.debug(f"SpeechManager: 语音文件已保存，URL: {audio_url}")

            return audio_url

        except Exception as e:
            logger.error(f"SpeechManager: 保存语音文件失败 - {str(e)}")
            return ""  # 返回空字符串，表示保存失败
