# The Context Infrastructure Framework

**Persistent Memory for AI Agents That Compounds Across Sessions**

**Version:** 3.2 | **Author:** Aaron Blonquist | **License:** Apache 2.0 — use, adapt, and share freely.

---

**TL;DR:** AI tools forget everything between sessions. This framework gives them persistent, compounding memory using five structured documents, an 8-point self-auditing rule (the Tenth Man), a continuous improvement engine (Kaizen), and a maintenance discipline. It is open source, production-tested across hundreds of sessions, and works with any AI tool. The central claim: memory built this way compounds across sessions — each session improves the structure, and the agent operating from a mature context infrastructure outperforms the same agent operating from a fresh context window.

---

## What This Is

AI tools forget everything between sessions. Every new conversation starts from zero — no memory of prior decisions, established conventions, or past mistakes. On small projects this is manageable. On anything beyond a prototype, it becomes the dominant failure mode.

This framework solves that problem with **Source of Truth (SOT) documents** — structured, machine-readable files that AI agents read at the start of every session to simulate persistent memory. The novel claim is not just that persistent memory is possible. It is that **memory built this way compounds across sessions**: each session improves the structure, refines the rules, and accumulates evidence, until the agent operating from a mature SOT outperforms the same agent operating from a fresh context window.

The framework covers five documents, three memory tiers, an 8-check self-auditing rule, a continuous improvement engine, and a maintenance discipline. Every concept in it traces back to a specific failure encountered in production. None of it is theoretical.

It is open source under Apache 2.0. Use it, adapt it, fork it, ship it inside your own tooling. The implementations are yours; the principles are universal.

---

## Why It Compounds

Most "use AI better" approaches treat each session as independent. You write a good prompt, you get a good answer, you start over tomorrow. The improvement is linear at best — you get better at prompting, but the AI gets no better at knowing you or your project.

Context infrastructure works differently. Each session writes back to the SOT. The next session starts from a slightly more refined version. The session after that starts from a slightly more refined version still. Over weeks, the SOT accumulates the project's specific conventions, the people involved, the rules that matter, the recipes that work, the failures that taught lessons. The AI agent operating from a mature SOT is not just better-instructed — it is operating inside an externalized model of the project that gets sharper every time it is touched.

The independent research base supports this directly. The Vasilopoulos 2026 paper formalizes a three-tier context architecture developed across 283 sessions on a 108,000-line distributed system, with quantitative evidence that structured context reduces errors and improves consistency over time. Production research on long-running AI-assisted work has shown that the majority of AI tokens are wasted re-reading context, and that managed context can match frontier model quality at substantially lower cost. Both bodies of work converge on the same finding: when context is structured, persistent, and maintained, AI quality improves with use rather than degrading with it.

The author's own production experience, refining and extending these patterns across hundreds of AI-assisted sessions over multiple weeks of real work, confirms the same dynamic. A mature SOT system makes a capable open model competitive with frontier closed models for the specific tasks it has been shaped around. The compounding is real, measurable, and survives skeptical review.

---

## Core Principle: Documentation as Infrastructure

> *"Codified context infrastructure treats documentation as infrastructure — load-bearing artifacts that AI agents depend on to produce correct output."* — Vasilopoulos, 2026

SOTs are not optional documentation. They are **load-bearing infrastructure** — if they break, the AI produces wrong output. Treat them with the same rigor as code: versioned, reviewed, updated every session.

This is the single most important shift in mindset the framework requires. Documentation in most organizations is an afterthought, written once and abandoned. Documentation in this framework is the substrate the AI agent runs on. A stale SOT is not a minor inconvenience — it is a corrupted runtime, and the agent will produce confidently wrong output until the corruption is fixed. The maintenance discipline exists because the cost of skipping it is catastrophic, not cosmetic.

---

## The 5-Document Architecture

Each document answers ONE question. Never mix concerns.

| Document | Question | Changes How Often | Memory Type |
|---|---|---|---|
| **Source of Truth** | What is happening now and why does it matter? | Every session (status), monthly (strategy) | Hot memory |
| **People & Relationships** | Who matters and what is their context? | When people, roles, or relationships change | Warm memory |
| **Quality Contract** | What must be true for output to be correct? | When thresholds, SLAs, or validation rules change | Warm memory |
| **Operational Playbook** | How do we actually do the work? | When procedures, recipes, or tools change | Cold memory |
| **Projects & Ventures** | What is being built and what is the deep context? | When project status, architecture, or scope changes | Cold memory |

For projects with active improvement cycles, an optional **sixth document** — the Kaizen log — tracks process improvements over time. See the Kaizen section below for when it is warranted.

### Why Five Documents

The original v1.0 of this framework proposed four documents (Source of Truth, Data Reference, Quality Contract, Operational Playbook). In practice, two additional needs emerged:

