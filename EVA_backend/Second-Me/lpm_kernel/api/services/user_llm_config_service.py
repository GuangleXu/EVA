from typing import Optional
from lpm_kernel.api.repositories.user_llm_config_repository import UserLLMConfigRepository
from lpm_kernel.api.dto.user_llm_config_dto import (
    UserLLMConfigDTO,
    UpdateUserLLMConfigDTO
)
from datetime import datetime
import os
import json


class UserLLMConfigService:
    """User LLM Configuration Service"""

    def __init__(self):
        self.repository = UserLLMConfigRepository()

    def get_available_llm(self) -> Optional['UserLLMConfigDTO']:
        """获取可用的LLM配置，优先级：数据库>环境变量>配置文件>默认值"""
        config = self.repository.get_default_config()
        if config:
            return config
        # 兜底：从环境变量读取
        api_key = os.environ.get("OPENAI_API_KEY", "")
        endpoint = os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
        model_name = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        if api_key:
            return UserLLMConfigDTO(
                provider_type="openai",
                key=api_key,
                chat_api_key=api_key,
                chat_endpoint=endpoint,
                chat_model_name=model_name
            )
        # 兜底：从配置文件读取
        config_path = os.path.join(os.path.dirname(__file__), "../../../../secondme_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    api_key = file_config.get("openai_api_key", "")
                    endpoint = file_config.get("openai_api_base_url", "https://api.openai.com/v1")
                    model_name = file_config.get("openai_model", "gpt-3.5-turbo")
                    if api_key:
                        return UserLLMConfigDTO(
                            provider_type="openai",
                            key=api_key,
                            chat_api_key=api_key,
                            chat_endpoint=endpoint,
                            chat_model_name=model_name
                        )
            except Exception as e:
                print(f"读取secondme_config.json失败: {str(e)}")
        # 兜底：返回None
        return None
    

    def update_config(
        self, 
        config_id: int, 
        dto: UpdateUserLLMConfigDTO
    ) -> UserLLMConfigDTO:
        """Update configuration or create if not exists
        
        This method ensures that only one configuration record exists in the database.
        If the configuration with the given ID doesn't exist, it will be created.
        
        Args:
            config_id: Configuration ID (should be 1)
            dto: UpdateUserLLMConfigDTO object
            
        Returns:
            Updated or created configuration
        """
        # Check if we need to clean up extra records
        self._ensure_single_record()
        
        # Update or create the configuration
        return self.repository.update(config_id, dto)

    def delete_key(self, config_id: int = 1) -> Optional[UserLLMConfigDTO]:
        """Delete API key from the configuration
        
        This method removes the API key and related fields from the configuration.
        
        Args:
            config_id: Configuration ID (default is 1)
            
        Returns:
            Updated configuration with key removed
        """
        # Check if we need to clean up extra records
        self._ensure_single_record()
        
        # Get the current configuration
        config = self.repository.get_default_config()
        if not config:
            # If no configuration exists, return None
            return None
        
        # delete 
        return self.repository.delete(config_id)
        
    def _ensure_single_record(self):
        """Ensure that only one configuration record exists in the database"""
        # This is a safety measure to ensure we only have one record
        # In normal operation, this should never be needed
        count = self.repository.count()
        if count != 1:
            # If we have more than one record, we need to clean up
            # This is a rare case that should not happen in normal operation
            # Implementation would depend on how we want to handle this case
            # For now, we'll just log a warning
            from lpm_kernel.common.logging import logger
            logger.warning(f"Found {count} LLM configurations in the database. Only one should exist.")
            # Future implementation could delete extra records
