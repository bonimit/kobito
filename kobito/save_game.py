"""Saving and loading a run.

One save slot, stored as a small JSON document:

    {
      "version": 1,
      "saved_at": "2026-10-16 14:32",
      "run": {                      # who you are and how far you've got
        "character_id", "companion_id", "theme_id",
        "jlpt_level", "level_number", "score", "xp",
        "item_box": {item_id: count}, "badges": [badge_id, ...],
        "difficulty_mode": "choose" | "adaptive" | "random",
        "tutor": {...} or null       # the AI tutor's learner model (adaptive mode)
      },
      "level": {...} or null,       # mid-level spot (see Game.snapshot)
      "settings": {"furigana": bool, "translation": bool, "music": bool, "sfx": bool},
      "profile": {...}              # ability level, yen, costumes (kobito/profile.py)
    }

"level" is null for a checkpoint at the start of a level (the autosave
made when a stage is cleared) and filled in when the player saves from the
settings menu or closes the window mid-level -- Continue then drops them
back exactly where they were.

Where it lives:
  * desktop -- a JSON file in the usual per-user data folder
    (%APPDATA%/Kobito, ~/Library/Application Support/Kobito, or
    ~/.local/share/kobito), or KOBITO_SAVE_PATH if set;
  * web (Pygbag) -- the browser's localStorage, since files written there
    vanish when the tab closes.

A missing, unreadable or out-of-date save is treated as "no save" -- a
broken file must never stop the game from starting.

Players: several people can share one computer (or browser). Each player
account (kobito/account_screen.py) has its own save document like the one
above -- players/<id>.json next to save.json, or localStorage key
"kobito.player.<id>" on the web -- and accounts.json / "kobito.accounts"
lists them: name, an optional PIN (stored salted and hashed), the mascot
for their portrait and when they last played. Until an account is chosen
(and for Guest play) the game uses save.json itself, exactly as before;
the first account created takes over whatever progress is in it.
"""

import hashlib
import json
import os
import secrets
import sys
import time
from pathlib import Path

from kobito import furigana
from kobito.constants import IS_WEB

SAVE_VERSION = 1
WEB_STORAGE_KEY = "kobito.save"
WEB_ACCOUNTS_KEY = "kobito.accounts"
WEB_PLAYER_PREFIX = "kobito.player."
MAX_NAME_LENGTH = 10

_current = {"id": None}   # the signed-in account's id; None = save.json (guest)


def save_path():
    override = os.environ.get("KOBITO_SAVE_PATH")
    if override:
        return Path(override)
    home = Path.home()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming") / "Kobito"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "Kobito"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share") / "kobito"
    return base / "save.json"


# -- Raw storage ----------------------------------------------------------------

def _location(account_id="current"):
    """(web localStorage key, desktop path) of a save document: the given
    account's, the signed-in one's ("current"), or save.json (None)."""
    if account_id == "current":
        account_id = _current["id"]
    if account_id is None:
        return WEB_STORAGE_KEY, save_path()
    return WEB_PLAYER_PREFIX + account_id, save_path().parent / "players" / f"{account_id}.json"


def _read_raw(location=None):
    key, path = location or _location()
    try:
        if IS_WEB:
            import platform  # Pygbag exposes the browser's `window` here
            return platform.window.localStorage.getItem(key)
        return path.read_text(encoding="utf-8") if path.exists() else None
    except Exception:
        return None


def _write_raw(text, location=None):
    key, path = location or _location()
    try:
        if IS_WEB:
            import platform
            platform.window.localStorage.setItem(key, text)
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write next to it and swap in, so a crash mid-write can't leave a
        # half-written (corrupt) save behind.
        tmp = path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def _read_doc(location=None):
    raw = _read_raw(location)
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("version") != SAVE_VERSION:
        return {}
    return doc


def _write_doc(doc, location=None):
    doc["version"] = SAVE_VERSION
    return _write_raw(json.dumps(doc, ensure_ascii=False), location)


# -- Player accounts -------------------------------------------------------------

def _accounts_location():
    return WEB_ACCOUNTS_KEY, save_path().parent / "accounts.json"


def list_accounts():
    """Every player on this device, most recently played first."""
    raw = _read_raw(_accounts_location())
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        data = {}
    accounts = [a for a in data.get("accounts", []) if isinstance(a, dict) and a.get("id") and a.get("name")]
    return sorted(accounts, key=lambda a: a.get("last_played", ""), reverse=True)


def _write_accounts(accounts):
    return _write_raw(json.dumps({"version": SAVE_VERSION, "accounts": accounts}, ensure_ascii=False),
                      _accounts_location())


def _hash_pin(pin, salt):
    return hashlib.sha256(f"{salt}:{pin}".encode("utf-8")).hexdigest()


def clean_name(name):
    name = " ".join(str(name).split())[:MAX_NAME_LENGTH]
    return "".join(ch for ch in name if ch.isprintable())


def create_account(name, pin=None, character_id=None):
    """Adds a player and returns their account. The very first account
    takes over the progress already in save.json, so nobody loses theirs
    when accounts arrive."""
    name = clean_name(name)
    if not name:
        raise ValueError("a name is needed")
    accounts = list_accounts()
    if any(a["name"].lower() == name.lower() for a in accounts):
        raise ValueError("that name is taken")
    account = {"id": secrets.token_hex(6), "name": name, "created": time.strftime("%Y-%m-%d"),
               "last_played": time.strftime("%Y-%m-%d %H:%M:%S"), "character_id": character_id}
    if pin:
        account["salt"] = secrets.token_hex(8)
        account["pin"] = _hash_pin(pin, account["salt"])
    if not accounts:
        legacy = _read_doc(_location(None))
        if legacy.get("run") or legacy.get("profile"):
            _write_doc(dict(legacy), _location(account["id"]))
            run = legacy.get("run") or {}
            account["character_id"] = account["character_id"] or run.get("character_id")
    accounts.append(account)
    _write_accounts(accounts)
    return account


