"""
Goal Stack — maintains focus across very long multi-turn sessions.

The problem: after 50+ turns, models lose track of the original goal.
The context engine compresses history, but there's no explicit goal tracking.
The model doesn't know "I was trying to accomplish X and I'm on step 3 of 7."

The solution: a goal stack injected into every model call.

Structure:
  - Active goal: what we're trying to accomplish
  - Subgoals: decomposed steps with completion status
  - Progress: what's done, what's next, what's blocked
  - History: completed goals for resumption context
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Subgoal:
    description: str
    status: str = "pending"  # pending, in_progress, completed, blocked
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class Goal:
    goal_id: str
    description: str
    subgoals: List[Subgoal] = field(default_factory=list)
    status: str = "active"  # active, completed, abandoned, paused
    created_at: str = ""
    completed_at: str = ""
    session_id: str = ""
    turn_started: int = 0
    turn_completed: int = 0

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "status": self.status,
            "subgoals": [s.to_dict() for s in self.subgoals],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "progress": self.progress_summary,
        }

    @property
    def progress_summary(self) -> str:
        if not self.subgoals:
            return "No subgoals defined"
        total = len(self.subgoals)
        done = sum(1 for s in self.subgoals if s.status == "completed")
        in_prog = sum(1 for s in self.subgoals if s.status == "in_progress")
        blocked = sum(1 for s in self.subgoals if s.status == "blocked")
        return f"{done}/{total} done, {in_prog} in progress, {blocked} blocked"

    @property
    def next_subgoal(self) -> Optional[Subgoal]:
        for s in self.subgoals:
            if s.status in ("pending", "in_progress"):
                return s
        return None


class GoalStack:

    def __init__(self, data_dir: str = "~/.memra/goals"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self._goals: Dict[str, Goal] = {}
        self._goal_history: List[Goal] = []
        self._load()

    def _path(self) -> str:
        return os.path.join(self.data_dir, "goals.json")

    def _save(self) -> None:
        data = {
            "active_goals": {gid: g.to_dict() for gid, g in self._goals.items()},
            "history": [g.to_dict() for g in self._goal_history[-20:]],
        }
        with open(self._path(), "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        path = self._path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for gid, gdata in data.get("active_goals", {}).items():
                self._goals[gid] = self._parse_goal(gdata)
            for gdata in data.get("history", []):
                self._goal_history.append(self._parse_goal(gdata))
        except Exception:
            pass

    def _parse_goal(self, data: dict) -> Goal:
        subgoals = [
            Subgoal(
                description=s["description"],
                status=s.get("status", "pending"),
                notes=s.get("notes", ""),
            )
            for s in data.get("subgoals", [])
        ]
        return Goal(
            goal_id=data.get("goal_id", ""),
            description=data.get("description", ""),
            subgoals=subgoals,
            status=data.get("status", "active"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at", ""),
        )

    def set_goal(self, description: str, subgoals: Optional[List[str]] = None,
                 session_id: str = "", turn: int = 0) -> Goal:
        goal_id = f"goal-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        goal = Goal(
            goal_id=goal_id,
            description=description,
            subgoals=[Subgoal(description=s) for s in (subgoals or [])],
            created_at=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            turn_started=turn,
        )
        self._goals[goal_id] = goal
        self._save()
        return goal

    def update_subgoal(self, goal_id: str, subgoal_index: int,
                       status: str, notes: str = "") -> Optional[Goal]:
        goal = self._goals.get(goal_id)
        if not goal or subgoal_index >= len(goal.subgoals):
            return None
        goal.subgoals[subgoal_index].status = status
        if notes:
            goal.subgoals[subgoal_index].notes = notes

        if all(s.status == "completed" for s in goal.subgoals) and goal.subgoals:
            goal.status = "completed"
            goal.completed_at = datetime.now(timezone.utc).isoformat()
            self._goal_history.append(goal)
            del self._goals[goal_id]

        self._save()
        return goal

    def complete_goal(self, goal_id: str) -> Optional[Goal]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        goal.status = "completed"
        goal.completed_at = datetime.now(timezone.utc).isoformat()
        self._goal_history.append(goal)
        del self._goals[goal_id]
        self._save()
        return goal

    def abandon_goal(self, goal_id: str) -> Optional[Goal]:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        goal.status = "abandoned"
        self._goal_history.append(goal)
        del self._goals[goal_id]
        self._save()
        return goal

    def get_active_goals(self) -> List[Goal]:
        return list(self._goals.values())

    def get_context(self) -> str:
        """Render goal stack for injection into model context."""
        active = self.get_active_goals()
        if not active:
            recent = self._goal_history[-3:] if self._goal_history else []
            if not recent:
                return ""
            lines = ["[RECENT COMPLETED GOALS]"]
            for g in recent:
                lines.append(f"- {g.description} (completed {g.completed_at[:10]})")
            return "\n".join(lines)

        lines = ["[ACTIVE GOALS — stay focused on these]"]
        for g in active:
            lines.append(f"\n## {g.description}")
            lines.append(f"Progress: {g.progress_summary}")

            if g.subgoals:
                for i, s in enumerate(g.subgoals):
                    marker = "✓" if s.status == "completed" else "→" if s.status == "in_progress" else "○" if s.status == "pending" else "✗"
                    lines.append(f"  {marker} {i+1}. {s.description}")
                    if s.notes:
                        lines.append(f"     Note: {s.notes}")

            nxt = g.next_subgoal
            if nxt:
                lines.append(f"\nNEXT: {nxt.description}")

        return "\n".join(lines)

    def get_resumption_context(self) -> str:
        """Context for resuming after a break — what was I working on?"""
        active = self.get_active_goals()
        if not active:
            return ""

        lines = ["[RESUMPTION — where you left off]"]
        for g in active:
            completed = [s for s in g.subgoals if s.status == "completed"]
            pending = [s for s in g.subgoals if s.status in ("pending", "in_progress")]

            lines.append(f"\nGoal: {g.description}")
            if completed:
                lines.append("Done: " + ", ".join(s.description for s in completed))
            if pending:
                lines.append("Next: " + pending[0].description)
            if len(pending) > 1:
                lines.append(f"Then: {', '.join(s.description for s in pending[1:3])}")

        return "\n".join(lines)
