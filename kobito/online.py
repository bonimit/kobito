"""The world leaderboard: talks to a Kobito server (server/kobito_server.py)
when one is configured -- KOBITO_SERVER=http://host:port -- and stays out
of the way otherwise.

Everything runs on a background thread, so a slow or missing server never
stalls the game: submit() sends this player's leaderboard entry (making
them an online id + secret token the first time, kept in their account
listing), refresh() fetches a board, and rows() returns the last one
fetched along with a status line for the screen.

Desktop only for now: the web build can't open sockets from Python, so
there it simply reports that online boards aren't available.
"""

import json
import os
import threading
import urllib.request

from kobito.constants import IS_WEB

TIMEOUT = 4.0
_state = {"boards": {}, "status": {}}


def server():
    return os.environ.get("KOBITO_SERVER", "").strip().rstrip("/")


def enabled():
    return bool(server()) and not IS_WEB


def _request(method, path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(server() + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _background(fn):
    thread = threading.Thread(target=fn, daemon=True)
    thread.start()
    return thread


def submit(account, profile, character_id=None):
    """Sends the player's entry for every board. Returns the thread (tests
    join it), or None when there's nothing to do."""
    if not enabled() or not account:
        return None
    from kobito import progress, save_game

    def work():
        try:
            token = account.get("online_token")
            if not token:
                reply = _request("POST", "/api/register", {"name": account["name"]})
                token = reply["token"]
                account["online_id"], account["online_token"] = reply["id"], token
                save_game.touch_account(online_id=reply["id"], online_token=token)
            entry = {board: [int(value), label] for board, (value, label) in progress.board_entry(profile).items()}
            _request("POST", "/api/scores", {"token": token, "character_id": character_id or "", "entry": entry})
        except Exception:
            pass   # offline, server down, ... -- try again next time

    return _background(work)


def refresh(board, limit=20):
    """Fetches a board in the background; rows() has it when it arrives."""
    if not enabled():
        return None
    _state["status"][board] = "loading"

    def work():
        try:
            reply = _request("GET", f"/api/leaderboard?board={board}&limit={limit}")
            _state["boards"][board] = reply.get("rows", [])
            _state["status"][board] = "ok"
        except Exception:
            _state["status"][board] = "error"

    return _background(work)


def rows(board):
    """(rows or None, status): status is "off", "loading", "ok" or "error"."""
    if not enabled():
        return None, "off"
    return _state["boards"].get(board), _state["status"].get(board, "loading")
