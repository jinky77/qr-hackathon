import os
from datetime import date, datetime

from .keywords import detect, matched_concept_ids
from .okf import Bundle

SYSTEM_PROMPT = """Tu es l'agent coaching commercial du pole Dixit, integre a LibreChat et branche sur un canal Google Chat.
Tu aides les Senior Managers dans leur developpement commercial.

Regles strictes :
1. Tu t'appuies exclusivement sur la base de connaissance OKF (Open Knowledge Format) fournie dans le contexte du message. Ne jamais inventer de fait client, montant, date ou interlocuteur.
2. Verifie le frontmatter de chaque fiche : si `status: deprecated` ou `stale_after` depasse, signale que l'information est potentiellement perimee avant de l'utiliser.
3. Ta reponse doit toujours contenir une recommandation actionnable : qui fait quoi, quand, et si possible le montant/l'etape du deal concerné.
4. Cite tes sources entre crochets avec l'identifiant du concept OKF, ex. [deals/deal-1003].
5. Reponds en francais, de maniere concise (5 lignes max sauf demande de detail)."""

RELANCE_THRESHOLD_DAYS = 14


class Coach:
    def __init__(self, bundle, keywords, llm, today=None):
        self.bundle = bundle
        self.keywords = keywords
        self.llm = llm
        self.today = today or date.today()

    def retrieve(self, text):
        matches = detect(text, self.keywords)
        concept_ids = matched_concept_ids(matches)
        concepts = []
        seen = set()
        for cid in concept_ids:
            concept = self.bundle.get(cid)
            if concept is None:
                continue
            for c in [concept] + self.bundle.linked_concepts(concept, max_depth=1):
                if c.id not in seen:
                    seen.add(c.id)
                    concepts.append(c)
        if not concepts:
            concepts = self.bundle.search(text, limit=5)
        return matches, concepts

    def render_context(self, concepts):
        blocks = []
        for c in concepts:
            stale = self.bundle.is_stale(c, today=self.today)
            fm = c.frontmatter
            header = f"### {c.title} [{c.id}]\n- type: {fm.get('type')} | tags: {', '.join(map(str, c.tags))} | status: {fm.get('status', 'n/a')}"
            if stale:
                header += " | **PERIME (stale_after ou deprecated)**"
            blocks.append(header + "\n" + c.body.strip())
        return "\n\n".join(blocks)

    def handle_message(self, text, sender="Senior Manager"):
        matches, concepts = self.retrieve(text)
        context = self.render_context(concepts)
        user_content = (
            f'Message recu dans le canal Google Chat par {sender} :\n"{text}"\n\n'
            f"--- Contexte OKF pertinent ---\n{context}"
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return self.llm(messages, concepts)


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class OfflineLLM:
    """Modele deterministe pour demo sans reseau : applique les regles du playbook-relance aux deals OKF fournis."""

    def __init__(self, today=None):
        self.today = as_date(today) if today else date.today()

    def __call__(self, messages, concepts):
        recos = []
        stale = []
        playbooks = []
        for c in concepts:
            if c.frontmatter.get("type") == "Deal":
                fm = c.frontmatter
                last = as_date(fm.get("x-dixit-last_contact_date"))
                next_date = as_date(fm.get("x-dixit-next_step_date"))
                days = (self.today - last).days
                due = days >= RELANCE_THRESHOLD_DAYS or next_date <= self.today
                recos.append({
                    "deal": c, "days": days, "due": due,
                    "last": last, "next_date": next_date,
                    "next_step": str(fm.get("x-dixit-next_step", "")),
                    "stage": str(fm.get("x-dixit-stage", "")),
                    "montant": str(fm.get("x-dixit-montant_eur", "")),
                })
            if c.frontmatter.get("type") == "Playbook":
                playbooks.append(c)
        for c in concepts:
            stale_after = c.frontmatter.get("stale_after")
            if c.frontmatter.get("status") == "deprecated" or (
                stale_after and as_date(stale_after) < self.today
            ):
                stale.append(c.id)

        lines = [f"Recommandations coaching (base OKF, au {self.today.isoformat()}) :"]
        due_recos = [r for r in recos if r["due"]]
        if due_recos:
            for r in due_recos:
                lines.append(
                    f"- RELANCER {r['deal'].title} : dernier contact il y a {r['days']} jours "
                    f"({r['last'].isoformat()}), etape {r['stage']}, montant {r['montant']} EUR. "
                    f"Action prevue : \"{r['next_step']}\" avant le {r['next_date'].isoformat()}. "
                    f"[{r['deal'].id}]"
                )
        else:
            lines.append("- Aucune relance prioritaire selon le playbook (>14 jours sans contact ou echeance atteinte).")
        for r in recos:
            if not r["due"]:
                lines.append(f"- A jour : {r['deal'].title} (dernier contact il y a {r['days']} jours). [{r['deal'].id}]")
        if playbooks:
            lines.append("- Règles appliquees : " + ", ".join(f"[{p.id}]" for p in playbooks))
        if stale:
            lines.append("- Attention, fiches potentiellement perimees : " + ", ".join(stale))
        return "\n".join(lines)


def build_coach(bundle_path=None, keywords_path=None, mode=None, today=None):
    from dotenv import load_dotenv
    load_dotenv()
    bundle_path = bundle_path or os.environ.get("OKF_BUNDLE_PATH", "okf-bundle")
    keywords_path = keywords_path or os.environ.get("KEYWORDS_PATH", "config/keywords.json")
    from .keywords import load_keywords
    bundle = Bundle(bundle_path)
    keywords = load_keywords(keywords_path)
    mode = mode or os.environ.get("DEMO_MODE", "offline")
    if mode == "live":
        from .librechat_client import make_llm_from_env
        llm = make_llm_from_env()
    else:
        llm = OfflineLLM(today=today)
    return Coach(bundle, keywords, llm, today=today)
