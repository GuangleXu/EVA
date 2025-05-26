"""Second-Me集成配置

控制EVA项目中Second-Me记忆系统的集成选项
"""

import os
from typing import Dict, Any

# 默认配置
DEFAULT_CONFIG = {
    # 是否启用Second-Me的长期记忆替换
    "use_secondme_long_term_memory": True,
    
    # 是否启用Second-Me的工作记忆替换
    "use_secondme_working_memory": True,
    
    # 是否启用Second-Me的规则记忆替换
    "use_secondme_rule_memory": True,
    
    # 数据存储路径（相对于项目根目录）
    "data_path": "data",
    
    # Second-Me模型路径（相对于项目根目录）
    "model_path": "models",
    
    # 是否启用详细日志
    "verbose_logging": True,
    
    # Second-Me模型配置
    "model_config": {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,  # 嵌入向量维度
        "use_gpu": False   # 是否使用GPU（需要合适的硬件和安装）
    }
}

# 动态配置
_config = {}


def load_config() -> Dict[str, Any]:
    """加载Second-Me集成配置
    
    读取环境变量和配置文件，确定最终配置
    
    Returns:
        Dict: 配置字典
    """
    global _config
    
    # 使用默认配置作为基础
    config = DEFAULT_CONFIG.copy()
    
    # 从环境变量读取配置（优先级高于默认值）
    if os.environ.get("EVA_USE_SECONDME_LTM", "").lower() in ("false", "0", "no"):
        config["use_secondme_long_term_memory"] = False
    
    if os.environ.get("EVA_USE_SECONDME_WM", "").lower() in ("false", "0", "no"):
        config["use_secondme_working_memory"] = False
    
    if os.environ.get("EVA_USE_SECONDME_RULE", "").lower() in ("false", "0", "no"):
        config["use_secondme_rule_memory"] = False
    
    # 从配置文件读取（如果有）
    config_file = os.path.join(os.path.dirname(__file__), "secondme_config.json")
    if os.path.exists(config_file):
        import json
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                # 更新配置，保留深层次的配置（如model_config）
                for key, value in file_config.items():
                    if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                        config[key].update(value)
                    else:
                        config[key] = value
        except Exception as e:
            print(f"读取Second-Me配置文件失败: {str(e)}")
    
    # 保存配置
    _config = config
    return config


def get_config() -> Dict[str, Any]:
    """获取当前配置
    
    如果配置尚未加载，则先加载配置
    
    Returns:
        Dict: 配置字典
    """
    global _config
    if not _config:
        return load_config()
    return _config 