"""
Entity Resolution — collapse duplicate mentions into canonical entities.

Problem: user mentions "my wife", "Sarah", "her" across different turns.
These are the same person but stored as separate facts.

Solution: maintain a registry of known entities with aliases.
When new facts arrive, check if they reference a known entity.
If so, link them. If not, create a new entity.

Inspired by Cognee's domain vocabulary approach.
"""
import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple


class EntityRegistry:

    def __init__(self, data_dir: str = "~/.memra/entities"):
        self.data_dir = os.path.expanduser(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self._registry_path = os.path.join(self.data_dir, "registry.json")
        self._registry = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._registry_path):
            with open(self._registry_path) as f:
                return json.load(f)
        return {"entities": [], "next_id": 1}

    def _save(self) -> None:
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    def register(self, canonical_name: str, category: str = "person",
                 aliases: Optional[List[str]] = None) -> Dict:
        for entity in self._registry["entities"]:
            if entity["canonical"].lower() == canonical_name.lower():
                if aliases:
                    for alias in aliases:
                        if alias.lower() not in [a.lower() for a in entity["aliases"]]:
                            entity["aliases"].append(alias)
                    self._save()
                return entity

        entity = {
            "id": self._registry["next_id"],
            "canonical": canonical_name,
            "category": category,
            "aliases": aliases or [],
            "facts": [],
        }
        self._registry["next_id"] += 1
        self._registry["entities"].append(entity)
        self._save()
        return entity

    def add_alias(self, canonical_name: str, alias: str) -> bool:
        for entity in self._registry["entities"]:
            if entity["canonical"].lower() == canonical_name.lower():
                if alias.lower() not in [a.lower() for a in entity["aliases"]]:
                    entity["aliases"].append(alias)
                    self._save()
                return True
        return False

    def resolve(self, mention: str) -> Optional[Dict]:
        mention_lower = mention.lower().strip()
        for entity in self._registry["entities"]:
            if entity["canonical"].lower() == mention_lower:
                return entity
            for alias in entity["aliases"]:
                if alias.lower() == mention_lower:
                    return entity
        return None

    def resolve_in_text(self, text: str) -> List[Tuple[str, Dict]]:
        found = []
        text_lower = text.lower()
        for entity in self._registry["entities"]:
            names = [entity["canonical"]] + entity["aliases"]
            for name in names:
                if name.lower() in text_lower:
                    found.append((name, entity))
                    break
        return found

    def add_fact_to_entity(self, canonical_name: str, fact: str) -> bool:
        for entity in self._registry["entities"]:
            if entity["canonical"].lower() == canonical_name.lower():
                if fact not in entity["facts"]:
                    entity["facts"].append(fact)
                    self._save()
                return True
        return False

    def get_all(self) -> List[Dict]:
        return self._registry["entities"]

    def get_context(self) -> str:
        entities = self._registry["entities"]
        if not entities:
            return ""

        lines = ["[KNOWN ENTITIES]"]
        for e in entities:
            aliases = f" (also: {', '.join(e['aliases'])})" if e["aliases"] else ""
            lines.append(f"- {e['canonical']}{aliases} [{e['category']}]")
            for fact in e["facts"][-3:]:
                lines.append(f"  - {fact}")
        return "\n".join(lines)

    def auto_extract_entities(self, text: str) -> List[Dict]:
        """Heuristic extraction of entity-defining statements."""
        extracted = []

        person_patterns = [
            r"(?:my (?:wife|husband|partner|spouse|girlfriend|boyfriend))\s+(?:is\s+)?(\w+)",
            r"(?:my (?:son|daughter|child|kid|baby))\s+(?:is\s+)?(\w+)",
            r"(?:my (?:mom|dad|mother|father|brother|sister))\s+(?:is\s+)?(\w+)",
            r"(?:my (?:boss|manager|cofounder|co-founder|partner))\s+(?:is\s+)?(\w+)",
            r"(?:my (?:friend|colleague|teammate))\s+(\w+)",
        ]

        for pattern in person_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                if len(name) > 1 and name[0].isupper():
                    relationship = match.group(0).split(name)[0].strip()
                    entity = self.register(name, category="person", aliases=[])
                    self.add_fact_to_entity(name, relationship + name)
                    extracted.append(entity)

        project_patterns = [
            r"(?:project|app|product|service|tool|platform)\s+(?:called|named)\s+[\"']?(\w+)[\"']?",
            r"(?:working on|building|developing)\s+(\w+(?:\s+\w+)?)\s+(?:app|project|system)",
        ]

        for pattern in project_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(1).strip()
                if len(name) > 2:
                    entity = self.register(name, category="project")
                    extracted.append(entity)

        return extracted
