"""
Cross-Layer Coordinator — the intelligence layer that ties everything together.

This is the moat. Individual layers (context, triage, agents, goals) are
commodities. The coordinator creates feedback loops between them:

- Context engine sees an agent stuck in a loop → escalates to frontier
- Triage knows from user profile that security topics need deep analysis → routes frontier
- Chain of thought detects drift → pauses, summarizes progress, refocuses
- Agent manager sees 3 agents queued → promotes the one with an approaching deadline
- Profile gets richer → triage gets smarter → costs drop → compounding

Nobody gets this by bolting PLUR + vMLX + OpenClaw together.
"""
import logging
from typing import Dict, List, Optional

from .context.structured_state import StructuredState
from .context.auditor import Auditor
from .context.entity_resolution import EntityRegistry
from .orchestrator.triage import TriageClassifier, TriageResult
from .agents.lifecycle import AgentManager, AgentState
from .chain_of_thought.goal_stack import GoalStack
from .chain_of_thought.drift_detection import check_drift
from .profile.user_profile import UserProfile

logger = logging.getLogger("memra.coordinator")


class Coordinator:
    """Orchestrates feedback loops between all Memra layers."""

    def __init__(self, *, state: StructuredState, auditor: Auditor,
                 entities: EntityRegistry, triage: TriageClassifier,
                 agent_mgr: AgentManager, goal_stack: GoalStack,
                 profile: UserProfile):
        self.state = state
        self.auditor = auditor
        self.entities = entities
        self.triage = triage
        self.agent_mgr = agent_mgr
        self.goal_stack = goal_stack
        self.profile = profile

    def assess_query(self, user_text: str, session_id: str) -> Dict:
        """Full cross-layer assessment of an incoming query.

        Returns routing decision, goal alignment, entity matches,
        profile-informed adjustments, and agent awareness.
        """
        result = {}

        # Layer 1: Triage classification
        triage_result = self.triage.classify(user_text)
        result["triage"] = triage_result.to_dict()

        # Layer 2: Profile-informed routing adjustment
        profile_adjustment = self._profile_routing_adjustment(user_text, triage_result)
        if profile_adjustment:
            result["profile_adjustment"] = profile_adjustment

        # Layer 3: Goal alignment check
        active_goals = self.goal_stack.get_active_goals()
        if active_goals:
            goal_dicts = [g.to_dict() for g in active_goals]
            drift = check_drift([user_text], goal_dicts)
            result["goal_alignment"] = {
                "on_track": not drift.get("drifted", False),
                "overlap_score": drift.get("overlap_score", 0),
                "active_goals": [g.description for g in active_goals],
            }
            if drift.get("drifted"):
                result["goal_alignment"]["warning"] = (
                    "This query may be off-topic. Active goal: " +
                    active_goals[0].description
                )

        # Layer 4: Entity awareness
        entity_matches = self.entities.resolve_in_text(user_text)
        if entity_matches:
            result["entities_mentioned"] = [
                {"mention": name, "canonical": e["canonical"], "category": e.get("category", "")}
                for name, e in entity_matches
            ]

        # Layer 5: Agent awareness
        active_agents = self.agent_mgr.list_active()
        if active_agents:
            relevant = self._find_relevant_agents(user_text, active_agents)
            if relevant:
                result["relevant_agents"] = [
                    {"name": a.name, "goal": a.task.goal[:80], "state": a.state.value}
                    for a in relevant
                ]

        # Layer 6: Recommended action
        result["recommendation"] = self._synthesize_recommendation(result)

        return result

    def _profile_routing_adjustment(self, user_text: str,
                                     triage: TriageResult) -> Optional[Dict]:
        """Check if user profile should override triage routing."""
        facts = self.profile._profile.get("facts", [])
        preferences = self.profile._profile.get("preferences", [])

        for pref in preferences:
            pref_lower = pref.lower()
            if "detailed" in pref_lower or "thorough" in pref_lower:
                if triage.route == "local" and triage.confidence < 0.7:
                    return {
                        "action": "escalate_to_frontier",
                        "reason": "User prefers detailed/thorough responses. Borderline query escalated.",
                    }

            if "concise" in pref_lower or "direct" in pref_lower:
                if triage.route == "frontier" and triage.confidence < 0.7:
                    return {
                        "action": "keep_local",
                        "reason": "User prefers concise responses. Borderline query kept local.",
                    }

        return None

    def _find_relevant_agents(self, user_text: str, agents) -> List:
        """Find agents whose goals are related to the current query."""
        text_lower = user_text.lower()
        relevant = []
        for agent in agents:
            goal_words = set(agent.task.goal.lower().split())
            query_words = set(text_lower.split())
            overlap = goal_words & query_words
            if len(overlap) >= 2:
                relevant.append(agent)
        return relevant

    def _synthesize_recommendation(self, assessment: Dict) -> str:
        """Produce a single recommendation from all layers."""
        parts = []

        route = assessment.get("triage", {}).get("route", "frontier")
        parts.append(f"Route: {route}")

        adj = assessment.get("profile_adjustment")
        if adj:
            parts.append(f"Profile override: {adj['action']}")

        alignment = assessment.get("goal_alignment", {})
        if alignment and not alignment.get("on_track", True):
            parts.append("Warning: possible drift from active goal")

        agents = assessment.get("relevant_agents", [])
        if agents:
            names = ", ".join(a["name"] for a in agents)
            parts.append(f"Related agents: {names}")

        return ". ".join(parts) + "."

    def get_full_context(self, session_id: str) -> str:
        """Build complete context injection from all layers."""
        parts = []

        profile_ctx = self.profile.get_context()
        if profile_ctx:
            parts.append(profile_ctx)

        entity_ctx = self.entities.get_context()
        if entity_ctx:
            parts.append(entity_ctx)

        goal_ctx = self.goal_stack.get_context()
        if goal_ctx:
            parts.append(goal_ctx)

        session_ctx = self.state.load(session_id)
        if session_ctx:
            parts.append(session_ctx)

        active_agents = self.agent_mgr.list_active()
        if active_agents:
            agent_lines = ["[ACTIVE AGENTS]"]
            for a in active_agents[:5]:
                agent_lines.append(f"- {a.name}: {a.task.goal[:60]} [{a.state.value}]")
            parts.append("\n".join(agent_lines))

        return "\n\n".join(parts) if parts else ""

    def end_of_session_check(self, session_id: str) -> Dict:
        """Run at end of session. Catches what individual layers miss."""
        findings = []

        # Check for abandoned goals
        active_goals = self.goal_stack.get_active_goals()
        for g in active_goals:
            pending = [s for s in g.subgoals if s.status == "pending"]
            if len(pending) == len(g.subgoals) and g.subgoals:
                findings.append(f"Goal '{g.description}' has no completed subgoals — stalled?")

        # Check for stuck agents
        for agent in self.agent_mgr.list_active():
            if agent.state == AgentState.RUNNING and agent.turns_completed == 0:
                findings.append(f"Agent '{agent.name}' is running but has 0 turns — stuck?")

        # Check audit warnings
        warnings = self.auditor.get_warnings(session_id)
        if warnings:
            findings.extend(warnings)

        # Profile gap check
        fact_count = len(self.profile._profile.get("facts", []))
        if fact_count < 3:
            findings.append("User profile is thin (<3 facts). Ask about preferences, role, or project context.")

        return {
            "session_id": session_id,
            "findings": findings,
            "finding_count": len(findings),
            "severity": "ok" if not findings else "review",
        }
