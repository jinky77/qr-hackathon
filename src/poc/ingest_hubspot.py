import argparse
import csv
import os
from datetime import datetime, timezone

from .okf import Bundle

CLIENT_TEMPLATE = """---
type: Client
title: {cid} — Secteur {secteur}
description: Compte {secteur} du pole Dixit (donnees HubSpot anonymisees), proprietaire {owner}.
tags: [client, {secteur}]
x-dixit-secteur: {secteur}
x-dixit-owner: {owner}
sources:
  - resource: {csv_resource}
    id: hubspot-export
    title: Export manuel HubSpot (donnees anonymisees)
    last_modified: {at}
generated:
  by: process:ingest-hubspot
  at: {at}
status: stable
---
# Opportunites en cours
{deals_list}
# Dernier contact
{last_contact}
# Prochaines actions
{next_steps}
# Citations
[1] Export HubSpot anonymise — `{csv_resource}`
"""

DEAL_TEMPLATE = """---
type: Deal
title: {deal_id} — {deal_name} ({cid})
description: Deal de {montant} EUR avec {cid} ({secteur}), etape {stage}.
tags: [deal, {secteur}]
x-dixit-client: /clients/{client_file}.md
x-dixit-montant_eur: {montant}
x-dixit-stage: {stage}
x-dixit-last_contact_date: {last_contact}
x-dixit-next_step: {next_step}
x-dixit-next_step_date: {next_step_date}
x-dixit-owner: {owner}
sources:
  - resource: {csv_resource}
    id: hubspot-export
    title: Export manuel HubSpot (donnees anonymisees)
    last_modified: {at}
generated:
  by: process:ingest-hubspot
  at: {at}
status: stable
---
# Resume
Deal de {montant} EUR avec [{cid}](/clients/{client_file}.md), etape {stage}, proprietaire {owner}.
# Historique
- {last_contact} : dernier contact.
# Prochaines actions
- {next_step} avant le {next_step_date}. Voir [playbook relance](/playbooks/playbook-relance.md).
# Citations
[1] Export HubSpot anonymise — `{csv_resource}`
"""


def slug_client(cid):
    return "client-" + cid.split("-")[-1].lower()


def slug_deal(deal_id):
    return deal_id.lower()


def ingest(csv_path, bundle_root, csv_resource=None, at=None):
    at = at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    csv_resource = csv_resource or os.path.relpath(os.path.abspath(csv_path), os.path.abspath(bundle_root + "/.."))
    with open(csv_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    clients = {}
    for row in rows:
        clients.setdefault(row["client_id"], {"secteur": row["secteur"], "owner": row["owner"], "deals": []})
        clients[row["client_id"]]["deals"].append(row)

    clients_dir = os.path.join(bundle_root, "clients")
    deals_dir = os.path.join(bundle_root, "deals")
    os.makedirs(clients_dir, exist_ok=True)
    os.makedirs(deals_dir, exist_ok=True)

    for cid, info in clients.items():
        client_file = slug_client(cid)
        deals_list = "\n".join(
            f"- [{d['deal_id']} — {d['deal_name']}](/deals/{slug_deal(d['deal_id'])}.md) : {d['montant_eur']} EUR, etape {d['stage']}"
            for d in info["deals"]
        )
        last_contact = max(d["last_contact_date"] for d in info["deals"])
        next_steps = "\n".join(
            f"- {d['next_step']} (echeance {d['next_step_date']}) — deal [{d['deal_id']}](/deals/{slug_deal(d['deal_id'])}.md)"
            for d in info["deals"]
        )
        content = CLIENT_TEMPLATE.format(
            cid=cid, secteur=info["secteur"], owner=info["owner"], csv_resource=csv_resource,
            at=at, deals_list=deals_list, last_contact=last_contact, next_steps=next_steps,
        )
        with open(os.path.join(clients_dir, client_file + ".md"), "w", encoding="utf-8") as fh:
            fh.write(content)

    for cid, info in clients.items():
        client_file = slug_client(cid)
        for d in info["deals"]:
            content = DEAL_TEMPLATE.format(
                deal_id=d["deal_id"], deal_name=d["deal_name"], cid=cid, client_file=client_file,
                montant=d["montant_eur"], secteur=info["secteur"], stage=d["stage"],
                last_contact=d["last_contact_date"], next_step=d["next_step"],
                next_step_date=d["next_step_date"], owner=d["owner"], csv_resource=csv_resource, at=at,
            )
            with open(os.path.join(deals_dir, slug_deal(d["deal_id"]) + ".md"), "w", encoding="utf-8") as fh:
                fh.write(content)

    _regenerate_index(bundle_root, "clients")
    _regenerate_index(bundle_root, "deals")
    _append_log(bundle_root, at, f"**Update**: (re)generation de {len(clients)} clients et {len(rows)} deals depuis `{csv_resource}` (process:ingest-hubspot).")
    return {"clients": len(clients), "deals": len(rows)}


def _regenerate_index(bundle_root, subdir):
    directory = os.path.join(bundle_root, subdir)
    bundle = Bundle(bundle_root)
    lines = [f"# {subdir.capitalize()}", ""]
    for concept in sorted(bundle.all(), key=lambda c: c.id):
        if concept.id.startswith(subdir + "/"):
            lines.append(f"- [{concept.title}]({os.path.basename(concept.id)}.md) - {concept.description}")
    with open(os.path.join(directory, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _append_log(bundle_root, at, entry):
    log_path = os.path.join(bundle_root, "log.md")
    day = at[:10]
    with open(log_path, encoding="utf-8") as fh:
        content = fh.read()
    if f"## {day}" not in content:
        content = content.rstrip() + f"\n\n## {day}\n"
    content = content.rstrip() + f"\n- {entry}\n"
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(content)


def main():
    parser = argparse.ArgumentParser(description="Ingerer un export CSV HubSpot dans le bundle OKF (clients + deals).")
    parser.add_argument("csv_path")
    parser.add_argument("--bundle", default=os.environ.get("OKF_BUNDLE_PATH", "okf-bundle"))
    args = parser.parse_args()
    summary = ingest(args.csv_path, args.bundle)
    print(f"OK: {summary['clients']} clients, {summary['deals']} deals ingestes dans {args.bundle}")


if __name__ == "__main__":
    main()
