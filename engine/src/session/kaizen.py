"""
Kaizen Engine — continuous improvement for the Memra system itself.

Tenth Man asks "is this still true?" Kaizen asks "is this the best way?"

Runs at end of day (or on demand). Analyzes session patterns and
proposes improvements to how the system works.

From Framework 3.2: "Every approved change gets tracked. Did it actually
help? If not, revert or adjust."
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("memra.kaizen")


class KaizenEngine:

    def __init__(self, data_dir: str = "~/.memra/kaizen"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self._log_path = os.path.join(self.data_dir, "improvements.jsonl")
        self._patterns_path = os.path.join(self.data_dir, "patterns.json")

    def analyze_session(self, session_meta: Dict, profile: Dict,
                        goal_history: List[Dict]) -> List[Dict]:
        """Analyze a session for improvement opportunities.

        Looks for patterns that indicate friction, waste, or missed opportunity.
        """
        proposals = []

        turns = session_meta.get("turns", 0)
        errors = session_meta.get("errors", [])
        decisions = session_meta.get("decisions", [])

        # Pattern: repeated errors suggest missing documentation
        if len(errors) > 3:
            proposals.append({
                "type": "documentation",
                "trigger": f"{len(errors)} errors in one session",
                "proposal": "Create a troubleshooting guide for the recurring error patterns.",
                "impact": "Reduce error re-occurrence in future sessions.",
                "reversible": True,
            })

        # Pattern: long session with no decisions suggests exploration without direction
        if turns > 20 and len(decisions) == 0:
            proposals.append({
                "type": "process",
                "trigger": f"{turns} turns with no decisions captured",
                "proposal": "Set a goal at session start. Use memra_set_goal to track progress.",
                "impact": "Keep sessions focused and decisions documented.",
                "reversible": True,
            })

        # Pattern: thin profile after multiple sessions
        fact_count = len(profile.get("facts", []))
        if fact_count < 5 and turns > 10:
            proposals.append({
                "type": "profile",
                "trigger": f"Only {fact_count} facts after {turns}+ turns",
                "proposal": "Ask about the user's role, tools, and project context to build the profile faster.",
                "impact": "Richer profile → better context → smarter routing.",
                "reversible": True,
            })

        # Pattern: goals set but never completed
        abandoned = [g for g in goal_history if g.get("status") == "abandoned"]
        if len(abandoned) > 2:
            proposals.append({
                "type": "goal_setting",
                "trigger": f"{len(abandoned)} goals abandoned",
                "proposal": "Goals may be too large. Break into smaller, achievable subgoals.",
                "impact": "Higher completion rate, better progress tracking.",
                "reversible": True,
            })

        # Pattern: all queries going to frontier (no local routing)
        # This would need triage stats — flag for when we have them

        return proposals

    def propose(self, proposals: List[Dict]) -> str:
        """Format proposals for user review."""
        if not proposals:
            return "No improvement proposals. Current practices are working well."

        lines = ["[KAIZEN — improvement proposals]", ""]
        for i, p in enumerate(proposals, 1):
            lines.append(f"**{i}. [{p['type'].upper()}]** {p['proposal']}")
            lines.append(f"   Trigger: {p['trigger']}")
            lines.append(f"   Impact: {p['impact']}")
            lines.append(f"   Reversible: {'Yes' if p.get('reversible') else 'No'}")
            lines.append("")

        lines.append("Approve, reject, or modify each proposal.")
        return "\n".join(lines)

    def approve(self, proposal: Dict, notes: str = "") -> Dict:
        """Record an approved improvement."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": proposal.get("type", "unknown"),
            "proposal": proposal.get("proposal", ""),
            "trigger": proposal.get("trigger", ""),
            "status": "approved",
            "notes": notes,
            "review_date": "",
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def reject(self, proposal: Dict, reason: str = "") -> Dict:
        """Record a rejected improvement."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": proposal.get("type", "unknown"),
            "proposal": proposal.get("proposal", ""),
            "status": "rejected",
            "reason": reason,
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def get_history(self) -> List[Dict]:
        """Get all improvement decisions."""
        if not os.path.exists(self._log_path):
            return []
        entries = []
        with open(self._log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def get_summary(self) -> str:
        """Summary of improvement activity."""
        history = self.get_history()
        if not history:
            return "No Kaizen history yet."

        approved = sum(1 for h in history if h.get("status") == "approved")
        rejected = sum(1 for h in history if h.get("status") == "rejected")
        by_type = {}
        for h in history:
            t = h.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        lines = [
            f"Kaizen history: {len(history)} proposals",
            f"  Approved: {approved}",
            f"  Rejected: {rejected}",
            f"  By type: {', '.join(f'{t}({c})' for t, c in by_type.items())}",
        ]
        return "\n".join(lines)