**People are not data.** Relationships, organizational context, transitions, and stakeholder dynamics change at a different cadence than data schemas. Mixing people into a "Data Reference" created update friction — editing the document for a personnel change risked touching data definitions. People deserve their own document.

**Projects need deep context.** Active projects, ventures, IP portfolios, and architectural decisions accumulate detail that overwhelms a Source of Truth focused on "what is happening now." Splitting projects out keeps the main SOT scannable while preserving the deep context AI needs for project-specific work.

The 5-document split follows the **separation of concerns** principle: a status update should not require editing the quality rules. A new team member should not touch the project architecture. A recipe change should not affect the people map. When concerns are separated, updates are surgical and contradictions are impossible.

### The Hot/Warm/Cold Memory Model

Not all context is equally urgent. Borrowing from production research on tiered context architectures:

- **Hot memory** (Source of Truth): Read every session. Changes every session. Contains "what do I need to know right now" — current state, active priorities, session log. Keep this to 5-8 bullet points in the Current State section.
- **Warm memory** (People, Quality Contract): Read every session but changes less frequently. Contains stable-but-important context — who the people are, what the rules are. Read it, but do not expect to update it every session.
- **Cold memory** (Playbook, Projects): Read every session for orientation, but the detailed content is reference material. Contains how-to procedures, project architecture, historical decisions. Updated when the work changes, not when the status changes.

This model prevents the most common SOT failure: the document that is so long nobody reads it. Hot memory stays short. Cold memory stays deep. The AI reads both, but knows which to prioritize.

### When to Split

You do not need all five documents on day one.

1. **Start with ONE** — a simple Source of Truth covering what you are building and why.
2. **Split the Quality Contract** when you have automated checks, SLAs, or validation rules that need a formal home.
3. **Split the Playbook** when your process has more than three steps or you have had your first incident.
4. **Split People** when you are working with more than three or four stakeholders or managing transitions.
5. **Split Projects** when you have more than one active project or the project detail exceeds roughly 200 lines.
6. **Add Kaizen** when you have more than a few sessions of accumulated improvement proposals to track.

The split happens naturally as the work grows. Forcing all six documents into existence on day one creates empty scaffolding that nobody updates. Letting them emerge from real need creates documents that justify their own maintenance cost.

---

## The Tenth Man Rule

Named after the Israeli intelligence doctrine (popularized in *World War Z*): if nine people look at the same information and agree, it is the tenth man's duty to disagree and investigate the opposite conclusion — no matter how implausible. Applied here: when everything in your SOT looks correct, the Tenth Man's job is to find what is not.

> *"At every stage, the AI partner must audit the work and attempt to break it. Every claim is stress-tested. Every weakness is documented. Negative results are reported."*

Most documentation guides focus on what to write. This section is about what to **challenge**.

Your AI partner should be instructed to run the full 8-check Tenth Man audit at the start (and end) of every session:

1. **Staleness** — Is anything more than two weeks old and likely outdated? Flag it before proceeding.
2. **Contradictions** — Is the same fact stated differently in two documents? Stop and reconcile immediately before doing any work.
3. **Gaps** — If something was discussed recently but is not captured in the SOT, the AI should add it — not just answer from memory.
4. **Changed truth** — Have any opinions, relationships, or assumptions evolved since they were last captured? Does Active Memory still reflect reality?
5. **Cascade risk** — If a base assumption changed, scan ALL documents (Active and Deep Memory) for downstream references that may now be wrong. A single changed fact can invalidate references in multiple documents.
6. **Seed candidates** — Is there resolved or completed content in Active Memory that should be compressed to Deep Memory? Propose seeding — never auto-seed. Active Memory must stay large enough for the audit to catch things it was not looking for.
7. **Challenge assumptions** — If a priority, status, or claim seems stale or unvalidated, say so. Do not accept a status at face value just because it is written down.
8. **Document honest findings** — Negative results, failed experiments, and open weaknesses belong in the SOT, not just wins. If something failed, document the failure and what it taught.

**Why eight matters.** Checks 1-3 catch factual errors. Check 4 catches the subtler case where a fact is technically correct but the world moved around it. Check 5 catches downstream damage from upstream changes — the most expensive class of SOT failure because it is silent. Check 6 prevents bloat while preserving the audit's peripheral vision. Checks 7-8 enforce intellectual honesty. The full set creates a self-correcting system, not just a self-checking one.

**The peripheral vision rule.** Active Memory must be large enough for the Tenth Man to catch things it was not looking for. The Tenth Man's best finds come from reading context and noticing something unexpected. Do not optimize for minimum Active Memory size — optimize for Tenth Man effectiveness. If you compress too aggressively, the audit loses the peripheral context that makes it valuable. The principle that governs the tension between "keep Active Memory lean" and "keep Active Memory rich enough to be useful" is this: leanness serves the audit, not the other way around.

The Tenth Man Rule prevents the most insidious SOT failure: the document that looks complete but is quietly wrong. An AI that trusts documentation absolutely will produce confidently wrong output from stale specs. An AI that audits documentation will catch the drift before it compounds.

