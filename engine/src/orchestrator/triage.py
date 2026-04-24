"""
Triage Classifier — Routes queries as ROUTINE or SYNTHESIS.

Design: default to ROUTINE (local/cheap). Escalate to SYNTHESIS (frontier)
only when positive signals are detected. This eliminates the need to
enumerate every possible routine query.

Three layers:
  1. Regex: fast pattern matching for clear signals
  2. Confidence gate: borderline cases escalate
  3. LLM pre-screen: optional cheap call for ambiguous cases (future)
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("memra.triage")


@dataclass
class TriageResult:
    route: str
    complexity_score: float
    confidence: float
    reasoning: str
    matched_signals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "route": self.route,
            "complexity_score": round(self.complexity_score, 3),
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "matched_signals": self.matched_signals,
        }


LOCAL_SIGNALS = [
    (r"generate\s+a\s+short\s+title", 2.0, "title_generation"),
    (r"---END USER MESSAGES---", 2.0, "metadata_wrapper"),
    (r"\b(summarize|title|name)\s+(the\s+)?(above|previous|this)\s+(message|conversation)", 1.5, "summarize_meta"),
]

FRONTIER_SIGNALS = [
    (r"\b(design|architect|plan)\s+(a|the|an)\b", 0.8, "architecture"),
    (r"\b(how should|what('s| is) the best way to|tradeoff|trade-off)\b", 0.7, "design_decision"),
    (r"\b(pattern|approach|strategy|framework)\s+(for|to)\b", 0.6, "strategy"),

    (r"\b(debugg?\w*|diagnos\w*|investigat\w*|root cause|intermittent)\b", 0.7, "complex_debug"),
    (r"\b(why (does|is|isn't|doesn't)|what('s| is) (wrong|causing))\b", 0.6, "why_question"),

    (r"\b(analog\w*|parallels?|compar\w+|contrast\w*)\b", 0.7, "cross_domain"),
    (r"\bhow would\s+(a|an|the)\s+\w+\s+(approach|handle|solve|think about)\b", 0.8, "perspective_transfer"),

    (r"\b(algorithm|optimize|optimization|complexity analysis)\b", 0.6, "algorithm"),
    (r"\b(implement|build)\s+(a|the)\s+\w+\s+(system|engine|pipeline|framework)\b", 0.7, "system_build"),

    (r"\b(evaluate|interpret|analyze|assess)\b", 0.5, "interpretation"),
    (r"\b(explain why|reasoning|insight|implication)\b", 0.6, "deep_reasoning"),

    (r"\b(write|draft|compose)\s+(a|an)\s+(essay|article|report|whitepaper|analysis)\b", 0.6, "creative_writing"),

    (r"\b(refactor|restructure|redesign|rethink)\b", 0.6, "refactoring"),

    (r"\b(security|vulnerabilit|injection|auth)\b", 0.6, "security"),

    (r"\b(help me (understand|think|figure|decide|plan))\b", 0.5, "help_understand"),
    (r"\b(what are the (pros|cons|advantages|disadvantages|options))\b", 0.5, "tradeoff_analysis"),

    (r"\b(build|create|develop|implement)\s+(a|an|the|my)\s+\w+\s+(app|system|platform|service|tool|api)\b", 0.7, "build_system"),

    (r"\b(think through|reason about|break down|unpack)\b", 0.4, "deep_think"),
]


class TriageClassifier:

    def __init__(self, frontier_threshold: float = 0.5):
        self.frontier_threshold = frontier_threshold

    def classify(self, request: str) -> TriageResult:
        request_lower = request.lower()
        matched_signals = []

        local_score = 0.0
        for pattern, weight, label in LOCAL_SIGNALS:
            if re.search(pattern, request_lower, re.IGNORECASE):
                local_score += weight
                matched_signals.append(f"local:{label}({weight})")

        frontier_score = 0.0
        frontier_matches = []
        for pattern, weight, label in FRONTIER_SIGNALS:
            if re.search(pattern, request_lower, re.IGNORECASE):
                frontier_score += weight
                frontier_matches.append((weight, label))
                matched_signals.append(f"frontier:{label}({weight})")

        if request.count("?") >= 3:
            frontier_score += 0.2
            matched_signals.append("frontier:multi_question(0.2)")

        if "```" in request:
            frontier_score += 0.15
            matched_signals.append("frontier:code_block(0.15)")

        if frontier_score == 0:
            return TriageResult(
                route="local",
                complexity_score=0.0,
                confidence=0.9,
                reasoning="No synthesis signals — routing local.",
                matched_signals=matched_signals,
            )

        total = local_score + frontier_score
        complexity = frontier_score / total if total > 0 else 1.0
        route = "frontier" if complexity >= self.frontier_threshold else "local"

        distance = abs(complexity - self.frontier_threshold)
        confidence = min(1.0, 0.5 + distance)

        if route == "local":
            top = sorted([(w, l) for w, l in [(local_score, "local_override")]], key=lambda x: -x[0])[:3]
            reasoning = f"Local override. Score={complexity:.2f} < threshold={self.frontier_threshold:.2f}"
        else:
            top = sorted(frontier_matches, key=lambda x: -x[0])[:3]
            reasons = ", ".join(f"{l}({w})" for w, l in top)
            reasoning = f"Synthesis: {reasons}. Score={complexity:.2f} >= threshold={self.frontier_threshold:.2f}"

        return TriageResult(
            route=route,
            complexity_score=round(complexity, 3),
            confidence=round(confidence, 3),
            reasoning=reasoning,
            matched_signals=matched_signals,
        )


def classify_query(query: str, threshold: float = 0.5) -> TriageResult:
    return TriageClassifier(frontier_threshold=threshold).classify(query)
