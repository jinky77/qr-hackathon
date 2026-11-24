import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

from .coach import build_coach

CHAT_API = "https://chat.googleapis.com/v1"


def handle_event(event, coach):
    if event.get("type") != "MESSAGE":
        return None
    message = event.get("message", {})
    text = message.get("text", "")
    sender = (message.get("sender", {}) or {}).get("displayName", "inconnu")
    bot_name = (event.get("bot", {}) or {}).get("displayName", "")
    if bot_name and bot_name.lower() in text.lower():
        text = text.lower().replace(bot_name.lower(), "").strip()
    if not text.strip():
        return None
    reply = coach.handle_message(text, sender=sender)
    return {"text": reply}


class WebhookHandler(BaseHTTPRequestHandler):
    coach = None
    webhook_path = "/gchat/webhook"

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != self.webhook_path:
            self._send_json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            event = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return
        if event.get("type") == "MESSAGE" and event.get("message", {}).get("text"):
            reply = handle_event(event, self.coach)
            self._send_json(200, reply or {})
        else:
            self._send_json(200, {})

    def log_message(self, *args):
        pass


def serve(coach, port, path):
    handler = type("BoundHandler", (WebhookHandler,), {"coach": coach, "webhook_path": path})
    server = HTTPServer(("0.0.0.0", port), handler)
    print(f"Webhook GChat en ecoute sur :{port}{path} (health: /health)")
    server.serve_forever()


def poll(coach, space_id, token, interval):
    headers = {"Authorization": f"Bearer {token}"}
    seen = set()
    print(f"Polling du canal GChat {space_id} toutes les {interval}s...")
    while True:
        resp = requests.get(f"{CHAT_API}/spaces/{space_id}/messages", headers=headers, timeout=30)
        resp.raise_for_status()
        for message in resp.json().get("messages", []):
            name = message.get("name")
            if name in seen:
                continue
            seen.add(name)
            sender = (message.get("sender", {}) or {}).get("displayName", "inconnu")
            if sender == "":
                continue
            text = message.get("text", "")
            if not text.strip():
                continue
            reply = coach.handle_message(text, sender=sender)
            requests.post(
                f"{CHAT_API}/spaces/{space_id}/messages",
                headers=headers,
                json={"text": reply},
                timeout=30,
            )
        time.sleep(interval)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Pont Google Chat <-> agent coaching (LibreChat + base OKF).")
    parser.add_argument("command", choices=["serve", "poll", "simulate"])
    parser.add_argument("--port", type=int, default=int(os.environ.get("GCHAT_WEBHOOK_PORT", "8080")))
    parser.add_argument("--path", default=os.environ.get("GCHAT_WEBHOOK_PATH", "/gchat/webhook"))
    parser.add_argument("--space", default=os.environ.get("GCHAT_SPACE_ID", ""))
    parser.add_argument("--token", default=os.environ.get("GCHAT_ACCESS_TOKEN", ""))
    parser.add_argument("--interval", type=int, default=int(os.environ.get("GCHAT_POLL_INTERVAL", "15")))
    parser.add_argument("messages", nargs="*", help="messages simules (commande simulate)")
    args = parser.parse_args()

    coach = build_coach()
    if args.command == "serve":
        serve(coach, args.port, args.path)
    elif args.command == "poll":
        if not args.space or not args.token:
            raise SystemExit("GCHAT_SPACE_ID et GCHAT_ACCESS_TOKEN requis pour 'poll'")
        poll(coach, args.space, args.token, args.interval)
    else:
        for message in args.messages or ["Oú en est le dossier client-002 ?"]:
            print(f"\n> GChat: {message}")
            print(f"< Agent: {coach.handle_message(message)}")


if __name__ == "__main__":
    main()
