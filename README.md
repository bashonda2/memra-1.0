# Memra 1.0

**Your AI just got a memory. And a 93% pay cut.**

Drop-in replacement for your Anthropic/OpenAI API endpoint. Same models, managed context, persistent memory. Works with Cursor, Claude Code, Goose, OpenClaw, or anything OpenAI-compatible.

---

## Quick Start

```bash
git clone https://github.com/bashonda2/memra-1.0.git
cd memra-1.0
./install.sh
./start.sh
```

Then point your AI tool at `http://localhost:8000`. Done.

---

## What It Does

Every AI tool sends your entire conversation history to the model on every turn. That's expensive, slow, and gets worse the longer you work.

Memra sits between your AI tool and the model. It manages what the model sees:

- **Tier 1 (Transcripts):** Immutable ground truth. Every exchange saved verbatim. Never lost.
- **Tier 2 (Structured State):** ~2K tokens instead of 50K+ raw history. Decisions, files, errors, personal context — extracted automatically.
- **Tier 3 (Deep Memory):** Resolved content compressed into seeds. 60% smaller, 100% fidelity.
- **Progressive Takeover:** Turns 1-10 pass-through. Turns 11-20 enrich. Turns 21+ replace raw history with managed context.
- **Opus Opener:** Turn 1 uses Opus for the best first impression. Sonnet on all subsequent turns.
- **Self-Auditing:** Tenth Man auditor validates managed context against transcripts every few turns.
- **User Profile:** Learns your preferences, tools, and patterns. Gets smarter across sessions.

Your AI tool doesn't know the difference. It sends messages to `localhost:8000` the same way it sends them to `api.anthropic.com`. Memra handles the rest.

---

## Connect Your Tool

### Cursor

Settings → Models → Override OpenAI Base URL → `http://localhost:8000/v1`

### Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
```

### Goose

Edit `~/.config/goose/config.yaml`:
```yaml
provider:
  type: openai
  host: http://localhost:8000
```

### OpenClaw

In your `.env`:
```
OPENAI_BASE_URL=http://localhost:8000/v1
```

### Any OpenAI SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
response = client.chat.completions.create(
    model="memra",
    messages=[{"role": "user", "content": "Hello"}]
)
```

---

## How It Works

```
You → Your AI Tool → Memra (localhost:8000) → Anthropic API
                          │
          ┌───────────────┤
          │               │
    Session Manager   Context Engine
          │               │
    Progressive       ┌───┴───┐
    Takeover     Tier 1  Tier 2  Deep Memory
                (raw)  (managed) (compressed)
                          │
                    Tenth Man Auditor
                  (validates accuracy)
```

Memra intercepts requests, injects managed context, and proxies to the frontier model. The model gets the right context at the right time — not everything, not nothing, but exactly what it needs.

---

## What Gets Saved

All data stays local in `memra_data/`:

```
memra_data/
  transcripts/    # Tier 1 — every exchange, verbatim, JSONL
  state/          # Tier 2 — structured state per session, markdown
  seeds/          # Deep Memory — compressed resolved content
  audit_log/      # Tenth Man findings
  profile/        # User profile (preferences, patterns)
```

Nothing leaves your machine except the API calls to your model provider (which you're already making).

---

## Configuration

Edit `engine/config/default.yaml`:

```yaml
frontier:
  model: "claude-sonnet-4-6"       # Default model
  opener_model: "claude-opus-4-6"  # Turn 1 model (best first impression)
  opener_turns: 1                   # How many turns use the opener

progressive:
  phase1_turns: 10    # Pass-through (no context replacement)
  phase2_turns: 20    # Enrich (add context alongside history)
  keep_last_turns: 5  # In phase 3, keep last N turns + managed context
```

---

## The Framework

Memra 1.0 implements the [Context Infrastructure Framework 3.2](framework/FRAMEWORK.md) — a production-tested methodology for persistent AI agent memory. The framework defines the five-document architecture, the Tenth Man self-auditing rule, the Kaizen continuous improvement engine, and the hot/warm/cold memory model. The engine automates what the framework describes.

---

## Roadmap

- **1.0** — Context engine, persistent memory, Opus opener, progressive takeover (this release)
- **1.1** — Triage routing (local vs. frontier), local MLX inference, entity resolution
- **2.0** — Persistent agent swarm, chain of thought tracking, vector retrieval
- **3.0** — Protocol adapters, iOS app, behavioral model

---

## License

Apache License 2.0. Use it, fork it, ship it. See [LICENSE](LICENSE).

Copyright 2026 Aaron Blonquist.
