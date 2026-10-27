"""Is Kobito's AI actually working?  Run this and it tells you, step by step.

    python tools/check_ai.py                       # uses KOBITO_AI_URL, assets/ai.json, or your own keys
    python tools/check_ai.py https://your-proxy    # check a proxy (Render, Cloudflare, ...)

With a proxy address it checks: the proxy is up, which services have keys and whether each key and
model really works, that browsers on your sites are allowed (CORS), and a real hint comes back.
Without one, it tries the keys in your environment (ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY).
Exits 0 when a hint was written by an AI, 1 otherwise.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kobito import ai_providers  # noqa: E402

SAMPLE = ("A student learning Japanese just answered a quiz question wrong. Question: 学校___行きます (which particle?). "
          "Correct answer: に. Give ONE short hint (at most 2 sentences) without saying the answer.")
SITES = ("https://bonimit.github.io", "https://bonimit.itch.io")


def say(ok, text):
    print(("  ✓ " if ok else "  ✗ ") + text)
    return ok


def request(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.status, dict(response.headers), json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read() or b"{}")
        except ValueError:
            body = {}
        return error.code, dict(error.headers), body


def check_proxy(url):
    url = url.rstrip("/")
    print(f"Checking the AI proxy at {url}")
    try:
        status, _, info = request(url + "/health?probe=1")
    except Exception as error:
        return say(False, f"can't reach it: {error}. Is it running, and is the address right (https://...)?")
    if not say(status == 200, f"the proxy answers /health (HTTP {status})"):
        return False
    working = False
    if info.get("mock"):
        say(True, "mock mode (AI_MOCK=1): canned answers, no real AI")
    for name, result in (info.get("probe") or {}).items():
        working |= say(result["ok"], f"{ai_providers.PROVIDERS[name]['label']}: {result['message']}")
    if not info.get("providers") and not info.get("mock"):
        say(False, "no API key is set on the proxy (set ANTHROPIC_API_KEY, GEMINI_API_KEY or OPENAI_API_KEY there)")
    for site in SITES:
        status, headers, _ = request(url + "/v1/complete", method="OPTIONS", headers={"Origin": site})
        allowed = headers.get("Access-Control-Allow-Origin", "")
        say(allowed in ("*", site), f"browsers on {site} {'may' if allowed in ('*', site) else 'may NOT'} call it "
                                    f"(AI_ALLOWED_ORIGINS)")
    status, _, reply = request(url + "/v1/complete", {"prompt": SAMPLE, "max_tokens": 200})
    if not (say(status == 200 and reply.get("text"), f"a real hint comes back (HTTP {status}, via {reply.get('provider')})")):
        return False
    print(f'\n  The AI said: "{reply["text"]}"')
    return True


def check_keys():
    print("Checking the API keys in this environment")
    found = ai_providers.configured()
    if not found:
        say(False, "no key set: export ANTHROPIC_API_KEY, GEMINI_API_KEY and/or OPENAI_API_KEY")
        return False
    working = False
    for name in found:
        ok, message = ai_providers.diagnose(name)
        working |= say(ok, f"{ai_providers.PROVIDERS[name]['label']}: {message}")
    if not working:
        return False
    text, who = ai_providers.complete_any(SAMPLE, 200)
    if not say(bool(text), f"a real hint comes back (via {who})"):
        return False
    print(f'\n  The AI said: "{text}"')
    return True


def main():
    url = (sys.argv[1] if len(sys.argv) > 1 else "") or os.environ.get("KOBITO_AI_URL", "").strip()
    if not url:
        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "ai.json")) as f:
                url = json.load(f).get("proxy", "")
        except (OSError, ValueError):
            url = ""
    ok = check_proxy(url) if url else check_keys()
    print("\n" + ("AI hints will work." if ok else "AI hints will NOT work yet -- the game falls back to its built-in hints."))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
