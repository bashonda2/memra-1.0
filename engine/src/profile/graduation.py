"""
Graduation engine — converts raw observations into capabilities.

Raw: "uses PostgreSQL", "uses Redis", "prefers concise answers"
Graduated: "Backend databases: proficient (PostgreSQL, Redis)"
           "Communication: prefers concise, direct responses"

Graduated profile is smaller and more actionable than raw facts.
"""
from collections import Counter, defaultdict
from typing import Dict, List


SKILL_GROUPS = {
    "backend": {"FastAPI", "Django", "Flask", "Express", "Spring", "Rails", "Go"},
    "frontend": {"React", "Vue", "Angular", "TypeScript", "Next.js", "Svelte"},
    "databases": {"PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "DynamoDB"},
    "infrastructure": {"Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform"},
    "ml_ai": {"PyTorch", "TensorFlow", "MLX", "Ollama", "LangChain"},
    "dev_tools": {"Git", "GitHub", "Cursor", "VSCode", "Claude", "ChatGPT"},
}

PROFICIENCY = {
    (1, 2): "mentioned",
    (3, 5): "familiar",
    (6, 10): "proficient",
    (11, 999): "expert",
}


def _proficiency_level(count: int) -> str:
    for (low, high), level in PROFICIENCY.items():
        if low <= count <= high:
            return level
    return "mentioned"


def graduate(facts: List[Dict]) -> str:
    if not facts:
        return ""

    tech_mentions = defaultdict(int)
    preferences = []
    context_facts = []

    for fact in facts:
        text = fact.get("text", "").lower()
        count = fact.get("evidence_count", 1)

        matched = False
        for group, members in SKILL_GROUPS.items():
            for tech in members:
                if tech.lower() in text:
                    tech_mentions[(group, tech)] += count
                    matched = True

        if any(kw in text for kw in ["prefer", "like", "want", "love", "hate"]):
            preferences.append(fact["text"])
        elif not matched:
            context_facts.append(fact["text"])

    lines = ["[USER — graduated capabilities]"]

    by_group = defaultdict(list)
    for (group, tech), count in tech_mentions.items():
        by_group[group].append((tech, count))

    for group, techs in sorted(by_group.items()):
        techs_sorted = sorted(techs, key=lambda t: -t[1])
        max_count = techs_sorted[0][1]
        level = _proficiency_level(max_count)
        tech_names = ", ".join(t[0] for t in techs_sorted)
        lines.append(f"- {group.replace('_', ' ').title()}: {tech_names} ({level})")

    for pref in preferences[:5]:
        lines.append(f"- {pref}")

    for ctx in context_facts[:5]:
        lines.append(f"- {ctx}")

    return "\n".join(lines) if len(lines) > 1 else ""
