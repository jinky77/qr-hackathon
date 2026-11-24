import os
import re
from datetime import datetime, date, timezone

import yaml

RESERVED_FILENAMES = {"index.md", "log.md"}
LINK_RE = re.compile(r"\]\(([^)]+)\)")


def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            frontmatter = yaml.safe_load("\n".join(lines[1:i]))
            body = "\n".join(lines[i + 1:])
            return frontmatter, body
    return None, text


def parse_datetime(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"not a datetime: {value!r}")


class Concept:
    def __init__(self, concept_id, frontmatter, body, path):
        self.id = concept_id
        self.frontmatter = frontmatter or {}
        self.body = body
        self.path = path

    @property
    def type(self):
        return self.frontmatter.get("type")

    @property
    def title(self):
        return self.frontmatter.get("title") or self.id

    @property
    def description(self):
        return self.frontmatter.get("description") or ""

    @property
    def tags(self):
        return self.frontmatter.get("tags") or []

    def searchable_text(self):
        return " ".join([self.id, str(self.title), str(self.description), " ".join(map(str, self.tags)), self.body]).lower()

    def links(self):
        out = []
        for target in LINK_RE.findall(self.body):
            target = target.split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("/"):
                resolved = target[1:]
            else:
                resolved = os.path.normpath(os.path.join(os.path.dirname(self.id), target))
            if resolved.endswith(".md"):
                out.append(resolved[:-3])
        return out


class Bundle:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.concepts = {}
        self.other_files = []
        self._load()

    def _load(self):
        for dirpath, _dirnames, filenames in os.walk(self.root):
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, self.root).replace(os.sep, "/")
                with open(full, encoding="utf-8") as fh:
                    text = fh.read()
                if name in RESERVED_FILENAMES:
                    continue
                frontmatter, body = parse_frontmatter(text)
                concept_id = rel[:-3]
                if isinstance(frontmatter, dict) and frontmatter.get("type"):
                    self.concepts[concept_id] = Concept(concept_id, frontmatter, body, full)
                else:
                    self.other_files.append(concept_id)

    def get(self, concept_id):
        return self.concepts.get(concept_id)

    def all(self):
        return list(self.concepts.values())

    def by_tag(self, tag):
        return [c for c in self.concepts.values() if tag in c.tags]

    def search(self, query, limit=10):
        tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) >= 4]
        scored = []
        for c in self.concepts.values():
            text = c.searchable_text()
            score = sum(text.count(t) for t in tokens)
            if score:
                scored.append((score, c))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [c for _score, c in scored[:limit]]

    def linked_concepts(self, concept, max_depth=1):
        seen = {concept.id}
        frontier = [concept]
        result = []
        for _ in range(max_depth):
            nxt = []
            for c in frontier:
                for link in c.links():
                    if link in seen:
                        continue
                    seen.add(link)
                    target = self.concepts.get(link)
                    if target is not None:
                        result.append(target)
                        nxt.append(target)
            frontier = nxt
        return result

    def is_stale(self, concept, today=None):
        today = today or datetime.now(timezone.utc)
        if not isinstance(today, datetime):
            today = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        if concept.frontmatter.get("status") == "deprecated":
            return True
        stale_after = concept.frontmatter.get("stale_after")
        if stale_after:
            return parse_datetime(stale_after) < today
        return False

    def validate(self):
        errors = []
        for concept in self.concepts.values():
            if not isinstance(concept.frontmatter, dict):
                errors.append(f"{concept.id}: frontmatter non conforme (mapping YAML attendu)")
            elif not concept.frontmatter.get("type"):
                errors.append(f"{concept.id}: champ 'type' manquant ou vide")
        root_index = os.path.join(self.root, "index.md")
        if not os.path.isfile(root_index):
            errors.append("index.md manquant à la racine du bundle")
        else:
            with open(root_index, encoding="utf-8") as fh:
                fm, _body = parse_frontmatter(fh.read())
            if not isinstance(fm, dict) or not fm.get("okf_version"):
                errors.append("index.md racine: 'okf_version' manquant dans le frontmatter")
        return errors