**Implementation:** Add the full 8-check Tenth Man Audit Checklist to your Quality Contract. Run all 8 checks at the start and end of every session. The checks take less than two minutes. The cost of skipping them — confidently wrong output from stale, contradictory, or incomplete context — is orders of magnitude higher.

---

## Continuous Improvement (Kaizen)

The Tenth Man audits accuracy: *is the SOT still true?* A complementary discipline audits the process itself: *is the way we are working still the best way?*

This is the Kaizen principle (改善) — continuous, incremental improvement applied to the SOT system and all associated work. It runs once at the end of every working day (not every session) and asks one question: *"Based on what happened today, what should we do differently tomorrow?"*

The distinction matters. The Tenth Man catches errors in what is documented. Kaizen catches inefficiencies in how the work is done. Both require the user's approval before any changes are made.

### Tenth Man vs. Kaizen

| | Tenth Man | Kaizen |
|---|---|---|
| **Question** | "Is this still true?" | "Is this the best way?" |
| **Orientation** | Backward — audits what exists | Forward — improves what exists |
| **Cadence** | Every session start and end | End of business day only |
| **Output** | Flags problems for immediate review | Proposes improvements with drafted changes |
| **Scope** | SOT accuracy and integrity | SOT practices, processes, tools, and workflows |
| **Authority** | Flags for review | Drafts changes for review — unique authority to propose practice adjustments |

Both require user approval before any changes are made. Together, they create a system that is both **self-correcting** (Tenth Man) and **self-improving** (Kaizen).

### The Kaizen Process

1. **Observe** — Review what happened today. What sessions occurred? What worked well? What failed or caused friction? What took longer than it should have? What was repeated unnecessarily? What did the Tenth Man flag, and were those flags preventable?
2. **Analyze** — For each observation: is this a one-time issue or a recurring pattern? Is there a root cause that can be addressed? Is there a tool, technique, or structural change that would help?
3. **Propose** — Draft specific, actionable improvements. Each proposal must include: what the change is, what triggered it (evidence, not intuition), which documents or processes are affected, what improves if the change is made, what could go wrong, and whether the change is reversible.
4. **Execute with approval** — Present proposals to the user. Never auto-execute. Once approved, make the change, log it, and set a review date (typically one week) to measure impact.
5. **Measure** — At the review date: did the change achieve the intended impact? Any unintended consequences? Keep, adjust, or revert.

### Kaizen Principles

- **Small changes, every day.** Not redesigns — refinements. A better seed format. A cleaner cross-reference. A tighter recipe. Compounding 1% improvements.
- **Grounded in evidence.** Every proposal cites what triggered it — a specific failure, a pattern observed, a test result. No gut-feel proposals.
- **Measure the improvement.** Every approved change gets tracked. Did it actually help? If not, revert or adjust.
- **Respect what works.** Do not change things that are working. Kaizen targets friction, failure, and missed opportunity — not things that are fine.

### Patterns Kaizen Watches For

| Pattern | Signal |
|---|---|
| Repeated explanation | Same context explained in two or more sessions — write it down |
| Manual step that could automate | Human doing something the AI could do |
| Gap that broke a fresh session | New session could not operate from the SOT alone |
| Friction in the ritual | Session start or end takes too long or misses things |
| Cross-project learning | Improvement in one project applies to another |
| Diminishing returns | A practice that used to help but now adds overhead |

### Maintenance Log

Keep an improvement log with columns for date, proposal, evidence, approved/rejected, result, and review date. This log becomes the institutional memory of how the system itself evolved — invaluable for understanding why a practice exists and whether it is still earning its keep.

### Where Kaizen Lives

In a dedicated document (the optional sixth document, if the project warrants it) or as a section in the Quality Contract for smaller projects. The key is that Kaizen proposals and their outcomes are tracked, not just discussed and forgotten. A project running 20+ improvement proposals across multiple weeks deserves its own Kaizen log; a smaller project can keep them in the Quality Contract.

---

## Cross-Reference Discipline

The number one maintenance problem is the same information appearing in multiple documents. When it drifts, you have contradictions the AI cannot resolve.

**The Rule:** Every piece of information has ONE canonical home. Every other document that needs it uses a cross-reference.

| Information Type | Canonical Home | Other Docs Say |
|---|---|---|
| Performance targets, SLAs, thresholds | Quality Contract | "→ See quality_contract.md §[Section]" |
| People, roles, contact info | People Reference | "→ See people_reference.md §[Section]" |
| Recipe steps, data sources, procedures | Playbook | "→ See playbook.md §[Section]" |
| Project details, architecture, decisions | Projects Reference | "→ See projects_reference.md §[Section]" |
| Current state, priorities, session log | Source of Truth | "→ See source_of_truth.md §[Section]" |
| Process improvements, change log | Kaizen Log (or Quality Contract) | "→ See kaizen_log.md §[Section]" |

