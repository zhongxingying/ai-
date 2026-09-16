# config.py
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 读取配置，如果没读到就给默认值或直接报错
ONEAPI_API_BASE = os.getenv("ONEAPI_API_BASE", "http://localhost:3000/v1")
ONEAPI_CHAT_API_KEY = os.getenv("ONEAPI_CHAT_API_KEY")
ONEAPI_CHAT_MODEL = os.getenv("ONEAPI_CHAT_MODEL", "qwen-turbo")

# 关键配置缺失就直接报错，别让服务带病运行
if not ONEAPI_CHAT_API_KEY:
    raise ValueError("环境变量 ONEAPI_CHAT_API_KEY 未设置，请检查 .env 文件")
