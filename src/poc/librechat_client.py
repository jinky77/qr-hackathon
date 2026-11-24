import os

import requests


class LibreChatClient:
    def __init__(self, base_url=None, api_key=None, endpoint=None, timeout=None):
        self.base_url = (base_url or os.environ.get("LIBRECHAT_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("LIBRECHAT_API_KEY", "")
        self.endpoint = endpoint or os.environ.get("LIBRECHAT_ENDPOINT", "/api/chat")
        self.timeout = int(timeout or os.environ.get("LIBRECHAT_TIMEOUT", "60"))
        if not self.base_url:
            raise RuntimeError("LIBRECHAT_BASE_URL non configure — endpoint API LibreChat a cabler (cf. Anthony).")

    def chat(self, messages, **options):
        url = self.base_url + self.endpoint
        payload = {"messages": messages, "stream": False, **options}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_text(response.json())

    @staticmethod
    def _extract_text(data):
        candidates = [
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content"),
            (data.get("message") or {}).get("content"),
            data.get("content"),
            data.get("text"),
            data.get("response"),
        ]
        for c in candidates:
            if isinstance(c, str) and c.strip():
                return c
        raise RuntimeError(f"Format de reponse LibreChat non reconnu: {str(data)[:300]}")


def make_llm_from_env():
    client = LibreChatClient()

    def llm(messages, concepts=None):
        return client.chat(messages)

    return llm
