"""
Memra 1.0 — Context engine server.

A standalone FastAPI service that implements the Context Infrastructure
Framework 3.2 as a running engine. Exposes an OpenAI-compatible API
at /v1/chat/completions. Any tool that speaks OpenAI API connects here.
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List, Optional, Tuple

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.openai_routes import router as openai_router
from .orchestrator.frontier_client import FrontierClient
from .session.manager import SessionManager
from .profile.user_profile import UserProfile

logger = logging.getLogger("memra")


class MemraEngine:
    """Central engine that coordinates context, session, frontier, and profile."""

    def __init__(self, config: dict):
        self.config = config
        self.session_mgr = SessionManager(config)
        self.profile = UserProfile(
            data_dir=os.path.join(
                config.get("context_engine", {}).get("data_dir", "memra_data"),
                "profile",
            )
        )

        frontier_config = config.get("frontier", {})
        self.frontier = FrontierClient(
            model=frontier_config.get("model", "claude-sonnet-4-6"),
            max_tokens=frontier_config.get("max_tokens", 8192),
        )
        self.opener_model = frontier_config.get("opener_model", "claude-opus-4-6")
        self.opener_turns = frontier_config.get("opener_turns", 1)

    def resolve_session(self, req: Request) -> str:
        return self.session_mgr.resolve_session(req)

    def inject_context(self, session_id: str, messages: List[dict],
                       user_text: str) -> List[dict]:
        messages = self.session_mgr.inject_context(session_id, messages, user_text)

        profile_ctx = self.profile.get_context()
        if profile_ctx:
            messages.insert(0, {"role": "system", "content": profile_ctx})

        return messages

    async def generate(self, messages: List[dict], *,
                       max_tokens: Optional[int] = None,
                       temperature: Optional[float] = None,
                       session_id: Optional[str] = None,
                       user_text: str = "",
                       is_metadata: bool = False) -> Dict:
        model_override = None
        if session_id and not is_metadata:
            turn_count = self.session_mgr.transcript.turn_count(session_id)
            if turn_count <= self.opener_turns:
                model_override = self.opener_model
                logger.info("Opus opener: turn %d — using %s", turn_count + 1, self.opener_model)

        result = await self.frontier.generate(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model_override=model_override,
        )

        if session_id and not is_metadata and result.get("text"):
            self.record_exchange(session_id, user_text, result["text"])

        return result

    async def stream(self, messages: List[dict], *,
                     max_tokens: Optional[int] = None,
                     temperature: Optional[float] = None) -> AsyncIterator[Tuple[str, Optional[str]]]:
        async for chunk_text, finish_reason in self.frontier.stream(
            messages, max_tokens=max_tokens, temperature=temperature,
        ):
            yield (chunk_text, finish_reason)

    def record_exchange(self, session_id: str, user_text: str, assistant_text: str) -> None:
        self.session_mgr.record_exchange(session_id, user_text, assistant_text)

        meta = self.session_mgr.state.get_meta(session_id)
        if meta:
            self.profile.update_from_state(meta)


def _load_config() -> dict:
    config_path = os.environ.get("MEMRA_CONFIG", "config/default.yaml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return yaml.safe_load(f)
    base = os.path.join(os.path.dirname(__file__), "..", "config", "default.yaml")
    if os.path.exists(base):
        with open(base) as f:
            return yaml.safe_load(f)
    return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = _load_config()
    app.state.config = config
    app.state.start_time = time.time()

    engine = MemraEngine(config)
    app.state.engine = engine

    log_level = config.get("logging", {}).get("level", "INFO")
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))

    logger.info("Memra 1.0 starting...")
    if engine.frontier.is_available:
        logger.info("Frontier: %s (opener: %s for first %d turns)",
                     engine.frontier.model, engine.opener_model, engine.opener_turns)
    else:
        logger.warning("Frontier: NOT AVAILABLE — set ANTHROPIC_API_KEY")

    data_dir = config.get("context_engine", {}).get("data_dir", "memra_data")
    logger.info("Data directory: %s", os.path.abspath(data_dir))
    logger.info("Memra 1.0 ready on http://%s:%s",
                config.get("api", {}).get("host", "127.0.0.1"),
                config.get("api", {}).get("port", 8000))

    yield

    logger.info("Memra 1.0 shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Memra 1.0",
        description="Context engine with persistent memory for AI agents",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(openai_router)

    @app.get("/v1/models")
    async def list_models():
        return {
            "object": "list",
            "data": [{
                "id": "memra",
                "object": "model",
                "created": int(app.state.start_time),
                "owned_by": "memra",
            }],
        }

    @app.get("/health")
    async def health():
        engine = app.state.engine
        return {
            "status": "ok",
            "version": "1.0.0",
            "frontier_available": engine.frontier.is_available,
            "uptime_seconds": int(time.time() - app.state.start_time),
        }

    return app


app = create_app()
