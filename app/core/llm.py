# 创建并导出一个全局的 OpenAI 客户端实例，整个项目共用这一个，不用每次都重新初始化。等价于 NestJS 里注入的 Service 单例。

from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # 读取 .env 文件，把里面的变量加载到环境变量里

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen-turbo")