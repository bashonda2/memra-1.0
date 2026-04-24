"""
Memra 1.0 — MCP Server.

Runs via stdio. Cursor/Claude Code spawns this process automatically.
No terminal, no port, no HTTP. Context management happens through
MCP tools and resources that the model can access natively.

Tools:
  - memra_remember: Store a fact, preference, or decision
  - memra_recall: Retrieve relevant context and profile
  - memra_context: Get full session context (structured state + profile)
  - memra_profile: Show what Memra knows about the user

Resources:
  - memra://context: Auto-loaded session context for the model
  - memra://profile: Auto-loaded user profile
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.context.transcript import TranscriptWriter
from src.context.structured_state import StructuredState
from src.context.auditor import Auditor
from src.context.seeds import SeedStore
from src.context.entity_resolution import EntityRegistry
from src.profile.user_profile import UserProfile
from src.agents.lifecycle import AgentManager
from src.chain_of_thought.goal_stack import GoalStack
from src.chain_of_thought.drift_detection import check_drift
from src.orchestrator.triage import classify_query

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("memra.mcp")

try:
    from fastmcp import FastMCP
except ImportError:
    logger.error("fastmcp not installed. Run: pip install fastmcp")
    sys.exit(1)


def _load_config() -> dict:
    config_path = os.environ.get("MEMRA_CONFIG")
    if config_path and os.path.exists(config_path):
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f)
    base = os.path.join(PROJECT_ROOT, "config", "default.yaml")
    if os.path.exists(base):
        import yaml
        with open(base) as f:
            return yaml.safe_load(f)
    return {}


config = _load_config()
ce_config = config.get("context_engine", {})
data_dir = os.environ.get(
    "MEMRA_DATA_DIR",
    ce_config.get("data_dir", os.path.join(os.path.expanduser("~"), ".memra")),
)

transcript = TranscriptWriter(data_dir=f"{data_dir}/transcripts")
state = StructuredState(data_dir=f"{data_dir}/state",
                        max_chars=ce_config.get("max_context_chars", 64000))
seeds = SeedStore(data_dir=f"{data_dir}/seeds")
auditor = Auditor(
    audit_log_dir=f"{data_dir}/audit_log",
    lookback_turns=ce_config.get("auditor", {}).get("lookback_turns", 3),
    enabled=ce_config.get("auditor", {}).get("enabled", True),
)
profile = UserProfile(data_dir=f"{data_dir}/profile")
entities = EntityRegistry(data_dir=f"{data_dir}/entities")
agent_mgr = AgentManager(data_dir=f"{data_dir}/agents")
goal_stack = GoalStack(data_dir=f"{data_dir}/goals")

_current_session: Optional[str] = None


def _get_session() -> str:
    global _current_session
    if not _current_session:
        _current_session = f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        state.create(_current_session)
        logger.info("New MCP session: %s", _current_session)
    return _current_session


mcp = FastMCP(
    "Memra",
    instructions=(
        "Memra is your persistent memory engine. It remembers facts, "
        "preferences, decisions, and context across sessions. "
        "Call memra_recall at the start of conversations to load context. "
        "Call memra_remember when the user shares important information. "
        "The user profile persists across all sessions."
    ),
)


@mcp.tool()
def memra_remember(
    content: str,
    category: str = "general",
) -> str:
    """Store a fact, preference, decision, or important context.

    Call this when the user shares something worth remembering:
    personal facts, preferences, project decisions, technical choices,
    or anything that should persist across sessions.

    Args:
        content: The fact or information to remember.
        category: Type of information (fact, preference, decision, context).
    """
    session_id = _get_session()
    turn = transcript.turn_count(session_id) + 1

    transcript.append(session_id, "system", f"[REMEMBERED] {content}", turn=turn)
    profile.add_fact(content, source_session=session_id)

    if category == "preference":
        profile.add_preference(content)

    extracted_entities = entities.auto_extract_entities(content)
    entity_names = [e["canonical"] for e in extracted_entities]

    return json.dumps({
        "status": "remembered",
        "content": content,
        "category": category,
        "session": session_id,
        "profile_facts": len(profile._profile.get("facts", [])),
        "entities_detected": entity_names,
    })


@mcp.tool()
def memra_recall(
    query: str = "",
) -> str:
    """Retrieve relevant context and what Memra knows.

    Call this at the start of a conversation or when you need context.
    Returns the user profile, current session state, and any relevant
    memories.

    Args:
        query: Optional search query to find specific memories.
    """
    session_id = _get_session()

    result = {}

    profile_ctx = profile.get_context()
    if profile_ctx:
        result["profile"] = profile_ctx

    entity_ctx = entities.get_context()
    if entity_ctx:
        result["entities"] = entity_ctx

    goal_ctx = goal_stack.get_context()
    if goal_ctx:
        result["goals"] = goal_ctx

    session_ctx = state.load(session_id)
    if session_ctx:
        result["session_state"] = session_ctx

    seed_ctx = seeds.render_seeds_context(session_id)
    if seed_ctx:
        result["deep_memory"] = seed_ctx

    warnings = auditor.get_warnings(session_id)
    if warnings:
        result["audit_warnings"] = warnings

    if query:
        triage = classify_query(query)
        result["triage"] = {
            "route": triage.route,
            "score": triage.complexity_score,
            "reasoning": triage.reasoning,
        }

    result["session_id"] = session_id
    result["turn_count"] = transcript.turn_count(session_id)
    result["total_facts"] = len(profile._profile.get("facts", []))
    result["total_entities"] = len(entities.get_all())

    if not profile_ctx and not session_ctx:
        result["note"] = "No context yet. Memra learns as you share information."

    return json.dumps(result, indent=2)


@mcp.tool()
def memra_context(
    user_message: str = "",
    assistant_message: str = "",
) -> str:
    """Record an exchange and get updated context.

    Call this after each meaningful exchange to keep the context
    engine updated. Returns the current structured state.

    Args:
        user_message: The user's message (for context tracking).
        assistant_message: The assistant's response (for context tracking).
    """
    session_id = _get_session()

    if user_message and assistant_message:
        turn = transcript.turn_count(session_id) + 1
        transcript.append(session_id, "user", user_message, turn=turn)
        transcript.append(session_id, "assistant", assistant_message, turn=turn)
        state.update(session_id, user_message, assistant_message, turn=turn)

        meta = state.get_meta(session_id)
        if meta:
            profile.update_from_state(meta)

        if auditor.enabled and turn % auditor.lookback_turns == 0:
            tier2 = state.load(session_id)
            tier1 = transcript.read_last_n_turns(session_id, auditor.lookback_turns)
            if tier2 and tier1:
                auditor.check(session_id, turn, tier2, tier1)

    ctx = state.load(session_id) or "(no session state yet)"
    profile_ctx = profile.get_context()

    return json.dumps({
        "session_id": session_id,
        "turn_count": transcript.turn_count(session_id),
        "structured_state": ctx,
        "profile": profile_ctx or "(no profile yet)",
    })


@mcp.tool()
def memra_profile() -> str:
    """Show what Memra knows about the user.

    Returns the full user profile: facts, preferences, and
    graduated capabilities. This persists across all sessions.
    """
    p = profile._profile

    facts_summary = []
    for f in sorted(p.get("facts", []), key=lambda x: x.get("evidence_count", 1), reverse=True):
        facts_summary.append({
            "text": f["text"],
            "evidence_count": f.get("evidence_count", 1),
            "added": f.get("added", ""),
        })

    return json.dumps({
        "total_facts": len(facts_summary),
        "facts": facts_summary[:20],
        "preferences": p.get("preferences", []),
        "profile_created": p.get("created", ""),
        "last_updated": p.get("last_updated", ""),
    }, indent=2)


@mcp.tool()
def memra_set_goal(
    goal: str,
    subgoals: str = "",
) -> str:
    """Set the current working goal with optional subgoals.

    Call this when the user states what they want to accomplish.
    The goal stack keeps the conversation focused and enables
    resumption if the session is interrupted.

    Args:
        goal: The main goal (e.g., "Build the authentication system").
        subgoals: Comma-separated steps (e.g., "Design schema, Build API, Write tests").
    """
    session_id = _get_session()
    turn = transcript.turn_count(session_id)
    subgoal_list = [s.strip() for s in subgoals.split(",") if s.strip()] if subgoals else []

    g = goal_stack.set_goal(goal, subgoals=subgoal_list, session_id=session_id, turn=turn)

    return json.dumps({
        "status": "goal_set",
        "goal": g.to_dict(),
        "context_injected": True,
    })


@mcp.tool()
def memra_update_progress(
    goal_id: str,
    subgoal_index: int,
    status: str,
    notes: str = "",
) -> str:
    """Update progress on a subgoal.

    Args:
        goal_id: The goal's ID.
        subgoal_index: Which subgoal (0-based index).
        status: New status: pending, in_progress, completed, blocked.
        notes: Optional notes about the progress.
    """
    g = goal_stack.update_subgoal(goal_id, subgoal_index, status, notes)
    if not g:
        return json.dumps({"error": "Goal or subgoal not found."})

    return json.dumps({
        "status": "updated",
        "goal": g.to_dict(),
    })


@mcp.tool()
def memra_check_focus(
    recent_messages: str = "",
) -> str:
    """Check if the conversation is still on track with active goals.

    Call this periodically (every 5-10 turns) or when the conversation
    seems to have drifted. Returns drift detection results and the
    current goal stack.

    Args:
        recent_messages: Last few user messages, newline-separated. If empty, uses session transcript.
    """
    session_id = _get_session()

    if recent_messages:
        messages = [m.strip() for m in recent_messages.split("\n") if m.strip()]
    else:
        entries = transcript.read_last_n_turns(session_id, 5)
        messages = [e["content"] for e in entries if e.get("role") == "user"]

    active = goal_stack.get_active_goals()
    active_dicts = [g.to_dict() for g in active]

    drift = check_drift(messages, active_dicts)

    result = {
        "drift": drift,
        "active_goals": active_dicts,
        "goal_context": goal_stack.get_context(),
    }

    if drift.get("drifted"):
        result["recommendation"] = "The conversation has drifted from the active goal. Consider refocusing or updating the goal."

    return json.dumps(result, indent=2)


@mcp.tool()
def memra_resume() -> str:
    """Get resumption context — what was I working on?

    Call this at the start of a new session to pick up where you left off.
    Returns active goals, progress, what's done, and what's next.
    """
    session_id = _get_session()

    resumption = goal_stack.get_resumption_context()
    profile_ctx = profile.get_context()
    active_agents = agent_mgr.list_active()

    result = {
        "resumption": resumption or "No active goals. What would you like to work on?",
        "profile": profile_ctx or "No profile yet.",
        "active_agents": len(active_agents),
    }

    if active_agents:
        result["agents"] = [
            {"name": a.name, "goal": a.task.goal[:80], "state": a.state.value}
            for a in active_agents[:5]
        ]

    return json.dumps(result, indent=2)


@mcp.tool()
def memra_spawn_agent(
    name: str,
    goal: str,
    constraints: str = "",
    priority: int = 5,
    max_turns: int = 100,
) -> str:
    """Spawn a persistent agent to work on a task in the background.

    The agent gets its own session in the context engine. It persists
    across server restarts. Use this for long-running tasks like research,
    monitoring, writing, or any work that benefits from persistence.

    Args:
        name: Short name for the agent (e.g., "Research Agent", "Monitor").
        goal: What the agent should accomplish.
        constraints: Comma-separated constraints (e.g., "no external APIs, max 50 turns").
        priority: 1 (highest) to 10 (lowest). Higher priority gets GPU time first.
        max_turns: Maximum turns before auto-completion.
    """
    constraint_list = [c.strip() for c in constraints.split(",") if c.strip()] if constraints else []

    agent = agent_mgr.spawn(
        name=name,
        goal=goal,
        constraints=constraint_list,
        max_turns=max_turns,
        priority=priority,
    )

    state.create(agent.session_id)

    return json.dumps({
        "status": "spawned",
        "agent": agent.to_dict(),
        "note": "Agent created with its own context session. Use memra_list_agents to check status.",
    })


@mcp.tool()
def memra_list_agents(
    filter_state: str = "all",
) -> str:
    """List all agents and their current status.

    Args:
        filter_state: Filter by state: "all", "active", "completed", "failed".
    """
    if filter_state == "active":
        agents = agent_mgr.list_active()
    elif filter_state == "completed":
        agents = [a for a in agent_mgr.list_all() if a.state.value == "completed"]
    elif filter_state == "failed":
        agents = [a for a in agent_mgr.list_all() if a.state.value == "failed"]
    else:
        agents = agent_mgr.list_all()

    summary = agent_mgr.get_summary()

    return json.dumps({
        "agents": [a.to_dict() for a in agents],
        "summary": summary,
    }, indent=2)


@mcp.tool()
def memra_agent_action(
    agent_id: str,
    action: str,
    output: str = "",
) -> str:
    """Control an agent: start, pause, resume, complete, or kill.

    Args:
        agent_id: The agent's ID.
        action: One of: start, pause, resume, complete, kill.
        output: Optional output/result message (for complete action).
    """
    actions = {
        "start": lambda: agent_mgr.start(agent_id),
        "pause": lambda: agent_mgr.pause(agent_id),
        "resume": lambda: agent_mgr.resume(agent_id),
        "complete": lambda: agent_mgr.complete(agent_id, output),
        "kill": lambda: agent_mgr.kill(agent_id),
    }

    if action not in actions:
        return json.dumps({"error": f"Unknown action: {action}. Use: start, pause, resume, complete, kill."})

    agent = actions[action]()
    if not agent:
        return json.dumps({"error": f"Agent not found: {agent_id}"})

    return json.dumps({
        "status": action,
        "agent": agent.to_dict(),
    })


@mcp.resource("memra://profile")
def get_profile_resource() -> str:
    """User profile — what Memra knows about you."""
    ctx = profile.get_context()
    return ctx if ctx else "No profile data yet. Memra learns as you share information."


@mcp.resource("memra://context")
def get_context_resource() -> str:
    """Current session context — structured state from the conversation."""
    session_id = _get_session()
    ctx = state.load(session_id)
    seed_ctx = seeds.render_seeds_context(session_id)
    parts = []
    if ctx:
        parts.append(ctx)
    if seed_ctx:
        parts.append(seed_ctx)
    return "\n\n".join(parts) if parts else "No session context yet."


@mcp.resource("memra://goals")
def get_goals_resource() -> str:
    """Active goals and progress — what we're working on."""
    ctx = goal_stack.get_context()
    return ctx if ctx else "No active goals. Set one with memra_set_goal."


@mcp.resource("memra://agents")
def get_agents_resource() -> str:
    """Active agents and their status."""
    active = agent_mgr.list_active()
    if not active:
        return "No active agents."
    lines = ["Active Agents:"]
    for a in active:
        lines.append(f"- [{a.state.value}] {a.name} ({a.agent_id}): {a.task.goal[:80]}")
        lines.append(f"  Turns: {a.turns_completed}/{a.task.max_turns}, Priority: {a.task.priority}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
