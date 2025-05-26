# utils.py
from dotenv import load_dotenv
import os
import json

# 自动加载 Second-Me 专属 .env 文件
dotenv_path = os.path.join(os.path.dirname(__file__), '../../../.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 优先从环境变量读取
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)
OPENAI_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", None)

# 如果环境变量没有，再从配置文件读取
if not OPENAI_API_KEY or not OPENAI_BASE_URL:
    config_path = os.path.join(os.path.dirname(__file__), "../../../../secondme_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                if not OPENAI_API_KEY:
                    OPENAI_API_KEY = file_config.get("openai_api_key", None)
                if not OPENAI_BASE_URL:
                    OPENAI_BASE_URL = file_config.get("openai_api_base_url", None)
        except Exception as e:
            print(f"读取secondme_config.json失败: {str(e)}")

# 兜底默认值
if not OPENAI_API_KEY:
    OPENAI_API_KEY = "Please provide your OpenAI API key."
if not OPENAI_BASE_URL:
    OPENAI_BASE_URL = "https://api.openai.com/v1"

Global_Bio = """
I'm CEO of a successful company. I'm also a good engineer.
"""