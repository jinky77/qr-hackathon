import json


def load_keywords(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    keywords = data.get("keywords", [])
    for kw in keywords:
        kw["pattern"] = kw["pattern"].lower()
    return keywords


def detect(text, keywords):
    lowered = text.lower()
    matches = []
    for kw in keywords:
        if kw["pattern"] in lowered:
            matches.append(kw)
    return matches


def matched_concept_ids(matches):
    seen = []
    for kw in matches:
        for concept_id in kw.get("concepts", []):
            if concept_id not in seen:
                seen.append(concept_id)
    return seen
