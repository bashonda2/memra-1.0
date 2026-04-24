"""
Tier 2 — Structured state manager.

Extracts decisions, files, errors, personal facts, and current task
from each exchange via heuristics. Renders as markdown (~2K tokens)
for injection into the model's context window.

This is the core of the cost reduction: instead of 50K+ tokens of raw
history, the model sees a curated 2K-token document.
"""
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


class StructuredState:

    def __init__(self, data_dir: str = "memra_data/state", max_chars: int = 64000):
        self.data_dir = data_dir
        self.max_chars = max_chars
        os.makedirs(data_dir, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _path(self, session_id: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return os.path.join(self.data_dir, f"{safe}.md")

    def create(self, session_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "session_id": session_id,
            "started": now,
            "last_updated": now,
            "turns": 0,
            "current_task": "",
            "decisions": [],
            "files": set(),
            "errors": [],
            "personal_facts": [],
            "turn_log": [],
        }
        self._cache[session_id] = meta
        self._write(session_id, meta)
        return meta

    def load(self, session_id: str) -> Optional[str]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            content = f.read()
        if not content.strip():
            return None
        if len(content) > self.max_chars:
            content = content[:self.max_chars] + "\n[...truncated]"
        return content

    def update(self, session_id: str, user_msg: str, assistant_msg: str, *,
               turn: Optional[int] = None) -> Dict[str, Any]:
        if session_id not in self._cache:
            existing = self._parse(session_id)
            if existing:
                self._cache[session_id] = existing
            else:
                self.create(session_id)

        meta = self._cache[session_id]
        meta["turns"] += 1
        meta["last_updated"] = datetime.now(timezone.utc).isoformat()
        effective_turn = turn if turn is not None else meta["turns"]

        meta["current_task"] = user_msg[:150].replace("\n", " ")

        combined = f"{user_msg}\n{assistant_msg}"
        for fp in self._extract_files(combined):
            meta["files"].add(fp)
        for err in self._extract_errors(combined):
            if err not in meta["errors"]:
                meta["errors"].append(err)
        for dec in self._extract_decisions(combined):
            if dec not in meta["decisions"]:
                meta["decisions"].append(dec)
        for fact in self._extract_personal_facts(user_msg):
            if fact not in meta["personal_facts"]:
                meta["personal_facts"].append(fact)

        meta["turn_log"].append({
            "turn": effective_turn,
            "time": meta["last_updated"],
            "user": user_msg[:100].replace("\n", " "),
            "assistant": assistant_msg[:100].replace("\n", " "),
        })

        self._write(session_id, meta)
        return meta

    def get_meta(self, session_id: str) -> Optional[Dict[str, Any]]:
        if session_id in self._cache:
            return self._cache[session_id]
        parsed = self._parse(session_id)
        if parsed:
            self._cache[session_id] = parsed
        return parsed

    def _write(self, session_id: str, meta: Dict[str, Any]) -> None:
        lines = [
            f"# Session: {session_id}",
            f"Started: {meta['started']}",
            f"Last updated: {meta.get('last_updated', '')}",
            f"Turns: {meta['turns']}",
            "",
            "## Current Task",
            meta.get("current_task", "(none)"),
            "",
            "## Key Decisions",
        ]
        decisions = meta.get("decisions", [])
        if decisions:
            for d in decisions[-20:]:
                lines.append(f"- {d}")
        else:
            lines.append("(none yet)")

        lines.extend(["", "## Files Mentioned"])
        files = meta.get("files", set())
        if files:
            for f in sorted(files):
                lines.append(f"- {f}")
        else:
            lines.append("(none yet)")

        lines.extend(["", "## Personal Context"])
        personal = meta.get("personal_facts", [])
        if personal:
            for p in personal[-20:]:
                lines.append(f"- {p}")
        else:
            lines.append("(none yet)")

        lines.extend(["", "## Errors Encountered"])
        errors = meta.get("errors", [])
        if errors:
            for e in errors[-10:]:
                lines.append(f"- {e}")
        else:
            lines.append("(none)")

        lines.extend(["", "## Turn Log (last 5)"])
        for entry in meta.get("turn_log", [])[-5:]:
            lines.append(f"### Turn {entry['turn']} ({entry['time']})")
            lines.append(f"User: {entry['user']}")
            lines.append(f"Assistant: {entry['assistant']}")
            lines.append("")

        with open(self._path(session_id), "w") as f:
            f.write("\n".join(lines))

    def _parse(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        meta = {
            "session_id": session_id, "started": "", "last_updated": "",
            "turns": 0, "current_task": "", "decisions": [],
            "files": set(), "errors": [], "personal_facts": [], "turn_log": [],
        }
        try:
            with open(path) as f:
                content = f.read()
            m = re.search(r"^Turns: (\d+)$", content, re.MULTILINE)
            if m:
                meta["turns"] = int(m.group(1))
            m = re.search(r"^Started: (.+)$", content, re.MULTILINE)
            if m:
                meta["started"] = m.group(1).strip()
        except OSError:
            return None
        return meta

    def _extract_files(self, text: str) -> Set[str]:
        patterns = [
            r"(?:^|\s)(/[\w./-]+\.[\w]+)",
            r"(?:^|\s)(src/[\w./-]+)",
            r"`([^`\s]+\.(?:py|js|ts|yaml|yml|json|md|txt|sh|swift|rs))`",
        ]
        found = set()
        for pat in patterns:
            for match in re.finditer(pat, text):
                fp = match.group(1)
                if len(fp) > 5 and not fp.startswith("http"):
                    found.add(fp)
        return found

    def _extract_errors(self, text: str) -> List[str]:
        errors = []
        keywords = ["error:", "failed:", "exception:", "traceback",
                     "importerror", "syntaxerror", "typeerror"]
        for line in text.split("\n"):
            if any(kw in line.lower().strip() for kw in keywords):
                clean = line.strip()[:120]
                if clean and clean not in errors:
                    errors.append(clean)
        return errors[:3]

    def _extract_decisions(self, text: str) -> List[str]:
        decisions = []
        pattern = (
            r"(?:decided|chose|choosing|going with|let's use|switching to|"
            r"using|selected|picking|opting for)\s+(.{10,80})"
        )
        for match in re.finditer(pattern, text, re.IGNORECASE):
            dec = match.group(0).strip()[:100]
            if dec:
                decisions.append(dec)
        return decisions[:2]

    def _extract_personal_facts(self, text: str) -> List[str]:
        facts = []
        patterns = [
            r"(?:my favorite|my fav|i (?:love|like|prefer|enjoy))\s+(.{5,80})",
            r"(?:i am|i'm|i work|i live|i have)\s+(.{5,80})",
            r"(?:my name is|call me|i go by)\s+(.{2,40})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                fact = match.group(0).strip()[:120]
                if len(fact) > 10:
                    facts.append(fact)
        return facts[:3]

    def list_sessions(self) -> List[str]:
        return sorted(f[:-3] for f in os.listdir(self.data_dir) if f.endswith(".md"))