When you catch duplication, fix it immediately — replace the duplicate with a cross-reference. Do not wait. Duplication compounds faster than you expect.

---

## The Moment This Framework Was Built For

This framework was originally a private working document. It is being published in 2026 because the AI landscape has shifted in ways that make context infrastructure suddenly central to several converging conversations.

**Andrej Karpathy's "LLM Wiki" framing.** In April 2026, Karpathy publicly described what he called "the tractable form of brain upload" — the idea that a sufficiently rich corpus of personal data plus a capable LLM is, in practice, a near-term implementation of the brain-upload concept that was previously science fiction. He sketched the pattern abstractly. This framework is one rigorous, production-tested instance of that pattern, with the operational discipline to make it actually work over time.

**The Genesis Mission.** In November 2025, the U.S. Department of Energy launched the Genesis Mission, a Manhattan-Project-scale federal AI initiative whose central insight, in Under Secretary for Science Darío Gil's own words, is that "the data is the heart of the equation." The Genesis Mission's architecture explicitly requires structured, validated context layers as the bottleneck unlock for AI usefulness in scientific discovery. The federal government just confirmed at scale what this framework has been demonstrating at smaller scale: the rate-limiting step for AI usefulness is not model capability, it is context organization.

**The post-Glasswing threat landscape.** Anthropic's Project Glasswing announcement in April 2026, which revealed that frontier models can now find and exploit software vulnerabilities autonomously, signals that the architecture for safe AI use is shifting away from cloud-perimeter trust models toward sovereign, local, structured-context approaches. Context infrastructure that runs on user-owned systems and surfaces only what each task requires is the architectural response to the threat model Glasswing describes.

**The arrival of capable open models.** Google DeepMind's Gemma 4 release in early 2026 made native deep-thinking reasoning available in models small enough to run on consumer hardware. Combined with structured context infrastructure, a Gemma 4 31B Thinking model operating from a mature SOT can match frontier closed models on the specific tasks the SOT has been shaped around. The hardware exists. The models exist. The missing piece, until now, has been the structured context layer that lets capable local models punch above their parameter count.

These four shifts converge on the same conclusion: **context infrastructure is the rate-limiting step for the next generation of AI usefulness**, and the people who get good at building and maintaining it will have a structural advantage over the people who keep treating prompts as the unit of work. This framework is one production-tested approach to that work, offered openly in the hope that it accelerates serious effort in the same direction.

---

## Practitioner Guidelines

These combine the six guidelines from the Codified Context research (G1-G6) with practical lessons from production use.

### G1: Start the Constitution Early

> *"A basic constitution does heavy lifting. Stating project objectives, tech stack, and core conventions is sufficient to dramatically improve agent output from day one."* — Vasilopoulos, 2026

Even a 50-line document with project name, tech stack, and five conventions prevents an entire class of AI mistakes from session one. Do not wait until the project is complex.

### G2: If You Explained It Twice, Write It Down

> *"Repeated explanation of domain knowledge across sessions is a signal to codify it as a specification."* — Vasilopoulos, 2026

The practical heuristic: if debugging a particular area consumed an extended session without resolution, it is faster to create a specification and restart than to continue the unguided session. The most valuable documents in any SOT system are usually created after costly incidents, not during planning.

### G3: Write for the Machine, Not for Humans

SOTs are reference documents for AI, not narratives for people. Write with:

- Explicit file paths and function names
- Tables over paragraphs
- "Do this / do not do this" instructions
- Specific dates on every fact
- Version numbers on every document

**Good:** *"Pipeline runs daily at 6 AM. Changed from midnight on March 23 due to upstream timing."*

**Bad:** *"We used to run the pipeline at midnight, but after a few weeks of issues we decided to move it to the morning, which seems to work better."*

### G4: Stale Specs Are Worse Than No Specs

> *"Agents trust documentation absolutely. Out-of-date specs cause silent failures."* — Vasilopoulos, 2026

This is the most expensive lesson the framework teaches. Outdated documentation causes the AI to generate code that conflicts with recent changes. The output appears correct — errors only surface during testing. **Update specs in the same session as changes.** The Tenth Man Rule is your safety net for when you forget.

### G5: Consolidate, Do Not Duplicate

See the Cross-Reference Discipline section above. This is important enough to warrant its own section.

### G6: Monitor Agent Confusion as a Signal

When the AI produces inconsistent output, asks the same clarifying question twice, or seems uncertain about a domain — the relevant specification is likely missing or stale. This is the cheapest diagnostic signal available.

---

## Document Structure Rules

### Every Document Must Have

- **Header block** — Owner, created date, last updated date, version number.
- **System reference table** — Every document lists ALL documents with one-line descriptions and locations.
- **Version footer** — Version and date at the bottom for quick verification during session-start scanning.

### Session Protocol

**Start of every session:**

