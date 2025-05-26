# EVA_backend/speech/tasks.py

from celery import shared_task
import os
import time
import logging

logger = logging.getLogger(__name__)

@shared_task
def clean_tts_files():
    """
    定期清理过期的 TTS 语音文件（超过 24 小时）。
    """
    tts_folder = "/app/media/tts_output"
    expiration_time = 24 * 3600  # 24 小时（秒）

    if not os.path.exists(tts_folder):
        logger.warning(f"路径 {tts_folder} 不存在，跳过清理")
        return f"路径 {tts_folder} 不存在，跳过清理"

    now = time.time()
    deleted_files = []

    for filename in os.listdir(tts_folder):
        file_path = os.path.join(tts_folder, filename)
        try:
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                logger.debug(f"检查文件: {filename}，年龄: {file_age} 秒")
                if file_age > expiration_time:  # 只删除超过 24 小时的文件
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    logger.info(f"已删除文件: {file_path}")
        except Exception as e:
            logger.error(f"无法删除文件 {file_path}：{e}")

    logger.info(f"TTS 文件清理完成，共删除 {len(deleted_files)} 个文件")
    return f"TTS 文件清理完成，共删除 {len(deleted_files)} 个文件"
