# 处理聊天请求，支持流式输出（SSE）。StreamingResponse 是 FastAPI 内置的，相当于你在 NestJS 里手动写 SSE 的封装版本。

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.core.llm import client, DEFAULT_MODEL
import json

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    流式聊天接口
    前端通过 EventSource 或 fetch + ReadableStream 接收数据
    每次收到一段文字就推送一条 SSE 消息
    """
    messages = [m.model_dump() for m in request.messages]
    model = request.model or DEFAULT_MODEL

    async def generate():
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                # SSE 格式：data: {...}\n\n
                yield f"data: {json.dumps({'content': delta}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")