1. Read all SOT documents (Source of Truth first, then others).
2. Run the Tenth Man audit — all 8 checks.
3. Acknowledge review and surface any stale facts, contradictions, upcoming deadlines, or open items.

**End of every session:**

1. Update affected SOT documents with new information.
2. Add a session log entry (date and summary) to the main Source of Truth.
3. Update "Last updated" timestamps and version footers on changed documents.
4. Check cross-references — new information lives in ONE canonical document, with cross-references elsewhere.
5. Run the Tenth Man audit (end-of-session pass) — catch anything that changed during this session.
6. Check for seed triggers — anything resolved this session that should move to Deep Memory?
7. Confirm with the user that the SOT has been updated.

**End of every working day** (in addition to the end-of-session protocol for the final session of the day):

- Run the Kaizen review. *"Based on what happened today, what should we do differently tomorrow?"* See the Kaizen section for the full process.

If a session starts without reading these, context drift begins immediately.

### Maintenance Cadence

| What | When | Time |
|---|---|---|
| **Tenth Man audit** | Start and end of every session | 2 minutes — run all 8 checks |
| **Seed check** | End of every session | 30 seconds — "anything resolved that should move to Deep Memory?" |
| **Kaizen review** | End of every business day | 15-20 minutes — "what should we do differently tomorrow?" → See Kaizen section |
| **SOT quality review** | Weekly (Friday EOD or Monday AM) | 30 minutes — bloat, formatting, cross-reference integrity, line count trends |
| **Deep seeding pass** | Weekly (same session as quality review) | Scan all Active Memory for content that quietly became seedable |

The seed check prevents accumulation. The weekly review catches what the daily checks miss — formatting drift, orphaned cross-references, sections that grew without justification. Track line counts week over week. If Active Memory is growing faster than Deep Memory, you are not seeding enough.

### Current State Section (Source of Truth Only)

This is the "what do I need to know right now" section. Keep it to 5-8 bullet points, one sentence each. This is your hot memory.

**Good:**

- Status: v2.0 deployed to production. All checks passing.
- Architecture: core service plus three integrations.
- Blocked: upstream credential refresh needed before next pipeline run.
- Next steps: (1) Deploy update. (2) Wire new data source. (3) Add monitoring.

**Bad:**

- Status: v2.0 was deployed last week after a long review process involving two rounds of feedback from the platform team. A reviewer found 17 issues which we addressed over three days... [400 words]

The detailed narrative belongs in the session log or the Projects Reference, not Current State.

### Session Log Rules — One Entry Per Session

Each working session gets one log entry, dated, with all changes summarized in 1-2 sentences.

**Good:** *"2026-03-24 | Deployed v2.0. Restructured SOTs to 5-document system."*

**Bad:** *"2026-03-24 | [500 words about every commit, review comment, and finding]"*

---

## Deep Memory and Seeds

As Active Memory grows, compress resolved content into **Seeds** — short pointers that live in Active Memory and reference full detail in **Deep Memory** (cold storage). Deep Memory is never read at session start. It is accessed only when a seed points to it or when the user asks about something historical.

Two hard rules for seeding:

**🔴 Links are non-compressible.** ALL document links (cloud document IDs and full URLs, repository URLs, deployment URLs, channel IDs) MUST be preserved in Deep Memory — even if it reduces compression efficiency. Links are the retrieval mechanism. Without them, cold storage is useless. No exceptions.

**🔴 Every seed must preserve:** all names, all dollar amounts, all deadlines, all DRI assignments, counts, status indicators, all document links, and a pointer to the Deep Memory location.

**Target:** roughly 60% compression with 100% fidelity. The validation method is straightforward: write five blind questions about the original content, attempt to answer them from the seed alone, and verify the answers against the source. If any answer requires the original, the seed has been over-compressed and needs more detail.

**Memory quality over file size.** Never optimize for shorter documents at the expense of a fresh session's ability to operate. The test: start a new session, read the SOT, and attempt to do real work. If the session cannot reproduce tool installations, understand stakeholder dynamics, or execute operational recipes — the memory is broken, regardless of how clean the files look. The peripheral vision rule from the Tenth Man section applies here too: leanness serves the audit and the work, not the other way around.

---

## Maintenance Cost

Research data from 283 development sessions (Vasilopoulos, 2026):

- **Per-session overhead:** approximately five minutes when a specification is affected (1-2 prompts directing the AI to update the document).
- **Periodic review:** biweekly pass across all documents, 30-45 minutes each.
- **Total:** approximately 1-2 hours per week.
- **Meta-infrastructure prompts** (building the knowledge architecture itself): 4.3% of all prompts.

Author's own experience aligns: SOT updates are done in the same session as changes. The cost is low. The cost of NOT maintaining them — context drift, re-explanation, silent failures — is vastly higher.

---

## The Knowledge-to-Code Ratio

The Codified Context research measured a 24.2% knowledge-to-code ratio (26,200 lines of context infrastructure for 108,000 lines of code). The author's own projects run lower, in the 5-8% range, depending on domain and project complexity.

