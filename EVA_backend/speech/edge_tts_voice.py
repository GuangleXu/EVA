# =============================================
# EdgeTTS 语音合成主力实现
# 依赖 edge-tts（微软在线 TTS），发音自然，需联网
# =============================================
import edge_tts
import traceback
from logs.logs import logger
from typing import Dict, Any, Optional

class EdgeTTSVoice:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
        self.rate = "+0%"

    async def generate_audio(self, text: str, **kwargs) -> bytes:
        try:
            rate_str = kwargs.get('rate', self.rate)
            # 修复百分号缺失问题
            if isinstance(rate_str, str) and '%' in rate_str:
                sign = '+' if '+' in rate_str else '-' if '-' in rate_str else '+'
                digits = ''.join(filter(str.isdigit, rate_str))
                rate_value = f"{sign}{digits}%"  # 确保包含百分号
            else:
                rate_value = "+0%"  # 默认值
            
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=rate_value,  # 直接使用带%的值
                # 不传递其他无效参数
            )
            
            # 添加音频数据校验
            audio_data = b''
            async for chunk in communicate.stream():
                if isinstance(chunk, Dict) and chunk.get("type") == "audio":
                    audio_chunk = chunk.get("data")
                    if audio_chunk is None:
                        continue
                    if not isinstance(audio_chunk, bytes):
                        raise TypeError(f"无效的音频数据类型: {type(audio_chunk)}")
                    audio_data += audio_chunk
                    
            if len(audio_data) < 1024:  # 最小音频文件大小检查
                raise ValueError("生成的音频数据过小")
                
            return audio_data
            
        except Exception as e:
            logger.error(f"EdgeTTS生成失败: {str(e)}")
            raise 