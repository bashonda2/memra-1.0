# Memra

**Your AI just got a memory. And a 93% pay cut.**

Drop-in context engine for any AI tool. Persistent memory, intelligent routing, background agents, chain of thought — all local. Works with Cursor, Claude Code, Goose, OpenClaw, or anything MCP/OpenAI-compatible.

---

## Quick Start

```bash
git clone https://github.com/bashonda2/memra-1.0.git
cd memra-1.0
python3.12 -m venv venv && source venv/bin/activate
pip install -e engine/
memra setup       # auto-configures Cursor
# restart Cursor — Memra is there
```

Or start the HTTP API server:

```bash
memra server      # runs on localhost:8000
```

---

## What It Does

AI tools forget everything between sessions. Memra gives them persistent, compounding memory.

### Context Engine (Pillar 1)

- **Tier 1 (Transcripts):** Immutable ground truth. Every exchange saved verbatim.
- **Tier 2 (Structured State):** ~2K tokens instead of 50K+ raw history. Decisions, files, errors, personal context — extracted automatically.
- **Tier 3 (Deep Memory):** Resolved content compressed into seeds. 60% smaller, 100% fidelity.
- **Progressive Takeover:** Turns 1-10 pass-through, 11-20 enrich, 21+ replace.
- **Opus Opener:** Turn 1 uses Opus for best first impression. Sonnet after.
- **Tenth Man Auditor:** Validates managed context against transcripts.
- **User Profile:** Learns preferences and patterns. Gets smarter across sessions.
- **Entity Resolution:** "my wife," "Sarah," "her" collapse into one canonical entity.

### Persistent Agent Swarm (Pillar 2)

- **Spawn agents** for background tasks — research, monitoring, writing.
- **Each agent** gets its own context session. Persists to disk. Survives restarts.
- **GPU-aware queue** serializes local Metal inference, parallelizes frontier calls.
- **Priority scheduling** — urgent agents get GPU time first.
- **Sub-agents** — agents can spawn child agents.

### Chain of Thought (Pillar 3)

- **Goal Stack:** Set goals with subgoals. Progress tracked and injected into every model call.
- **Drift Detection:** Flags when conversation diverges from the active goal.
- **Resumption Protocol:** "Last session you completed A/B. Next: C." Pick up where you left off.

### Cross-Layer Intelligence (The Moat)

- Profile-informed routing: user prefers concise answers → borderline queries stay local.
- Goal alignment: triage knows what you're working on → routes accordingly.
- Agent awareness: relevant background agents surfaced when you ask related questions.
- End-of-session check: catches stalled goals, stuck agents, thin profiles, audit warnings.
- Kaizen: continuous improvement proposals based on session patterns.

---

## MCP Tools (11)

| Tool | Purpose |
|------|---------|
| `memra_remember` | Store facts, preferences, decisions |
| `memra_recall` | Load context, profile, goals, entities |
| `memra_context` | Record exchanges, get updated state |
| `memra_profile` | Show what Memra knows about you |
| `memra_set_goal` | Set working goal with subgoals |
| `memra_update_progress` | Update subgoal status |
| `memra_check_focus` | Drift detection — am I still on track? |
| `memra_resume` | Pick up where you left off |
| `memra_spawn_agent` | Create a persistent background agent |
| `memra_list_agents` | See all agents and their status |
| `memra_agent_action` | Start, pause, resume, complete, or kill an agent |

## MCP Resources (4)

| Resource | What it provides |
|----------|-----------------|
| `memra://profile` | User profile — auto-loaded |
| `memra://context` | Session state — auto-loaded |
| `memra://goals` | Active goals and progress |
| `memra://agents` | Active agents and status |

---

## Connect Your Tool

### Cursor (MCP — recommended)

```bash
memra setup    # auto-configures .cursor/mcp.json
```

### Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
memra server
```

### Any OpenAI SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
```

---

## CLI

```bash
memra serve     # Start MCP server (stdio, for Cursor)
memra server    # Start HTTP API server (localhost:8000)
memra setup     # Auto-configure Cursor MCP
memra status    # Show profile stats and data directory
```

---

## Architecture

```
User → AI Tool → Memra Engine
                     │
    ┌────────────────┼────────────────┐
    │                │                │
Coordinator     Context Engine    Agent Manager
(cross-layer)        │            (spawn/queue)
    │         ┌──────┼──────┐         │
    │      Tier 1  Tier 2  Seeds   GPU Queue
    │      (raw)  (managed) (cold)    │
    │         │                  ┌────┴────┐
  Triage    Auditor           Local    Frontier
  Router   (Tenth Man)        (MLX)    (API)
    │
 Profile ←→ Entities ←→ Goals ←→ Kaizen
    └──── feedback loops ────┘
```

---

## Data

All data stays local in `~/.memra/`:

```
~/.memra/
  transcripts/    # Tier 1 — every exchange, verbatim
  state/          # Tier 2 — structured state per session
  seeds/          # Deep Memory — compressed resolved content
  audit_log/      # Tenth Man findings
  profile/        # User profile
  entities/       # Entity registry
  goals/          # Goal stack
  agents/         # Agent definitions
  kaizen/         # Improvement log
```

Nothing leaves your machine except the API calls you're already making.

---

## The Framework

Memra implements the [Context Infrastructure Framework 3.2](framework/FRAMEWORK.md) — a production-tested methodology for persistent AI agent memory with five-document architecture, Tenth Man self-auditing, Kaizen continuous improvement, and hot/warm/cold memory tiers.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

Copyright 2026 Aaron Blonquist / Memra Technologies Inc.
