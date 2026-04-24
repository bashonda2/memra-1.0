"""
Agent Lifecycle Manager — spawn, pause, resume, kill persistent agents.

Each agent is:
  - A session in the context engine (its own Tier 1/2/3)
  - A task definition (goal, constraints, reporting, termination condition)
  - A lifecycle state (spawned, running, paused, completed, failed)
  - Independently routable through triage (routine → local, synthesis → frontier)

Agents persist to disk. They survive server restarts. They queue for
GPU access via the task queue (Metal can't handle concurrent generations).
"""
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("memra.agents")


class AgentState(Enum):
    SPAWNED = "spawned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class AgentTask:
    goal: str
    constraints: List[str] = field(default_factory=list)
    reporting_cadence: str = "on_completion"
    termination_condition: str = "goal_achieved"
    max_turns: int = 100
    priority: int = 5


@dataclass
class Agent:
    agent_id: str
    name: str
    task: AgentTask
    state: AgentState = AgentState.SPAWNED
    session_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    turns_completed: int = 0
    last_output: str = ""
    parent_agent_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns_completed": self.turns_completed,
            "last_output": self.last_output[:200],
            "parent_agent_id": self.parent_agent_id,
            "error": self.error,
            "task": {
                "goal": self.task.goal,
                "constraints": self.task.constraints,
                "max_turns": self.task.max_turns,
                "priority": self.task.priority,
            },
        }


class AgentManager:

    def __init__(self, data_dir: str = "~/.memra/agents"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self._agents: Dict[str, Agent] = {}
        self._load_all()

    def _agent_path(self, agent_id: str) -> str:
        return os.path.join(self.data_dir, f"{agent_id}.json")

    def _save(self, agent: Agent) -> None:
        agent.updated_at = datetime.now(timezone.utc).isoformat()
        with open(self._agent_path(agent.agent_id), "w") as f:
            json.dump(agent.to_dict(), f, indent=2)

    def _load_all(self) -> None:
        if not os.path.exists(self.data_dir):
            return
        for fname in os.listdir(self.data_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.data_dir, fname)) as f:
                        data = json.load(f)
                    agent = Agent(
                        agent_id=data["agent_id"],
                        name=data["name"],
                        task=AgentTask(
                            goal=data["task"]["goal"],
                            constraints=data["task"].get("constraints", []),
                            max_turns=data["task"].get("max_turns", 100),
                            priority=data["task"].get("priority", 5),
                        ),
                        state=AgentState(data["state"]),
                        session_id=data.get("session_id"),
                        created_at=data.get("created_at", ""),
                        updated_at=data.get("updated_at", ""),
                        turns_completed=data.get("turns_completed", 0),
                        last_output=data.get("last_output", ""),
                        parent_agent_id=data.get("parent_agent_id"),
                        error=data.get("error"),
                    )
                    self._agents[agent.agent_id] = agent
                except Exception as e:
                    logger.error("Failed to load agent %s: %s", fname, e)

    def spawn(self, name: str, goal: str, *,
              constraints: Optional[List[str]] = None,
              max_turns: int = 100,
              priority: int = 5,
              parent_agent_id: Optional[str] = None) -> Agent:
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        session_id = f"agent-sess-{agent_id}"
        now = datetime.now(timezone.utc).isoformat()

        agent = Agent(
            agent_id=agent_id,
            name=name,
            task=AgentTask(
                goal=goal,
                constraints=constraints or [],
                max_turns=max_turns,
                priority=priority,
            ),
            state=AgentState.SPAWNED,
            session_id=session_id,
            created_at=now,
            updated_at=now,
            parent_agent_id=parent_agent_id,
        )

        self._agents[agent_id] = agent
        self._save(agent)
        logger.info("Agent spawned: %s (%s) — %s", name, agent_id, goal[:80])
        return agent

    def start(self, agent_id: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        if agent.state not in (AgentState.SPAWNED, AgentState.PAUSED):
            logger.warning("Cannot start agent %s in state %s", agent_id, agent.state.value)
            return agent
        agent.state = AgentState.RUNNING
        self._save(agent)
        logger.info("Agent started: %s", agent_id)
        return agent

    def pause(self, agent_id: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        if agent.state != AgentState.RUNNING:
            return agent
        agent.state = AgentState.PAUSED
        self._save(agent)
        logger.info("Agent paused: %s", agent_id)
        return agent

    def resume(self, agent_id: str) -> Optional[Agent]:
        return self.start(agent_id)

    def complete(self, agent_id: str, output: str = "") -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.state = AgentState.COMPLETED
        agent.last_output = output
        self._save(agent)
        logger.info("Agent completed: %s", agent_id)
        return agent

    def fail(self, agent_id: str, error: str = "") -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.state = AgentState.FAILED
        agent.error = error
        self._save(agent)
        logger.error("Agent failed: %s — %s", agent_id, error)
        return agent

    def kill(self, agent_id: str) -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.state = AgentState.KILLED
        self._save(agent)
        logger.info("Agent killed: %s", agent_id)
        return agent

    def record_turn(self, agent_id: str, output: str = "") -> Optional[Agent]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        agent.turns_completed += 1
        agent.last_output = output
        if agent.turns_completed >= agent.task.max_turns:
            agent.state = AgentState.COMPLETED
            logger.info("Agent %s hit max turns (%d)", agent_id, agent.task.max_turns)
        self._save(agent)
        return agent

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def list_all(self) -> List[Agent]:
        return sorted(self._agents.values(), key=lambda a: a.created_at, reverse=True)

    def list_active(self) -> List[Agent]:
        return [a for a in self._agents.values()
                if a.state in (AgentState.SPAWNED, AgentState.RUNNING, AgentState.PAUSED)]

    def list_by_priority(self) -> List[Agent]:
        active = self.list_active()
        return sorted(active, key=lambda a: a.task.priority)

    def get_summary(self) -> Dict:
        all_agents = self.list_all()
        by_state = {}
        for a in all_agents:
            by_state[a.state.value] = by_state.get(a.state.value, 0) + 1
        return {
            "total": len(all_agents),
            "active": len(self.list_active()),
            "by_state": by_state,
        }
