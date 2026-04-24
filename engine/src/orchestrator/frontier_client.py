"""
Frontier API client — proxies requests to Anthropic (or OpenAI).

Handles the translation between OpenAI message format and Anthropic's
Messages API, including tool calls, streaming, and extended thinking.
"""
import json
import logging
import os
from typing import AsyncIterator, Dict, List, Optional, Tuple

logger = logging.getLogger("memra.frontier")


class FrontierClient:

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 8192):
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._init_client()

    def _init_client(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — frontier calls will fail")
            return
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            logger.error("anthropic package not installed")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def _convert_messages(self, messages: List[dict]) -> Tuple[Optional[str], List[dict]]:
        """Split system messages out (Anthropic uses a separate 'system' param)."""
        system_parts = []
        api_messages = []

        for m in messages:
            if m["role"] == "system":
                system_parts.append(m.get("content", ""))
            elif m["role"] == "tool":
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": m.get("content", ""),
                    }],
                })
            elif m["role"] == "assistant" and m.get("tool_calls"):
                content_blocks = []
                if m.get("content"):
                    content_blocks.append({"type": "text", "text": m["content"]})
                for tc in m["tool_calls"]:
                    func = tc.get("function", {})
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": json.loads(func.get("arguments", "{}"))
                        if isinstance(func.get("arguments"), str)
                        else func.get("arguments", {}),
                    })
                api_messages.append({"role": "assistant", "content": content_blocks})
            else:
                api_messages.append({"role": m["role"], "content": m.get("content", "")})

        system_text = "\n\n".join(system_parts) if system_parts else None
        return system_text, api_messages

    async def generate(self, messages: List[dict], *,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None,
                       model_override: Optional[str] = None) -> Dict:
        if not self._client:
            return {"text": "Error: Anthropic API key not configured.", "finish_reason": "error"}

        system_text, api_messages = self._convert_messages(messages)
        model = model_override or self.model

        kwargs = {
            "model": model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": api_messages,
        }
        if system_text:
            kwargs["system"] = system_text
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            response = await self._client.messages.create(**kwargs)

            text_content = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {"name": block.name, "arguments": json.dumps(block.input)},
                    })

            return {
                "text": text_content,
                "tool_calls": tool_calls if tool_calls else None,
                "finish_reason": "tool_calls" if tool_calls else (response.stop_reason or "stop"),
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "model": model,
            }
        except Exception as e:
            logger.error("Frontier generation failed: %s", e)
            return {"text": f"Error: {e}", "finish_reason": "error"}

    async def stream(self, messages: List[dict], *,
                     max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> AsyncIterator[Tuple[str, Optional[str]]]:
        if not self._client:
            yield ("Error: Anthropic API key not configured.", "error")
            return

        system_text, api_messages = self._convert_messages(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": api_messages,
        }
        if system_text:
            kwargs["system"] = system_text
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield (text, None)
            yield ("", "stop")
        except Exception as e:
            logger.error("Frontier stream failed: %s", e)
            yield (f"Error: {e}", "error")
