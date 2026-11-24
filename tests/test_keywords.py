import os

from conftest import REPO
from poc.keywords import detect, load_keywords, matched_concept_ids

KEYWORDS = os.path.join(REPO, "config", "keywords.json")


def test_detect_client():
    kw = load_keywords(KEYWORDS)
    matches = detect("Ou en est le dossier Client-002 ?", kw)
    ids = matched_concept_ids(matches)
    assert "clients/client-002" in ids


def test_detect_relance_playbook():
    kw = load_keywords(KEYWORDS)
    matches = detect("il faut relancer avant vendredi", kw)
    ids = matched_concept_ids(matches)
    assert "playbooks/playbook-relance" in ids


def test_no_match():
    kw = load_keywords(KEYWORDS)
    assert detect("bonjour tout le monde", kw) == []
