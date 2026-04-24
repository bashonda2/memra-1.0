"""
Session manager — lifecycle, persistence, context injection.

Handles session resolution (which session is this request part of?),
context loading and injection, progressive takeover, and exchange recording.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import Request

from ..context.transcript import TranscriptWriter
from ..context.structured_state import StructuredState
from ..context.auditor import Auditor
from ..context.seeds import SeedStore

logger = logging.getLogger("memra.session")


class SessionManager:

    def __init__(self, config: dict):
        ce_config = config.get("context_engine", {})
        data_dir = os.environ.get(
            "MEMRA_DATA_DIR",
            ce_config.get("data_dir", os.path.join(os.path.expanduser("~"), ".memra")),
        )

        self.transcript = TranscriptWriter(data_dir=f"{data_dir}/transcripts")
        self.state = StructuredState(data_dir=f"{data_dir}/state",
                                     max_chars=ce_config.get("max_context_chars", 64000))
        self.seeds = SeedStore(data_dir=f"{data_dir}/seeds")

        auditor_config = ce_config.get("auditor", {})
        self.auditor = Auditor(
            audit_log_dir=f"{data_dir}/audit_log",
            lookback_turns=auditor_config.get("lookback_turns", 3),
            enabled=auditor_config.get("enabled", True),
        )

        prog_config = config.get("progressive", {})
        self.phase1_turns = prog_config.get("phase1_turns", 10)
        self.phase2_turns = prog_config.get("phase2_turns", 20)
        self.keep_last_turns = prog_config.get("keep_last_turns", 5)

        self._session_map: Dict[str, str] = {}

    def resolve_session(self, req: Request) -> str:
        header_id = req.headers.get("x-session-id")
        if header_id:
            return header_id

        client_ip = req.client.host if req.client else "unknown"
        user_agent = req.headers.get("user-agent", "")[:50]
        key = f"{client_ip}:{user_agent}"

        if key not in self._session_map:
            session_id = f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            self._session_map[key] = session_id
            self.state.create(session_id)
            logger.info("New session created: %s", session_id)

        return self._session_map[key]

    def inject_context(self, session_id: str, messages: List[dict],
                       user_text: str) -> List[dict]:
        ctx = self.state.load(session_id)
        seed_ctx = self.seeds.render_seeds_context(session_id)
        if seed_ctx:
            ctx = f"{ctx}\n\n{seed_ctx}" if ctx else seed_ctx

        if not ctx:
            return messages

        turn_count = self.transcript.turn_count(session_id)

        if turn_count <= self.phase1_turns:
            messages.insert(0, {
                "role": "system",
                "content": f"[MEMRA — accumulated context]\n{ctx}",
            })
        elif turn_count <= self.phase2_turns:
            messages.insert(0, {
                "role": "system",
                "content": f"[MEMRA — accumulated context]\n{ctx}",
            })
        else:
            system_msgs = [m for m in messages if m["role"] == "system"]
            conversation = [m for m in messages if m["role"] in ("user", "assistant")]
            other = [m for m in messages if m["role"] not in ("system", "user", "assistant")]

            keep_count = self.keep_last_turns * 2
            recent = conversation[-keep_count:] if len(conversation) > keep_count else conversation

            messages = []
            messages.extend(system_msgs)
            messages.append({
                "role": "system",
                "content": f"[MEMRA — accumulated context]\n{ctx}",
            })
            messages.extend(other)
            messages.extend(recent)

            logger.info(
                "Progressive takeover: turn %d, kept %d of %d messages",
                turn_count, len(recent), len(conversation),
            )

        return messages

    def record_exchange(self, session_id: str, user_text: str, assistant_text: str) -> None:
        turn = self.transcript.turn_count(session_id) + 1

        self.transcript.append(session_id, "user", user_text, turn=turn)
        self.transcript.append(session_id, "assistant", assistant_text, turn=turn)

        self.state.update(session_id, user_text, assistant_text, turn=turn)

        if self.auditor.enabled and turn % self.auditor.lookback_turns == 0:
            tier2 = self.state.load(session_id)
            tier1 = self.transcript.read_last_n_turns(session_id, self.auditor.lookback_turns)
            if tier2 and tier1:
                result = self.auditor.check(session_id, turn, tier2, tier1)
                if result.findings:
                    logger.info("Audit findings at turn %d: %s", turn, result.findings)
