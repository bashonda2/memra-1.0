"""
OpenAI-compatible /v1/chat/completions endpoint.

This is the shim layer — translates OpenAI API format to/from the Memra
engine. Any tool that speaks OpenAI API (Cursor, Claude Code, Goose,
OpenClaw, any SDK) connects here without modification.
"""
import json
import logging
import re
import time
import uuid
from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    Message,
    UsageInfo,
)

logger = logging.getLogger("memra")
router = APIRouter()

_METADATA_PATTERNS = [
    re.compile(r"generate\s+a\s+short\s+title", re.IGNORECASE),
    re.compile(r"---END USER MESSAGES---.*generate\s+", re.IGNORECASE | re.DOTALL),
    re.compile(r"summarize\s+(the\s+)?(above|previous)\s+(message|conversation)", re.IGNORECASE),
]


def _is_metadata_request(text: str) -> bool:
    return any(p.search(text) for p in _METADATA_PATTERNS)


def _get_user_text(messages: List[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                return " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            return content or ""
    return ""


def _parse_messages(raw_messages) -> List[dict]:
    messages = []
    for m in raw_messages:
        content = m.content
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        msg = {"role": m.role, "content": content or ""}
        if m.tool_calls:
            msg["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id
        if m.name:
            msg["name"] = m.name
        messages.append(msg)
    return messages


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, req: Request):
    query_id = f"memra-{uuid.uuid4().hex[:12]}"
    engine = req.app.state.engine

    if request.temperature is not None:
        request.temperature = max(0.0, min(request.temperature, 2.0))
    if not request.max_tokens or request.max_tokens < 8192:
        request.max_tokens = 8192

    messages = _parse_messages(request.messages)
    user_text = _get_user_text(messages)

    if not user_text.strip():
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "No user message found.", "type": "invalid_request_error"}},
        )

    is_metadata = _is_metadata_request(user_text)

    session_id = None
    if not is_metadata:
        session_id = engine.resolve_session(req)
        messages = engine.inject_context(session_id, messages, user_text)

    if request.stream:
        return EventSourceResponse(
            _stream_response(engine, messages, query_id, request, session_id, user_text, is_metadata)
        )

    result = await engine.generate(
        messages=messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        session_id=session_id,
        user_text=user_text,
        is_metadata=is_metadata,
    )

    response = ChatCompletionResponse(
        id=query_id,
        created=int(time.time()),
        model="memra",
        choices=[
            ChatCompletionChoice(
                message=Message(
                    role="assistant",
                    content=result["text"],
                    tool_calls=result.get("tool_calls"),
                ),
                finish_reason=result.get("finish_reason", "stop"),
            )
        ],
        usage=UsageInfo(
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            total_tokens=result.get("prompt_tokens", 0) + result.get("completion_tokens", 0),
        ),
    )

    headers = {}
    if session_id:
        headers["X-Session-Id"] = session_id
    return JSONResponse(content=response.model_dump(), headers=headers)


async def _stream_response(engine, messages, query_id, request, session_id, user_text, is_metadata):
    collected_text = []

    async for chunk_text, finish_reason in engine.stream(
        messages=messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    ):
        collected_text.append(chunk_text)
        data = {
            "id": query_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "memra",
            "choices": [{"index": 0, "delta": {"content": chunk_text}, "finish_reason": None}],
        }
        yield {"data": json.dumps(data)}

    final = {
        "id": query_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "memra",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield {"data": json.dumps(final)}
    yield {"data": "[DONE]"}

    if session_id and not is_metadata:
        full_text = "".join(collected_text)
        engine.record_exchange(session_id, user_text, full_text)
