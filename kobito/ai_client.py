"""How the game reaches an AI: one place that decides, and never blocks the quiz.

  * A Kobito AI proxy (server/kobito_ai_proxy.py) -- the way to give AI hints
    to the web build, and to players without their own key. Its address is
    KOBITO_AI_URL on the desktop, or "proxy" in assets/ai.json (the web
    workflow writes that file from the AI_PROXY_URL repository variable).
  * Or, on the desktop, the player's own keys: ANTHROPIC_API_KEY (Claude),
    GEMINI_API_KEY (Gemini), OPENAI_API_KEY (ChatGPT) -- see ai_providers.py.

start(prompt) returns an AIRequest at once and the answer arrives later --
from a thread on the desktop, from an asyncio task in the browser (where
there are no threads and no sockets, only JavaScript's fetch). Callers poll
`request.done` / `request.text` each frame. If nothing is configured,
default_client() is None and the game uses its built-in hints.
"""

import asyncio
import json
import os
import sys
import threading
import time

from kobito import ai_providers
from kobito.assets import ASSETS_DIR
from kobito.constants import IS_WEB

CONFIG_FILE = ASSETS_DIR / "ai.json"
MAX_TOKENS = 1024
PROXY_TIMEOUT = 9.0


class AIRequest:
    """One question in flight. `done` flips to True when the answer (or a
    failure: text stays None) is in."""

    def __init__(self):
        self.done = False
        self.text = None
        self.provider = None

    def finish(self, text, provider=None):
        self.text = (text or "").strip() or None
        self.provider = provider if self.text else None
        self.done = True

    def wait(self, timeout=PROXY_TIMEOUT + 2):
        """Desktop only: blocks until it's done. Returns the text (or None)."""
        end = time.time() + timeout
        while not self.done and time.time() < end:
            time.sleep(0.01)
        return self.text


def proxy_url(environ=None):
    environ = os.environ if environ is None else environ
    url = "" if IS_WEB else environ.get("KOBITO_AI_URL", "").strip()
    if not url:
        try:
            url = str(json.loads(CONFIG_FILE.read_text(encoding="utf-8")).get("proxy", "")).strip()
        except (OSError, ValueError, AttributeError):
            url = ""
    return url.rstrip("/")


class AIClient:
    def __init__(self, proxy="", providers=(), environ=None, web=IS_WEB, web_post=None, web_get=None):
        self.proxy = proxy
        self.providers = list(providers)
        self.environ = environ
        self.web = web
        self._web_post = web_post or _fetch_post
        self._web_get = web_get or _fetch_get
        self.status = "unknown"      # check() moves it to "checking", then "ok" or "down"
        self.problem = ""            # why it's down, in words

    @property
    def label(self):
        """What the companion screen shows: the service, or ONLINE for a proxy."""
        if self.proxy:
            return "ONLINE"
        return ai_providers.PROVIDERS[self.providers[0]]["label"] if self.providers else ""

    def start(self, prompt, max_tokens=MAX_TOKENS):
        request = AIRequest()
        if self.web:
            if not self.proxy:
                request.finish(None)
                return request
            try:
                asyncio.ensure_future(self._ask_web(request, prompt, max_tokens))
            except Exception:
                request.finish(None)
            return request

        def work():
            try:
                text, provider = self._ask_blocking(prompt, max_tokens)
            except Exception:
                text, provider = None, None
            request.finish(text, provider)

        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            request.finish(None)
        return request

    # -- Is it actually working? ---------------------------------------------------

    def check(self):
        """Finds out in the background whether the AI is reachable and working, so the game tells
        the truth (status: "checking" -> "ok" or "down"; `problem` says why). The proxy is only
        asked for its /health -- no AI tokens are spent; direct keys get one tiny request."""
        if self.status == "checking":
            return
        self.status, self.problem = "checking", ""
        if self.web:
            try:
                asyncio.ensure_future(self._check_web())
            except Exception:
                self.status = "down"
            return

        def work():
            try:
                if self.proxy:
                    info = ai_providers.get_json(self.proxy + "/health", PROXY_TIMEOUT)
                    ok = bool(info.get("ok")) and bool(info.get("providers") or info.get("mock"))
                    self.problem = "" if ok else "the proxy has no API key set"
                else:
                    ok, reasons = False, []
                    for name in self.providers:
                        good, message = ai_providers.diagnose(name, self.environ)
                        if good:
                            ok = True
                            break
                        reasons.append(f"{ai_providers.PROVIDERS[name]['label']}: {message}")
                    self.problem = "" if ok else "; ".join(reasons) or "no key works"
            except Exception as error:
                ok, self.problem = False, ai_providers._reason(error)
            self.status = "ok" if ok else "down"
            if not ok:
                print(f"[Kobito AI] not working: {self.problem}  (run: python tools/check_ai.py)", file=sys.stderr)

        try:
            threading.Thread(target=work, daemon=True).start()
        except Exception:
            self.status = "down"

    async def _check_web(self):
        try:
            info = json.loads(await asyncio.wait_for(self._web_get(self.proxy + "/health"), PROXY_TIMEOUT))
            ok = bool(info.get("ok")) and bool(info.get("providers") or info.get("mock"))
            self.problem = "" if ok else "the proxy has no API key set"
            self.status = "ok" if ok else "down"
        except BaseException as error:
            self.problem, self.status = type(error).__name__, "down"
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise

    # -- The desktop: a thread, urllib ---------------------------------------------

    def _ask_blocking(self, prompt, max_tokens):
        if self.proxy:
            reply = ai_providers.post_json(self.proxy + "/v1/complete", {"content-type": "application/json"},
                                           {"prompt": prompt, "max_tokens": max_tokens}, PROXY_TIMEOUT)
            return reply.get("text"), reply.get("provider")
        return ai_providers.complete_any(prompt, max_tokens, self.environ)

    # -- The browser: asyncio + JavaScript fetch -----------------------------------

    async def _ask_web(self, request, prompt, max_tokens):
        try:
            raw = await asyncio.wait_for(
                self._web_post(self.proxy + "/v1/complete", {"prompt": prompt, "max_tokens": max_tokens}),
                PROXY_TIMEOUT)
            reply = json.loads(raw)
            request.finish(reply.get("text"), reply.get("provider"))
        except BaseException as error:          # a timeout, a CORS error, bad JSON ... -> built-in hints
            request.finish(None)
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise


async def _fetch_post(url, data):
    """POST JSON with the browser's fetch (Pygbag's aio.fetch). Raises if it isn't there."""
    from aio.fetch import RequestHandler
    handler = RequestHandler()
    handler.debug = False
    return await handler.post(url, data)


async def _fetch_get(url):
    """GET with the browser's fetch (Pygbag's aio.fetch)."""
    from aio.fetch import RequestHandler
    handler = RequestHandler()
    handler.debug = False
    return await handler.get(url)


def default_client(environ=None, web=IS_WEB):
    """The AIClient this player can use, or None (built-in hints)."""
    proxy = proxy_url(environ)
    providers = [] if (web or proxy) else ai_providers.configured(environ)
    if not proxy and not providers:
        return None
    return AIClient(proxy=proxy, providers=providers, environ=environ, web=web)
