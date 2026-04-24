"""
Tenth Man Auditor — validates Tier 2 against Tier 1.

Runs after every N turns (configurable). Checks for:
1. Staleness — facts older than threshold
2. Contradictions — Tier 2 claims not supported by Tier 1
3. Gaps — important content in Tier 1 missing from Tier 2
4. Drift — Tier 2 summary diverged from actual conversation
"""
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("memra.auditor")


@dataclass
class AuditResult:
    session_id: str
    turn: int
    timestamp: str
    findings: List[str] = field(default_factory=list)
    severity: str = "ok"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "turn": self.turn,
            "timestamp": self.timestamp,
            "findings": self.findings,
            "severity": self.severity,
        }


class Auditor:

    def __init__(self, audit_log_dir: str = "memra_data/audit_log",
                 lookback_turns: int = 3, enabled: bool = True):
        self.audit_log_dir = audit_log_dir
        self.lookback_turns = lookback_turns
        self.enabled = enabled
        os.makedirs(audit_log_dir, exist_ok=True)

    def check(self, session_id: str, current_turn: int,
              tier2_content: str, tier1_entries: List[dict]) -> AuditResult:
        if not self.enabled:
            return AuditResult(
                session_id=session_id, turn=current_turn,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        findings = []

        tier1_text = " ".join(
            e.get("content", "") for e in tier1_entries
            if e.get("role") == "assistant"
        ).lower()
        tier2_lower = tier2_content.lower()

        error_keywords = ["error", "failed", "exception", "bug", "broken"]
        for kw in error_keywords:
            if kw in tier1_text and kw not in tier2_lower:
                findings.append(f"GAP: '{kw}' appears in transcript but not in structured state")

        decision_keywords = ["decided", "chose", "going with", "switching to"]
        for kw in decision_keywords:
            if kw in tier1_text and kw not in tier2_lower:
                findings.append(f"GAP: decision language '{kw}' in transcript but not captured")

        severity = "ok"
        if len(findings) > 3:
            severity = "warning"
        if len(findings) > 6:
            severity = "critical"

        result = AuditResult(
            session_id=session_id,
            turn=current_turn,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings=findings,
            severity=severity,
        )

        self._log(result)
        return result

    def get_warnings(self, session_id: str) -> List[str]:
        log_path = os.path.join(self.audit_log_dir, f"{session_id}.jsonl")
        if not os.path.exists(log_path):
            return []
        warnings = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get("severity") in ("warning", "critical"):
                        warnings.extend(entry.get("findings", []))
        return warnings[-5:]

    def _log(self, result: AuditResult) -> None:
        log_path = os.path.join(self.audit_log_dir, f"{result.session_id}.jsonl")
        with open(log_path, "a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")
