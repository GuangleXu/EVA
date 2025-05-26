"""Base class for all voice classes."""
# base.py
from abc import ABC, abstractmethod


class VoiceBase(ABC):
    """
    抽象基类：定义所有语音引擎的通用接口。
    """

    @abstractmethod
    def set_voice(self, voice_name: str) -> None:
        """
        设置语音类型。
        :param voice_name: 语音名称，如 "晓晓" 或 "云希"。
        """
        pass

    @abstractmethod
    def save_to_file(self, text: str, file_path: str) -> None:
        """
        将文本转换为语音并保存到文件。
        :param text: 要转换的文本。
        :param file_path: 保存语音的文件路径。
        """
        pass
