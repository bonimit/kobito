"""Kobito's online leaderboard server -- one small file, Python's standard
library only (http.server + sqlite3), so it runs anywhere Python does.

    python server/kobito_server.py                    # http://0.0.0.0:8787
    python server/kobito_server.py --port 9000 --db /data/kobito.db

Then point each player's game at it:

    KOBITO_SERVER=http://your-server:8787 python main.py

API (JSON in, JSON out):
    POST /api/register     {"name"}                         -> {"id", "token"}
    POST /api/scores       {"token", "character_id", "entry": {board: [value, label]}}
    GET  /api/leaderboard?board=level&limit=20              -> {"board", "rows": [{rank, name, value, label, character_id}]}
    GET  /health                                            -> {"ok": true}

Boards: level, score, correct, streak, trophies (see kobito/progress.py).
A player's token is a random secret only they hold (stored hashed here);
it's what lets them update their own scores. Scores are trusted as sent --
fine for friends and a classroom, not hardened against cheating.
"""

import argparse
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BOARDS = ("level", "score", "correct", "streak", "trophies")
MAX_BODY = 4096
MAX_NAME = 10
MAX_LABEL = 24
MAX_VALUE = 10 ** 9


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, name TEXT, token_hash TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS scores (player_id TEXT, board TEXT, value INTEGER, label TEXT,
                                                   character_id TEXT, updated REAL, PRIMARY KEY (player_id, board));
                CREATE INDEX IF NOT EXISTS scores_board ON scores (board, value DESC);
            """)
            self.db.commit()

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def register(self, name):
        player_id, token = secrets.token_hex(8), secrets.token_hex(16)
        with self.lock:
            self.db.execute("INSERT INTO players VALUES (?, ?, ?, ?)", (player_id, name, self._hash(token), time.time()))
            self.db.commit()
        return player_id, token

    def player_for(self, token):
        with self.lock:
            row = self.db.execute("SELECT id FROM players WHERE token_hash = ?", (self._hash(token),)).fetchone()
        return row[0] if row else None

    def submit(self, player_id, character_id, entry):
        with self.lock:
            for board, (value, label) in entry.items():
                self.db.execute("INSERT OR REPLACE INTO scores VALUES (?, ?, ?, ?, ?, ?)",
                                (player_id, board, value, label, character_id, time.time()))
            self.db.commit()

    def top(self, board, limit):
        with self.lock:
            rows = self.db.execute(
                "SELECT p.name, s.value, s.label, s.character_id FROM scores s JOIN players p ON p.id = s.player_id "
                "WHERE s.board = ? ORDER BY s.value DESC, s.updated ASC LIMIT ?", (board, limit)).fetchall()
        return [{"rank": i + 1, "name": n, "value": v, "label": label, "character_id": c}
                for i, (n, v, label, c) in enumerate(rows)]


def _clean_name(name):
    name = " ".join(str(name).split())[:MAX_NAME]
    return "".join(ch for ch in name if ch.isprintable())


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Kobito/1"

        def log_message(self, fmt, *args):   # quiet by default
            pass

        def _send(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return None
            try:
                data = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeDecodeError):
                return None
            return data if isinstance(data, dict) else None

        def do_OPTIONS(self):
            self._send(204, {})

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"ok": True})
            if url.path == "/api/leaderboard":
                query = parse_qs(url.query)
                board = (query.get("board") or ["level"])[0]
                if board not in BOARDS:
                    return self._send(400, {"error": "unknown board"})
                try:
                    limit = max(1, min(100, int((query.get("limit") or ["20"])[0])))
                except ValueError:
                    limit = 20
                return self._send(200, {"board": board, "rows": store.top(board, limit)})
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            data = self._body()
            if data is None:
                return self._send(400, {"error": "bad request"})
            if path == "/api/register":
                name = _clean_name(data.get("name", ""))
                if not name:
                    return self._send(400, {"error": "a name is needed"})
                player_id, token = store.register(name)
                return self._send(200, {"id": player_id, "token": token})
            if path == "/api/scores":
                player_id = store.player_for(str(data.get("token", "")))
                if not player_id:
                    return self._send(403, {"error": "unknown player"})
                entry = {}
                for board, pair in (data.get("entry") or {}).items():
                    if board in BOARDS and isinstance(pair, (list, tuple)) and len(pair) == 2:
                        value, label = pair
                        if isinstance(value, int) and 0 <= value <= MAX_VALUE:
                            entry[board] = (value, str(label)[:MAX_LABEL])
                character = str(data.get("character_id") or "")[:24]
                store.submit(player_id, character, entry)
                return self._send(200, {"ok": True, "boards": sorted(entry)})
            return self._send(404, {"error": "not found"})

    return Handler


def serve(host="0.0.0.0", port=8787, db="kobito_leaderboard.db"):
    server = ThreadingHTTPServer((host, port), make_handler(Store(db)))
    return server


def main():
    parser = argparse.ArgumentParser(description="Kobito online leaderboard server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--db", default="kobito_leaderboard.db")
    args = parser.parse_args()
    server = serve(args.host, args.port, args.db)
    print(f"Kobito leaderboard on http://{args.host}:{args.port}  (database: {args.db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