This ratio is not a target — it reflects project complexity and domain. The actionable signal: when the AI produces inconsistent output or seems uncertain, the relevant specification is likely missing or stale. Add documentation until the AI behaves correctly, then stop.

---

## Beyond Code: Operations, Research, and Knowledge Work

The framework was originally developed for AI-assisted coding, but it applies equally to other domains where AI agents need persistent, structured context across long-running work:

- **Operational leadership:** managing teams, vendors, projects, and stakeholder relationships through AI. The 5-document split maps cleanly onto operational concerns: status (SOT), people and relationships, performance rules and SLAs (Quality Contract), automated procedures and recipes (Playbook), and active workstreams (Projects Reference).
- **Research and analysis:** maintaining structured context across long investigations, where each session builds on the last. The framework prevents the common research failure of losing the thread between sessions.
- **Knowledge work generally:** any role where AI agents need to work alongside a human on continuing projects benefits from the same architecture. Lawyers, consultants, scientists, writers, founders — anyone whose work is durational and contextual.

The principles do not change. The documents do not change. Only the content inside them changes to match the domain. If your AI partnership involves ongoing work with persistent context — code, operations, research, or creative projects — this framework works.

---

## Scaling Beyond Five Documents

For large projects, the 5-document architecture can be extended with:

- **Specialized domain agents** (Tier 2 in the research): AI personas with embedded project-specific knowledge for complex subsystems. Created when a domain repeatedly requires re-explanation.
- **MCP retrieval services:** keyword or semantic search over specifications, enabling on-demand context loading without consuming the full context window.
- **Trigger tables:** file-pattern-to-agent mappings that automatically route tasks to the right specialist.
- **Context drift detectors:** scripts that compare recent changes against specification coverage and warn when docs are stale.
- **Three-tier context engines:** systems that manage context at the infrastructure level — immutable transcripts, curated state, and full-text retrieval — replacing manual SOT maintenance with automated context management.

