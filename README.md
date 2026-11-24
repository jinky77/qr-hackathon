# PoC OKF × Agent coaching commercial — Pôle Dixit (hackathon)

PoC démontrable en séminaire : un **agent coaching commercial** dans LibreChat, branché sur un canal **Google Chat**, qui s'appuie sur une **base de connaissance au format OKF** (Open Knowledge Format v0.3 — répertoire de fichiers Markdown + frontmatter YAML, lisible par humains et agents) pour aider les Senior Managers du pôle Dixit à relancer leurs clients et préparer leurs RDV.

## Architecture

```
Senior Managers pôle Dixit ──discutent──▶ Bot Google Chat (canal #dixit-commercial)
                                                    │ webhook / poll (mot-clé détecté)
                                                    ▼
                                     pont GChat  (src/poc/gchat_bridge.py)
                                                    │ message + contexte OKF
                                                    ▼
                                     LibreChat API (src/poc/librechat_client.py)
                                                    │ agent + Skill "okf-dixit-coach"
                                                    ▼
                                     Base de connaissance OKF  (okf-bundle/)
                                     ◀── alimentée par : export CSV HubSpot (manuel d'abord,
                                           MCP HubSpot ensuite), canal GChat, mails exportés
```

## Contenu du repo

| Chemin | Rôle |
|---|---|
| `okf-bundle/` | Base de connaissance OKF v0.3 : `index.md` racine (`okf_version`), `log.md`, `clients/`, `deals/`, `signaux/`, `playbooks/` |
| `skill/SKILL.md` | Skill agent (format agentskills.io) : règles de lecture/écriture OKF pour l'agent LibreChat |
| `scripts/package_skill.py` | Package `SKILL.md` + `okf-bundle/` en un zip uploadable dans LibreChat (`dist/`) |
| `scripts/validate_okf.py` | Lint de conformité OKF (frontmatter YAML + `type` requis sur chaque concept) |
| `src/poc/okf.py` | Lecteur de bundle OKF : concepts, liens, tags, recherche, péremption (`status`/`stale_after`) |
| `src/poc/keywords.py` | Détection de mots-clés dans les messages GChat → concepts OKF à charger |
| `src/poc/ingest_hubspot.py` | Export CSV HubSpot → fiches OKF `clients/` + `deals/` (+ index + log) |
| `src/poc/coach.py` | Orchestrateur : message → mots-clés → contexte OKF → prompt → réponse (LLM live ou déterministe offline) |
| `src/poc/librechat_client.py` | Client API LibreChat (endpoint à câbler — cf. Anthony) |
| `src/poc/gchat_bridge.py` | Pont GChat : webhook HTTP, poller Chat API, ou simulation CLI |
| `src/poc/demo.py` | Scénario de démo scripté (4 messages) pour la séance |
| `config/keywords.json` | Mot-clé → concepts OKF (client-001…003, deal-…, relance, rdv, portefeuille) |
| `data/hubspot_export_sample.csv` | Export HubSpot **anonymisé** (Client-001…, DEAL-…, SM-…) |
| `tests/` | Tests unitaires (lecteur OKF, mots-clés, ingestion, coach offline) |

## Prérequis

- Python 3.11+ ; `pip install -r requirements.txt` (+ `-r requirements-dev.txt` pour les tests)
- Une instance LibreChat avec upload de skills (zip `SKILL.md` à la racine)
- `.env` à partir de `.env.example` (voir section sécurité)

## Mise en route

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # puis renseigner

# 1. Valider la conformité OKF du bundle
python scripts/validate_okf.py okf-bundle

# 2. (Re)générer clients & deals depuis un export HubSpot (CSV anonymisé)
PYTHONPATH=src python -m poc.ingest_hubspot data/hubspot_export_sample.csv --bundle okf-bundle

# 3. Packager la skill et l'uploader dans LibreChat (panneau Skills → upload zip)
python scripts/package_skill.py   # produit dist/okf-dixit-coach-skill.zip

# 4. Tests
python -m pytest tests -q
```

## Démo en séance

**Mode offline (recommandé en secours / sans réseau)** — déterministe, sans appel LLM :

```bash
PYTHONPATH=src python -m poc.demo --mode offline --today 2026-11-24
```

Scénario joué : `client-002` → relance recommandée (dernier contact il y a 27 j, DEAL-1003 450 k€) ; `client-001` → DEAL-1001 à relancer ; `client-003` + « rdv » → playbook préparation ; « portefeuille » → vue d'ensemble.

**Mode live** — le pont écoute les événements GChat et appelle LibreChat :

```bash
PYTHONPATH=src python -m poc.demo --mode live                 # transcript via API LibreChat
PYTHONPATH=src python -m poc.gchat_bridge serve --port 8080    # webhook: POST /gchat/webhook
PYTHONPATH=src python -m poc.gchat_bridge poll                 # alternative: polling Chat API
PYTHONPATH=src python -m poc.gchat_bridge simulate "Où en est client-002 ?"
```

## Sécurité & conformité

- Données **anonymisées uniquement** dans le PoC (Client-001/002/003, SM-1/2) ; à remplacer par un vrai export HubSpot pseudonymisé avec validation du pôle Dixit (RGPD : mails et discussions internes = données sensibles).
- Aucun secret en dur : tout passe par `.env` (`LIBRECHAT_API_KEY`, `GCHAT_ACCESS_TOKEN`…) — ne jamais committer `.env`.
- Conformité OKF vérifiable à tout moment : `python scripts/validate_okf.py okf-bundle`.

## Limites du PoC / TODO

- Endpoint exact de l'API LibreChat à câbler (avec Anthony) : `LIBRECHAT_BASE_URL` + `LIBRECHAT_ENDPOINT` + clé API.
- HubSpot : export CSV manuel d'abord ; MCP HubSpot en second temps.
- Sources GChat/mails : exports anonymisés ; ingestion automatique à définir.
- Le mode `live` délègue le raisonnement au LLM de LibreChat ; le mode `offline` applique les règles du playbook de façon déterministe (même contexte OKF injecté).