def has_pin(account):
    return bool(account.get("pin"))


def check_pin(account, pin):
    return not has_pin(account) or _hash_pin(pin, account.get("salt", "")) == account["pin"]


def sign_in(account):
    """Makes `account` (or None: guest) the one every load/save uses."""
    _current["id"] = account["id"] if account else None
    if account:
        touch_account(last_played=time.strftime("%Y-%m-%d %H:%M:%S"))


def current_account():
    return next((a for a in list_accounts() if a["id"] == _current["id"]), None)


def touch_account(**fields):
    """Updates the signed-in account's listing (portrait, last played, ...)."""
    if _current["id"] is None:
        return
    accounts = list_accounts()
    for account in accounts:
        if account["id"] == _current["id"]:
            account.update(fields)
    _write_accounts(accounts)


def delete_account(account_id):
    accounts = [a for a in list_accounts() if a["id"] != account_id]
    _write_accounts(accounts)
    key, path = _location(account_id)
    try:
        if IS_WEB:
            import platform
            platform.window.localStorage.removeItem(key)
        elif path.exists():
            path.unlink()
    except Exception:
        pass
    if _current["id"] == account_id:
        _current["id"] = None


def load_profile_of(account_id):
    """Another player's profile (for the leaderboard)."""
    from kobito.profile import Profile
    return Profile.from_dict(_read_doc(_location(account_id)).get("profile"))


# -- Run ------------------------------------------------------------------------

def load_run():
    """The saved run as {"run": {...}, "level": {...} or None, "saved_at": str},
    or None if there's nothing (valid) to continue."""
    from kobito.characters import CHARACTERS
    from kobito.companions import COMPANIONS
    from kobito.difficulty import JLPT_DESCRIPTIONS
    from kobito.themes import THEMES

    doc = _read_doc()
    run = doc.get("run")
    if not isinstance(run, dict):
        return None
    try:
        valid = (
            run["character_id"] in {c["id"] for c in CHARACTERS}
            and run["companion_id"] in {c["id"] for c in COMPANIONS}
            and run["theme_id"] in THEMES
            and run["jlpt_level"] in JLPT_DESCRIPTIONS
            and int(run["level_number"]) >= 1
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        return None

    from kobito.items import ITEMS
    run = dict(run)
    run["level_number"] = int(run["level_number"])
    run["score"] = max(0, int(run.get("score", 0)))
    run["xp"] = max(0, int(run.get("xp", 0)))
    box = run.get("item_box") if isinstance(run.get("item_box"), dict) else {}
    run["item_box"] = {k: int(v) for k, v in box.items() if k in ITEMS and int(v) > 0}
    run["badges"] = [b for b in run.get("badges", []) if isinstance(b, str)]
    history = run.get("question_history") if isinstance(run.get("question_history"), list) else []
    run["question_history"] = [q for q in history if isinstance(q, str)]
    from kobito.difficulty import MODE_CHOOSE, MODES
    if run.get("difficulty_mode") not in MODES:
        run["difficulty_mode"] = MODE_CHOOSE
    if not isinstance(run.get("tutor"), dict):
        run["tutor"] = None
    level = doc.get("level") if isinstance(doc.get("level"), dict) else None
    return {"run": run, "level": level, "saved_at": doc.get("saved_at", "")}


def save_run(run, level=None, profile=None):
    """Writes the run (and optionally a mid-level spot and the profile).
    Returns True on success. Settings already in the save are kept."""
    doc = _read_doc()
    doc["run"] = run
    doc["level"] = level
    if profile is not None:
        doc["profile"] = profile.to_dict()
    doc["saved_at"] = time.strftime("%Y-%m-%d %H:%M")
    doc.setdefault("settings", current_settings())
    return _write_doc(doc)


# -- Profile --------------------------------------------------------------------

def load_profile():
    """The player's ability level, 円, wardrobe and trophies (kept across runs)."""
    from kobito.profile import Profile
    profile = Profile.from_dict(_read_doc().get("profile"))
    profile.seed = _current["id"] or "guest"   # whose daily missions these are
    return profile


def save_profile(profile):
    doc = _read_doc()
    doc["profile"] = profile.to_dict()
    doc.setdefault("settings", current_settings())
    return _write_doc(doc)


def clear_run():
    doc = _read_doc()
    doc.pop("run", None)
    doc.pop("level", None)
    return _write_doc(doc)


# -- Settings -------------------------------------------------------------------

def current_settings():
    from kobito import audio
    return {"furigana": furigana.is_enabled(), "translation": furigana.is_translation_visible(),
            "music": audio.music_enabled(), "sfx": audio.sfx_enabled()}


def save_settings():
    doc = _read_doc()
    doc["settings"] = current_settings()
    return _write_doc(doc)


def apply_saved_settings():
    """Restores the furigana / translation / sound toggles from the last session."""
    from kobito import audio
    settings = _read_doc().get("settings")
    if not isinstance(settings, dict):
        return
    if "music" in settings:
        audio.set_music(bool(settings["music"]))
    if "sfx" in settings:
        audio.set_sfx(bool(settings["sfx"]))
    if "furigana" in settings and bool(settings["furigana"]) != furigana.is_enabled():
        furigana.toggle()
    if "translation" in settings and bool(settings["translation"]) != furigana.is_translation_visible():
        furigana.toggle_translation()
