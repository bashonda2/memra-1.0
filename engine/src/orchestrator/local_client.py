"""
Local inference client — connects to Ollama for on-device model inference.

Ollama exposes an OpenAI-compatible API at localhost:11434.
This client translates Memra's requests to that API.
Cost: $0. Latency: ~200ms TTFT. No data leaves the machine.
"""
import json
import logging
import os
from typing import AsyncIterator, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("memra.local")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


class LocalClient:

    def __init__(self, model: str = "qwen3.6", base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    @property
    def is_available(self) -> bool:
        try:
            import httpx as _httpx
            r = _httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            if r.status_code == 200:
                models = r.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
        except Exception:
            pass
        return False

    async def generate(self, messages: List[dict], *,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None) -> Dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        options = {}
        if max_tokens:
            options["num_predict"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature
        if options:
            payload["options"] = options

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            msg = data.get("message", {})
            return {
                "text": msg.get("content", ""),
                "finish_reason": "stop",
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "model": self.model,
                "route": "local",
            }
        except Exception as e:
            logger.error("Local generation failed: %s", e)
            return {
                "text": f"Local model error: {e}",
                "finish_reason": "error",
                "route": "local",
            }

    async def stream(self, messages: List[dict], *,
                     max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> AsyncIterator[Tuple[str, Optional[str]]]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        options = {}
        if max_tokens:
            options["num_predict"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature
        if options:
            payload["options"] = options

        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {})
                        content = msg.get("content", "")
                        if content:
                            done = data.get("done", False)
                            yield (content, "stop" if done else None)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error("Local stream failed: %s", e)
            yield (f"Local model error: {e}", "error")