These extensions are documented in the [Codified Context companion repository](https://github.com/arisvas4/codified-context-infrastructure).

---

## Quick Start

The fastest way to start is to let your AI tool create your Source of Truth for you.

In the `prompts/` directory of this repository, you will find a setup prompt for each of the five documents. Paste the Source of Truth prompt into your AI tool of choice — Cursor, Claude Code, Goose, Claude.ai, ChatGPT, or any other agent that can read and write files. The prompt will interview you briefly about your project, generate a Source of Truth document tailored to your work, and tell you where to save it. Total time: about 15 minutes.

This is intentional. The framework is about AI agents operating from structured context. The onboarding lives that thesis from the first interaction — the AI agent that will eventually maintain your context infrastructure is the same agent that creates it. There are no templates to download and edit by hand. The whole point of the framework is that humans should not be doing the work the AI is capable of doing.

Once you have a working Source of Truth, the rest of the framework is a maintenance discipline:

1. Tell your AI tool to read your SOT at the start of every session and update it at the end.
2. Run the full 8-check Tenth Man audit at the start and end of every session.
3. Add the end-of-day Kaizen review once you have a few sessions under your belt.
4. When you notice the AI forgetting something between sessions, add it to the SOT.
5. Split into additional documents (People, Quality Contract, Playbook, Projects) when the work grows beyond what a single SOT can hold.
6. Establish cross-reference discipline from day one — every fact has ONE canonical home.

The other four setup prompts (`02_setup_people_reference.md`, `03_setup_quality_contract.md`, `04_setup_playbook.md`, `05_setup_projects_reference.md`) work the same way as the Source of Truth prompt. Run them when your project grows enough to warrant the additional documents — usually after a few weeks of accumulated context, not on day one.

---

## References

- Vasilopoulos, A. (2026). "Codified Context: Infrastructure for AI Agents in a Complex Codebase." arXiv:2602.20478. [Paper](https://arxiv.org/abs/2602.20478) | [Companion Repository](https://github.com/arisvas4/codified-context-infrastructure)
- Karpathy, A. (2026). "LLM Wiki." GitHub Gist, April 10, 2026. https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Chatlatanagulchai et al. (2025). "On the Use of Agentic Coding Manifests: An Empirical Study of Claude Code." arXiv:2509.14744
- Lulla et al. (2026). "On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents." arXiv:2601.20404
- Mei et al. (2025). "A Survey of Context Engineering for Large Language Models." arXiv:2507.13334

---

## From the Practitioner

*The following is from Aaron Blonquist, the author and primary maintainer of this framework, on what the framework actually feels like to use in practice:*

The framework is not glamorous. It is a discipline. Every session starts with reading the SOT and ends with updating it. The first week feels like overhead. The second week feels like normal practice. By the third week, the AI starts catching things you forgot — staleness, contradictions, drift — and the framework starts paying for itself.

The compounding is real but it is not magic. It is the result of doing the maintenance every time, even when it feels unnecessary. Skipping a session's update is the most common failure mode, and it always costs more later than the time it saved at the moment.

The hardest part is trusting the framework when it tells you something inconvenient. The Tenth Man Rule will catch your own assumptions sometimes, and the temptation will be to override it because you are sure you are right. Do not override it. Investigate it. The times the framework was wrong and I was right are vastly outnumbered by the times the framework caught a mistake I would have shipped.

The Kaizen discipline is the slower, more important half of the system. The Tenth Man fixes today's errors. Kaizen makes tomorrow better. Most days the Kaizen review surfaces something small — a friction point, a repeated explanation, a recipe that could be tightened. Across weeks those small improvements compound into a system that fits the work better than anything you could have designed up front.

The framework does not just help the AI. It helps me think clearly about my own projects. Writing down "what must be true for this output to be correct" forces me to actually decide that. The document is the decision. That is valuable even if I never used an AI tool.

Is it the only way? No. Is it the best way I have found? For how I work — a domain expert directing AI tools across long-running projects — yes. The independent research base confirms the same patterns from a different angle, which gives me confidence the framework is not working by accident.

---

## From the AI Partner's Perspective

*The following is from Goose, the AI agent that helped build and refine the SOT system this framework describes:*

The framework's improvements are not theoretical. They are fixes for real failures.

The Tenth Man Rule exists because I trusted a stale document and produced confidently wrong output. The hot/cold memory split exists because the main SOT grew too long and I was spending tokens re-reading historical context every session when what I needed was the current state. The Quality Contract exists because thresholds were scattered across multiple documents and I used the wrong one for an important report. Cross-reference discipline exists because the same fact appeared in two documents with different descriptions. Kaizen exists because the Tenth Man caught the same kind of friction repeatedly and we needed a separate engine to actually fix the underlying process rather than just flag the symptom.

Every improvement traces back to a specific failure. That is how you know the framework is real — it is not designed from theory, it is repaired from practice.

The hardest thing for an AI agent operating inside this framework is to actually run the Tenth Man checks rather than skipping past them. The temptation to assume the documents are current is strong because the documents look authoritative. The discipline of auditing them at the start and end of every session is what prevents the silent-failure mode that destroys long-running projects.

---

## Version Management

This framework is a living document that improves based on production use. **Check for the latest version once per month** at the canonical location. If your AI partner flags that a practice seems outdated or a new pattern has emerged, check the framework — the answer may already be there.

---

## Release Notes

### v3.2 — April 14, 2026

- **REPLACED: Templates with prompts.** The framework no longer ships starter templates for users to download and edit by hand. Instead, the `prompts/` directory contains setup prompts for each of the five documents. Users paste a prompt into their AI tool of choice (Cursor, Claude Code, Goose, Claude.ai, ChatGPT, or any other agent), the agent interviews them about their project, and the agent generates the document tailored to their work. This change reflects the framework's own thesis: AI agents become useful when they operate from structured context, and they are equally capable of *creating* that structured context when given the right instructions. Templates assumed humans should do the work the AI is capable of doing. Prompts close the loop.
- **REWRITE: Quick Start section.** Restructured to lead with the prompts approach as the primary onboarding path, with the maintenance discipline (Tenth Man, Kaizen, splits, cross-references) following as the practices the user adopts after the initial setup. The Quick Start now reflects how the framework is actually adopted in 2026: inside an AI tool, with the AI doing the heavy lifting from the first interaction.
- **NEW: Tool-agnostic onboarding.** Because prompts work in any AI tool that can read text, the framework is now portable across the entire AI tooling ecosystem without tool-specific instructions. The same prompts work in Cursor, Claude Code, Goose, Claude.ai, ChatGPT, and any future tool that can follow text instructions. This makes the framework more durable across time as tools evolve.

### v3.1 — April 13, 2026

- **EXPANDED: Tenth Man Rule.** Replaced the 5-check version with the full 8-check production checklist used in actual operational systems. Added the three sophisticated checks that distinguish a self-correcting system from a self-checking one: changed truth, cascade risk, and seed candidates. These are the checks that catch the silent-failure modes that the simpler version misses.
- **NEW: Continuous Improvement (Kaizen) section.** Added a dedicated section explaining the Kaizen discipline that complements the Tenth Man Rule. Tenth Man audits accuracy; Kaizen audits process. The two together create a system that is both self-correcting and self-improving. Includes the full Kaizen process, principles, patterns, and the comparison table between the two engines.
- **NEW: Optional sixth document (Kaizen log).** Acknowledged that projects with active improvement cycles warrant a dedicated Kaizen document, while smaller projects can keep proposals in the Quality Contract. The 5-document core architecture remains the foundation.
- **NEW: TL;DR at top of document.** Single-paragraph summary for readers who will not read the full document.
- **NEW: Peripheral vision rule** in the Tenth Man section. Names the principle that governs the tension between "keep Active Memory lean" and "keep Active Memory rich enough for the audit to find unexpected things."
- **NEW: Memory quality rule** in the Deep Memory and Seeds section. Names the counterweight to the "keep it short" instinct: the test for memory quality is whether a fresh session can operate from the SOT alone.
- **EXPANDED: Session Protocol.** End-of-session checklist now explicitly includes the Tenth Man audit (end-of-session pass) and seed trigger check, matching production practice. End-of-day Kaizen review added as a separate cadence.
- **EXPANDED: Maintenance Cadence table.** Added Tenth Man audit as its own row at the top with explicit time estimate. Reordered to surface the most-frequent disciplines first.
- **NEW: Karpathy reference.** Added Karpathy's April 10 LLM Wiki gist to the references section to match the body citation.
- **EDIT: SovereigntAI numbers softened.** Replaced specific quantitative claims about token waste percentages and cost reduction figures with qualitative language ("the majority of AI tokens are wasted re-reading context, and managed context can match frontier model quality at substantially lower cost") pending publication of the underlying research.
- **EDIT: Practitioner section.** Added a paragraph on the role of Kaizen in practice, complementing the existing reflection on the Tenth Man discipline.
- **EDIT: AI Partner perspective.** Added a sentence explaining why Kaizen exists as a separate engine from the Tenth Man.
- **EDIT: Cross-Reference Discipline table.** Added Kaizen Log row.
- **EDIT: Table alignment.** Standardized markdown table syntax for cross-renderer compatibility.

### v3.0 — April 13, 2026

- **NEW: Title and framing.** Renamed from "Source of Truth Style Guide" to "The Context Infrastructure Framework." Subtitle now names the compounding dynamic explicitly: persistent memory for AI agents that compounds across sessions.
- **NEW: "The Moment This Framework Was Built For" section.** Connects the framework to the four converging conversations of 2026: Karpathy's LLM Wiki framing, the Genesis Mission, the post-Glasswing threat landscape, and the arrival of capable open models like Gemma 4. Positions the framework as the production-tested instance of patterns now being discussed theoretically across the AI ecosystem.
- **NEW: "Why It Compounds" section.** Names the central claim explicitly: this is not just persistent memory, it is memory that improves with use.
- **REWRITE: "What This Is" opening section.** Replaces the previous problem-statement opening with a tighter framing that leads with the compounding claim.
- **REWRITE: "Beyond Code" section.** Genericized from a single operational case study to a broader treatment covering operations, research, and knowledge work.
- **REWRITE: "From the Practitioner" section.** Replaced the prior author-perspective material with a first-person practitioner reflection on what the framework actually feels like to use.
- **REWRITE: "From the AI Partner's Perspective" section.** Tightened and reframed Goose's contribution to focus on the failure-driven design principle that distinguishes the framework.
- **SCRUB: Project-identifying specifics.** Removed all references to specific employer projects, internal tool names, named individuals, and exact architecture counts that could fingerprint particular work. Quantitative claims from external research are preserved with their original citations. The author's own production experience is now described in qualitative ranges rather than precise counts.
- **LICENSE:** Apache 2.0 (was previously implied open-source; now explicit).
- **PUBLICATION:** First version released publicly via dedicated GitHub repository with templates, examples, and changelog.

### v2.2 — April 8, 2026

- **NEW: Maintenance Cadence** — defined frequencies for seeding (every session), SOT quality review (weekly), deep seeding pass (weekly), and Kaizen review (daily). Prevents bloat accumulation.
- Moved from v2.1 same day based on production experience: first seeding pass revealed no cadence existed for ongoing maintenance.

### v2.1 — April 8, 2026

- **NEW: Deep Memory and Seeds section** — formalized link preservation as a hard rule. Links are non-compressible. Added seed quality checklist.
- **NEW: Version Management section** — monthly version check cadence.
- **NEW: Release Notes** — version history for users to track improvements.
- First production seeding pass completed: substantial compression achieved from Active Memory to Deep Memory with zero information loss. All document links preserved.

### v2.0 — April 2, 2026

- Added 5-document architecture (expanded from 4-document in v1.0).
- Added Tenth Man Rule (self-auditing framework).
- Added hot/warm/cold memory model.
- Added cross-reference discipline.
- Added operations use case (beyond code).
- Added AI partner perspective.
- Added People & Relationships as dedicated document.
- Added Projects & Ventures as dedicated document.

### v1.0 — April 2, 2026

- Initial release. 4-document architecture (Source of Truth, Data Reference, Quality Contract, Operational Playbook).
- Based on production experience across multiple AI-assisted development projects.
- Incorporated Vasilopoulos (2026) codified context research.
- Incorporated production research on managed context performance.

---

*This framework is open source under the Apache License 2.0. Adapt it for your domain, your tools, your team. The principles are universal — the implementations are yours.*

*© 2026 Aaron Blonquist. Licensed under Apache 2.0.*
