import os
from datetime import datetime, timezone

from conftest import REPO
from poc.okf import Bundle, parse_frontmatter

BUNDLE = os.path.join(REPO, "okf-bundle")


def test_bundle_loads_and_validates():
    bundle = Bundle(BUNDLE)
    assert len(bundle.concepts) >= 10
    assert bundle.validate() == []


def test_required_type_present():
    bundle = Bundle(BUNDLE)
    for concept in bundle.all():
        assert concept.type, concept.id


def test_get_and_search():
    bundle = Bundle(BUNDLE)
    c = bundle.get("clients/client-002")
    assert c is not None and c.type == "Client"
    hits = bundle.search("supply chain industrie")
    assert any("deal-1003" in h.id or "client-002" in h.id for h in hits)


def test_cross_links_resolve():
    bundle = Bundle(BUNDLE)
    deal = bundle.get("deals/deal-1003")
    links = deal.links()
    assert "clients/client-002" in links
    assert "playbooks/playbook-relance" in links


def test_staleness_detection():
    bundle = Bundle(BUNDLE)
    deal = bundle.get("deals/deal-1003")
    assert not bundle.is_stale(deal, today=datetime(2026, 11, 24, tzinfo=timezone.utc))
    fm, body = parse_frontmatter("---\ntype: X\nstale_after: 2026-01-01T00:00:00Z\n---\nbody")
    stale_concept = type(deal)("tmp/x", fm, body, "x")
    assert bundle.is_stale(stale_concept, today=datetime(2026, 11, 24, tzinfo=timezone.utc))


def test_frontmatter_parse():
    fm, body = parse_frontmatter("---\ntype: Deal\ntitle: T\n---\n# Corps\ntexte")
    assert fm == {"type": "Deal", "title": "T"}
    assert "# Corps" in body
    fm2, body2 = parse_frontmatter("pas de frontmatter")
    assert fm2 is None
