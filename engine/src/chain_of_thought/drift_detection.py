"""
Drift Detection — flag when conversation diverges from active goal.

If the last N turns don't relate to any active goal, something went wrong.
Either the user changed direction (update the goal) or the model drifted
(refocus on the goal).

Uses keyword overlap between recent turns and active goal descriptions.
Not perfect, but catches obvious drift without requiring an LLM call.
"""
import re
from typing import Dict, List, Optional, Set, Tuple


def _extract_keywords(text: str) -> Set[str]:
    """Extract meaningful words, dropping stopwords and short words."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "about",
        "that", "this", "it", "its", "and", "or", "but", "not", "no", "if",
        "then", "than", "when", "what", "which", "who", "how", "where", "why",
        "all", "each", "every", "some", "any", "few", "more", "most", "other",
        "such", "only", "same", "so", "just", "also", "very", "much", "well",
        "here", "there", "now", "up", "out", "them", "they", "their", "you",
        "your", "we", "our", "me", "my", "i", "he", "she", "his", "her",
    }
    words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
    return words - stopwords


def check_drift(
    recent_messages: List[str],
    active_goals: List[Dict],
    threshold: float = 0.15,
) -> Dict:
    """Check if recent conversation has drifted from active goals.

    Args:
        recent_messages: Last N user messages.
        active_goals: List of goal dicts with 'description' and 'subgoals'.
        threshold: Minimum keyword overlap ratio to consider on-track.

    Returns:
        Dict with 'drifted' bool, 'overlap_score', 'suggestion'.
    """
    if not active_goals or not recent_messages:
        return {
            "drifted": False,
            "overlap_score": 1.0,
            "reason": "No active goals or no recent messages to compare.",
        }

    goal_keywords = set()
    for goal in active_goals:
        goal_keywords |= _extract_keywords(goal.get("description", ""))
        for sg in goal.get("subgoals", []):
            if isinstance(sg, dict):
                goal_keywords |= _extract_keywords(sg.get("description", ""))
            elif isinstance(sg, str):
                goal_keywords |= _extract_keywords(sg)

    if not goal_keywords:
        return {
            "drifted": False,
            "overlap_score": 1.0,
            "reason": "Goal descriptions too short to analyze.",
        }

    message_keywords = set()
    for msg in recent_messages[-5:]:
        message_keywords |= _extract_keywords(msg)

    if not message_keywords:
        return {
            "drifted": False,
            "overlap_score": 1.0,
            "reason": "Recent messages too short to analyze.",
        }

    overlap = goal_keywords & message_keywords
    overlap_score = len(overlap) / len(goal_keywords) if goal_keywords else 0

    drifted = overlap_score < threshold

    if drifted:
        goal_descs = [g.get("description", "") for g in active_goals]
        suggestion = (
            f"The last {len(recent_messages)} turns don't seem related to the active "
            f"goal(s): {'; '.join(goal_descs[:2])}. Either update the goal or refocus."
        )
    else:
        suggestion = ""

    return {
        "drifted": drifted,
        "overlap_score": round(overlap_score, 3),
        "overlapping_keywords": sorted(overlap)[:10],
        "reason": suggestion if drifted else "On track.",
    }
