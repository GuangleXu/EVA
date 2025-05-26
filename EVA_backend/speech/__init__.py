# EVA_backend/speech/__init__.py

# 仅导入顶层类，避免循环依赖
from speech.speech_manager import SpeechManager  # ✅ 直接导入 SpeechManager

# 将模块暴露的公共接口定义在 __all__ 中
__all__ = ["SpeechManager"]
