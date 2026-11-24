import argparse
import os
from datetime import date

from dotenv import load_dotenv

from .coach import build_coach

SCENARIO = [
    ("SM-2", "Bonjour, ou en est le dossier client-002 ? On doit relancer, non ?"),
    ("SM-1", "Il faut qu'on relance client-001 avant la fin de semaine, tu confirmes ?"),
    ("SM-2", "Je prepare un rdv avec client-003 la semaine prochaine, aide-moi."),
    ("SM-1", "Donne-moi une vue d'ensemble de mon portefeuille."),
]


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Demo du PoC en seance (offline deterministe ou live via LibreChat).")
    parser.add_argument("--mode", choices=["offline", "live"], default=os.environ.get("DEMO_MODE", "offline"))
    parser.add_argument("--today", default=os.environ.get("DEMO_TODAY", ""))
    parser.add_argument("--bundle", default=os.environ.get("OKF_BUNDLE_PATH", "okf-bundle"))
    parser.add_argument("--keywords", default=os.environ.get("KEYWORDS_PATH", "config/keywords.json"))
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else None
    coach = build_coach(bundle_path=args.bundle, keywords_path=args.keywords, mode=args.mode, today=today)

    print(f"=== Demo PoC OKF x agent coaching commercial (pole Dixit) — mode: {args.mode} ===")
    for sender, message in SCENARIO:
        print(f"\n[{sender} dans #gchat] {message}")
        reply = coach.handle_message(message, sender=sender)
        for line in reply.splitlines():
            print(f"[agent] {line}")
    print("\n=== Fin de la demo ===")


if __name__ == "__main__":
    main()
