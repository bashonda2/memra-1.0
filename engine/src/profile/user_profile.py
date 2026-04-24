"""
User profile — preferences, personal facts, graduated capabilities.

Builds over time from extracted personal facts in Tier 2 structured state.
The profile is injected into context so the model knows the user.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional


class UserProfile:

    def __init__(self, data_dir: str = "memra_data/profile"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._profile_path = os.path.join(data_dir, "profile.json")
        self._profile = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._profile_path):
            with open(self._profile_path) as f:
                return json.load(f)
        return {
            "created": datetime.now(timezone.utc).isoformat(),
            "facts": [],
            "preferences": [],
            "capabilities": [],
        }

    def _save(self) -> None:
        self._profile["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self._profile_path, "w") as f:
            json.dump(self._profile, f, indent=2)

    def add_fact(self, fact: str, source_session: str = "") -> None:
        for existing in self._profile["facts"]:
            if existing["text"].lower() == fact.lower():
                existing["evidence_count"] = existing.get("evidence_count", 1) + 1
                self._save()
                return
        self._profile["facts"].append({
            "text": fact,
            "source": source_session,
            "added": datetime.now(timezone.utc).isoformat(),
            "evidence_count": 1,
        })
        self._save()

    def add_preference(self, preference: str) -> None:
        if preference not in self._profile["preferences"]:
            self._profile["preferences"].append(preference)
            self._save()

    def get_context(self) -> str:
        if not self._profile["facts"] and not self._profile["preferences"]:
            return ""

        lines = ["[USER PROFILE — what Memra knows about you]"]
        strong_facts = sorted(
            self._profile["facts"],
            key=lambda f: f.get("evidence_count", 1),
            reverse=True,
        )
        for fact in strong_facts[:15]:
            lines.append(f"- {fact['text']}")

        if self._profile["preferences"]:
            lines.append("")
            for pref in self._profile["preferences"][:5]:
                lines.append(f"- Preference: {pref}")

        return "\n".join(lines)

    def update_from_state(self, state_meta: Dict) -> None:
        for fact in state_meta.get("personal_facts", []):
            self.add_fact(fact, source_session=state_meta.get("session_id", ""))
