# — 数据结构定义
# 作用：定义请求和响应的数据格式，就像 NestJS 里的 DTO + class-validator。Pydantic 会自动校验数据类型，如果传错了会直接报错。


from pydantic import BaseModel
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str = "qwen-turbo"
    stream: bool = True

class ChatResponse(BaseModel):
    content: str
    model: str