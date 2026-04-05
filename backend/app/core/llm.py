# 创建并导出一个全局的 OpenAI 客户端实例，整个项目共用这一个，不用每次都重新初始化。等价于 NestJS 里注入的 Service 单例。

from openai import AsyncOpenAI
import os
from app.core.paths import ensure_env_loaded

ensure_env_loaded()

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen-turbo")
