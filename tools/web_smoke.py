"""Opens the built web version (build/web) in a real headless Chromium and
reports what happens: console messages, page errors, the canvas size over
time and whether the game ever drew anything. Used by the "Web smoke test"
workflow (.github/workflows/web-test.yml) -- GitHub's runners can reach the
Pygbag CDN, which a sandbox may not.

    python tools/web_smoke.py [build/web] [seconds to watch]
"""
import functools
import http.server
import io
import sys
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = sys.argv[1] if len(sys.argv) > 1 else "build/web"
WATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 150


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


handler = functools.partial(Quiet, directory=ROOT)
server = http.server.ThreadingHTTPServer(("127.0.0.1", 8123), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()


def dump_text(page, label):
    """Everything written in the page: Pygbag prints Python's output and
    error messages in a terminal area, which is where a crash shows up."""
    texts = page.evaluate("""() => {
        const out = [document.body.innerText];
        for (const el of document.querySelectorAll('.xterm-rows, .xterm-accessibility, #terminal, pre, textarea')) {
            out.push(el.innerText || el.value || '');
        }
        try { if (window.term && window.term.buffer) {
            const b = window.term.buffer.active, lines = [];
            for (let i = 0; i < b.length; i++) lines.push(b.getLine(i).translateToString(true));
            out.push(lines.join('\\n'));
        } } catch (e) { out.push('term read failed: ' + e); }
        return out;
    }""")
    seen = set()
    print(f"----- PAGE TEXT ({label}) -----")
    for t in texts:
        t = "\n".join(line.rstrip() for line in t.splitlines() if line.strip())
        if t and t not in seen:
            seen.add(t)
            print(t[-6000:])
            print("-----")


def stats(png):
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("RGB")
    w, h = img.size
    colors = img.resize((64, 36)).getcolors(64 * 36)
    colors.sort(reverse=True)
    return f"{w}x{h} top colours {[(n, c) for n, c in colors[:4]]}  distinct~{len(colors)}"


with sync_playwright() as p:
    browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page(viewport={"width": 1100, "height": 700})
    t0 = time.time()
    page.on("console", lambda m: print(f"[{time.time() - t0:5.1f}s console.{m.type}] {m.text[:300]}", flush=True))
    page.on("pageerror", lambda e: print(f"[{time.time() - t0:5.1f}s PAGE ERROR] {str(e)[:400]}", flush=True))
    page.on("requestfailed", lambda r: print(f"[{time.time() - t0:5.1f}s REQUEST FAILED] {r.url[:150]} {r.failure}", flush=True))
    page.goto("http://127.0.0.1:8123/")
    clicked = False
    last = ""
    for step in range(WATCH // 10):
        time.sleep(10)
        size = page.evaluate("() => { const c = document.querySelector('canvas'); return c ? [c.width, c.height] : null }")
        shot = page.screenshot()
        now = stats(shot)
        print(f"[{time.time() - t0:5.1f}s] canvas={size}  screen: {now}", flush=True)
        if step == 2:
            dump_text(page, "30s")
        if step == 1 and not clicked:
            page.mouse.click(550, 350)
            clicked = True
            print("  (clicked the page)", flush=True)
        if step in (5, 12):
            page.screenshot(path=f"web_shot_{step}.png")
    page.screenshot(path="web_shot_final.png")
    final = page.evaluate("() => { const c = document.querySelector('canvas'); return c ? [c.width, c.height] : null }")
    print("RESULT:", "game is drawing (canvas resized)" if final and final[0] > 100 else "NOTHING DREW", final)
    dump_text(page, "FINAL")
    browser.close()
