import os
from datetime import date

from conftest import REPO
from poc.coach import Coach, OfflineLLM
from poc.keywords import load_keywords
from poc.okf import Bundle

BUNDLE = os.path.join(REPO, "okf-bundle")
KEYWORDS = os.path.join(REPO, "config", "keywords.json")
TODAY = date(2026, 11, 24)


def make_coach():
    bundle = Bundle(BUNDLE)
    keywords = load_keywords(KEYWORDS)
    return Coach(bundle, keywords, OfflineLLM(today=TODAY), today=TODAY)


def test_relance_recommandee_sur_client_002():
    coach = make_coach()
    reply = coach.handle_message("Ou en est le dossier client-002 ? On doit relancer non ?", sender="SM-2")
    assert "RELancer".lower() in reply.lower()
    assert "deal-1003" in reply
    assert "27 jours" in reply


def test_client_003_a_jour():
    coach = make_coach()
    reply = coach.handle_message("Je prepare un rdv avec client-003", sender="SM-2")
    assert "A jour" in reply
    assert "playbook-preparation-rdv" in reply


def test_recuperation_par_mot_cle():
    coach = make_coach()
    matches, concepts = coach.retrieve("parlons de client-001")
    ids = [c.id for c in concepts]
    assert "clients/client-001" in ids
    assert "deals/deal-1001" in ids


def test_fallback_recherche_plein_texte():
    coach = make_coach()
    matches, concepts = coach.retrieve("budget supply chain industrie")
    assert concepts
