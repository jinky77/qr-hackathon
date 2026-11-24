import os
import shutil

from conftest import REPO
from poc.ingest_hubspot import ingest
from poc.okf import Bundle

CSV = os.path.join(REPO, "data", "hubspot_export_sample.csv")


def test_ingest_generates_conform_bundle(tmp_path):
    bundle_dir = tmp_path / "okf-bundle"
    shutil.copytree(os.path.join(REPO, "okf-bundle"), bundle_dir)
    summary = ingest(CSV, str(bundle_dir), csv_resource="data/hubspot_export_sample.csv", at="2026-11-24T12:00:00Z")
    assert summary == {"clients": 3, "deals": 4}
    bundle = Bundle(str(bundle_dir))
    assert bundle.validate() == []
    deal = bundle.get("deals/deal-1003")
    assert deal.type == "Deal"
    assert str(deal.frontmatter["x-dixit-montant_eur"]) == "450000"
    assert str(deal.frontmatter["x-dixit-last_contact_date"]) == "2026-10-28"
    assert "clients/client-002" in deal.links()
    client = bundle.get("clients/client-002")
    assert client.frontmatter["generated"]["by"] == "process:ingest-hubspot"
    with open(os.path.join(str(bundle_dir), "log.md"), encoding="utf-8") as fh:
        assert "ingest-hubspot" in fh.read()
