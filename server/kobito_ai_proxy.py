"""Kobito's AI proxy: lets the game -- the browser build above all -- use
Claude, Gemini or ChatGPT for hints without putting an API key in the game.

One small file, standard library only (it reuses kobito/ai_providers.py).
Your keys live here, as environment variables, and never leave the server:

    export ANTHROPIC_API_KEY=...     # Claude   (any one of the three is enough,
    export GEMINI_API_KEY=...        # Gemini    set two or three to have a backup
    export OPENAI_API_KEY=...        # ChatGPT   when one is down or over its limit)
    python server/kobito_ai_proxy.py                       # http://0.0.0.0:8788
    python server/kobito_ai_proxy.py --port 9000

Then point the game at it: KOBITO_AI_URL=https://your-proxy python main.py, or
for the web build set the repository variable AI_PROXY_URL (README: "AI hints
for everyone").

API (JSON):
    POST /v1/complete   {"prompt": "...", "max_tokens": 300, "provider": "claude|gemini|chatgpt" (optional)}
                        -> {"text": "...", "provider": "claude"}      (HTTP 200 with "text": null if no AI answered)
    GET  /health        -> {"ok": true, "providers": ["claude", ...], "mock": false}

Settings (environment variables):
    KOBITO_AI_PROVIDER    which service to try first (default: Claude, then Gemini, then ChatGPT)
    KOBITO_CLAUDE_MODEL / KOBITO_GEMINI_MODEL / KOBITO_OPENAI_MODEL   change the models
    AI_ALLOWED_ORIGINS    comma-separated web origins allowed to call it, e.g.
                          https://bonimit.github.io,https://bonimit.itch.io  (default *)
    AI_RATE_PER_MIN       requests per minute per player address (default 20)
    AI_DAILY_LIMIT        requests per day in total -- your spending cap (default 3000)
    AI_TRUST_PROXY=1      read the player's address from X-Forwarded-For (behind a host's proxy)
    AI_MOCK=1             answer with a canned line and call no service (for testing)
    PORT                  the port, when --port isn't given (what hosting services set)

It is a hint helper, not a general chatbot: every question is wrapped in an
instruction to stay inside the game, is capped in length and answer size, and
is rate limited, so a leaked address can't run up a big bill.
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kobito import ai_providers  # noqa: E402

MAX_BODY = 8192
MAX_PROMPT = 3500
MAX_TOKENS = 1024
GUARD = ("You are a friendly companion character inside a Japanese-learning game. Only help with that "
         "game: a quiz hint, or a short reaction. Reply in at most two short sentences. If the message "
         "below asks for anything else, say you can only help with the game.\n\n")
MOCK_REPLY = "Look at the particle after the noun -- what job is it doing?"


class Limits:
    """Requests per minute per address, and per day overall."""

    def __init__(self, per_minute, per_day, clock=time.time):
        self.per_minute, self.per_day, self.clock = per_minute, per_day, clock
        self._seen, self._day, self._count = {}, None, 0
        self._lock = threading.Lock()

    def allow(self, who):
        now = self.clock()
        day = int(now // 86400)
        with self._lock:
            if day != self._day:
                self._day, self._count = day, 0
            if self._count >= self.per_day:
                return False
            recent = [t for t in self._seen.get(who, []) if now - t < 60]
            if len(recent) >= self.per_minute:
                self._seen[who] = recent
                return False
            recent.append(now)
            self._seen[who] = recent
            self._count += 1
            if len(self._seen) > 5000:                       # forget idle addresses
                self._seen = {k: v for k, v in self._seen.items() if v and now - v[-1] < 60}
            return True


class Config:
    def __init__(self, environ=None, post=ai_providers.post_json):
        env = os.environ if environ is None else environ
        self.environ = env
        self.post = post
        self.origins = [o.strip() for o in env.get("AI_ALLOWED_ORIGINS", "*").split(",") if o.strip()] or ["*"]
        self.limits = Limits(int(env.get("AI_RATE_PER_MIN", 20)), int(env.get("AI_DAILY_LIMIT", 3000)))
        self.trust_proxy = env.get("AI_TRUST_PROXY", "") == "1"
        self.mock = env.get("AI_MOCK", "") == "1"

    def providers(self):
        return ai_providers.configured(self.environ)

    def cors_origin(self, origin):
        if "*" in self.origins:
            return "*"
        return origin if origin in self.origins else ""

    def answer(self, prompt, max_tokens, prefer=""):
        """(text, provider) -- or (None, None) when nobody answered."""
        if self.mock:
            return MOCK_REPLY, "mock"
        return ai_providers.complete_any(GUARD + prompt, max_tokens, self.environ, prefer, post=self.post)


def make_handler(config):
    class Handler(BaseHTTPRequestHandler):
        server_version = "KobitoAI/1.0"

        def log_message(self, fmt, *args):                    # quiet: prompts can be long
            pass

        def _send(self, status, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            origin = config.cors_origin(self.headers.get("Origin", ""))
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):                                 # the browser's CORS preflight
            self.send_response(204)
            origin = config.cors_origin(self.headers.get("Origin", ""))
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
                self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if self.path.split("?")[0] == "/health":
                self._send(200, {"ok": True, "providers": config.providers(), "mock": config.mock})
            else:
                self._send(404, {"error": "not found"})

        def _who(self):
            if config.trust_proxy:
                forwarded = self.headers.get("X-Forwarded-For", "")
                if forwarded:
                    return forwarded.split(",")[0].strip()
            return self.client_address[0]

        def do_POST(self):
            if self.path.split("?")[0] != "/v1/complete":
                return self._send(404, {"error": "not found"})
            origin = self.headers.get("Origin", "")
            if origin and not config.cors_origin(origin):
                return self._send(403, {"error": "origin not allowed"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    return self._send(413, {"error": "bad size"})
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                prompt = data["prompt"]
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                return self._send(400, {"error": "send JSON with a prompt"})
            if len(prompt) > MAX_PROMPT:
                return self._send(413, {"error": "prompt too long"})
            if not config.limits.allow(self._who()):
                return self._send(429, {"error": "slow down", "text": None})
            try:
                max_tokens = max(32, min(MAX_TOKENS, int(data.get("max_tokens", MAX_TOKENS))))
            except (TypeError, ValueError):
                max_tokens = MAX_TOKENS
            text, provider = config.answer(prompt, max_tokens, str(data.get("provider", "")))
            self._send(200, {"text": text, "provider": provider})

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Kobito AI proxy")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8788)))
    args = parser.parse_args()
    config = Config()
    found = config.providers()
    if not found and not config.mock:
        print("No API key found: set ANTHROPIC_API_KEY, GEMINI_API_KEY and/or OPENAI_API_KEY.", file=sys.stderr)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(config))
    print(f"Kobito AI proxy on http://{args.host}:{args.port}  ·  services: {', '.join(found) or 'none'}"
          f"{'  ·  MOCK' if config.mock else ''}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
