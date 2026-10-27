"""The three AI services Kobito can ask for hints: Claude (Anthropic), Gemini
(Google) and ChatGPT (OpenAI). Standard library only -- plain HTTPS requests --
so it runs on the desktop game and on the small proxy server
(server/kobito_ai_proxy.py) alike, with no SDKs to install.

    ANTHROPIC_API_KEY                  Claude      (model: KOBITO_CLAUDE_MODEL,  default claude-haiku-5-5)
    GEMINI_API_KEY / GOOGLE_API_KEY    Gemini      (model: KOBITO_GEMINI_MODEL,  default gemini-2.5-flash)
    OPENAI_API_KEY                     ChatGPT     (model: KOBITO_OPENAI_MODEL,  default gpt-4o-mini)
    KOBITO_AI_PROVIDER=claude|gemini|chatgpt     which one to try first

Every function here is safe to call: a missing key, a network error, a
refusal or a blocked answer is just None, and the game falls back to its
built-in hints.
"""

import json
import os

TIMEOUT = 8.0

PROVIDERS = {
    "claude": {
        "label": "CLAUDE", "keys": ("ANTHROPIC_API_KEY",), "model_env": "KOBITO_CLAUDE_MODEL",
        "model": "claude-haiku-5-5", "base": "https://api.anthropic.com",
    },
    "gemini": {
        "label": "GEMINI", "keys": ("GEMINI_API_KEY", "GOOGLE_API_KEY"), "model_env": "KOBITO_GEMINI_MODEL",
        "model": "gemini-2.5-flash", "base": "https://generativelanguage.googleapis.com",
    },
    "chatgpt": {
        "label": "CHATGPT", "keys": ("OPENAI_API_KEY",), "model_env": "KOBITO_OPENAI_MODEL",
        "model": "gpt-4o-mini", "base": "https://api.openai.com",
    },
}
ORDER = ("claude", "gemini", "chatgpt")
ALIASES = {"anthropic": "claude", "google": "gemini", "openai": "chatgpt", "gpt": "chatgpt"}


def normalize(name):
    name = (name or "").strip().lower()
    name = ALIASES.get(name, name)
    return name if name in PROVIDERS else ""


def api_key(name, environ=None):
    environ = os.environ if environ is None else environ
    for var in PROVIDERS[name]["keys"]:
        if environ.get(var, "").strip():
            return environ[var].strip()
    return ""


def configured(environ=None, prefer=""):
    """The providers that have a key, the preferred one (KOBITO_AI_PROVIDER or
    `prefer`) first, then Claude, Gemini, ChatGPT."""
    environ = os.environ if environ is None else environ
    first = normalize(prefer or environ.get("KOBITO_AI_PROVIDER", ""))
    names = ([first] if first else []) + [n for n in ORDER if n != first]
    return [n for n in names if api_key(n, environ)]


def model_for(name, environ=None):
    environ = os.environ if environ is None else environ
    spec = PROVIDERS[name]
    return environ.get(spec["model_env"], "").strip() or spec["model"]


def base_url(name, environ=None):
    environ = os.environ if environ is None else environ
    return environ.get(f"KOBITO_{name.upper()}_URL", "").strip().rstrip("/") or PROVIDERS[name]["base"]


# -- One request per service ---------------------------------------------------------

def build_request(name, key, model, prompt, max_tokens, base=None):
    """(url, headers, body dict) for one short question to `name`."""
    base = base or PROVIDERS[name]["base"]
    if name == "claude":
        return (f"{base}/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]})
    if name == "gemini":
        config = {"maxOutputTokens": max_tokens}
        if model.startswith("gemini-2.5-flash"):
            config["thinkingConfig"] = {"thinkingBudget": 0}      # a hint doesn't need to think first
        return (f"{base}/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": key, "content-type": "application/json"},
                {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config})
    if name == "chatgpt":
        return (f"{base}/v1/chat/completions",
                {"authorization": f"Bearer {key}", "content-type": "application/json"},
                {"model": model, "max_completion_tokens": max_tokens,
                 "messages": [{"role": "user", "content": prompt}]})
    raise ValueError(name)


def parse_response(name, data):
    """The answer text from a service's reply, or None (refused, blocked, empty)."""
    try:
        if name == "claude":
            if data.get("stop_reason") == "refusal":
                return None
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        elif name == "gemini":
            if data.get("promptFeedback", {}).get("blockReason"):
                return None
            candidate = data["candidates"][0]
            if candidate.get("finishReason") in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT"):
                return None
            text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
        elif name == "chatgpt":
            message = data["choices"][0]["message"]
            if message.get("refusal"):
                return None
            text = message.get("content") or ""
        else:
            return None
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    return text.strip() or None


def post_json(url, headers, body, timeout=TIMEOUT):
    import urllib.request   # only here: the browser build never gets this far
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url, timeout=TIMEOUT):
    import urllib.request
    with urllib.request.urlopen(urllib.request.Request(url, headers={"accept": "application/json"}), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def complete(name, prompt, max_tokens=1024, environ=None, timeout=TIMEOUT, post=post_json):
    """Asks `name` and returns its answer text, or None for any reason at all."""
    name = normalize(name)
    if not name:
        return None
    key = api_key(name, environ)
    if not key:
        return None
    try:
        url, headers, body = build_request(name, key, model_for(name, environ), prompt, max_tokens,
                                           base_url(name, environ))
        return parse_response(name, post(url, headers, body, timeout))
    except Exception:
        return None


def _reason(error):
    """A short, readable reason for a failed request (the service's own message when it sent one)."""
    import json as _json
    import urllib.error
    if isinstance(error, urllib.error.HTTPError):
        try:
            body = _json.loads(error.read().decode("utf-8", "replace"))
            detail = body.get("error", body)
            detail = detail.get("message", detail) if isinstance(detail, dict) else detail
        except Exception:
            detail = error.reason
        hints = {401: " (the key is wrong or revoked)", 403: " (the key isn't allowed to do this)",
                 404: " (the model name isn't available to this key -- set KOBITO_*_MODEL)", 429: " (out of quota or rate limited)"}
        return f"HTTP {error.code}: {str(detail)[:160]}{hints.get(error.code, '')}"
    return f"{type(error).__name__}: {str(error)[:160]}"


def diagnose(name, environ=None, timeout=TIMEOUT, post=post_json):
    """(ok, message): one tiny real request to `name`, with the reason when it fails."""
    name = normalize(name)
    if not name:
        return False, "unknown service"
    key = api_key(name, environ)
    if not key:
        return False, "no key set"
    try:
        url, headers, body = build_request(name, key, model_for(name, environ), "Reply with one word: ok", 32,
                                           base_url(name, environ))
        text = parse_response(name, post(url, headers, body, timeout))
    except Exception as error:
        return False, _reason(error)
    return (True, f"ok ({model_for(name, environ)})") if text else (False, "answered with nothing (blocked or empty)")


def complete_any(prompt, max_tokens=1024, environ=None, prefer="", timeout=TIMEOUT, post=post_json):
    """(text, provider) from the first configured service that answers, else (None, None)."""
    for name in configured(environ, prefer):
        text = complete(name, prompt, max_tokens, environ, timeout, post)
        if text:
            return text, name
    return None, None
