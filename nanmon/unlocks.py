from __future__ import annotations
import json
import os
from .constants import ASSET_HAT_DIR

_UNLOCKS_FILE = os.path.join(os.path.dirname(__file__), "unlocked_hats.json")


def is_debug_unlock_all() -> bool:
    """Debug mode flag for unlocking all hats.
    Set env NANMON_DEBUG_UNLOCK_ALL=1 (or DEBUG=1) to enable.
    """
    return os.environ.get("NANMON_DEBUG_UNLOCK_ALL") == "1" or os.environ.get("DEBUG") == "1"


def load_unlocked_hats() -> set[str]:
    try:
        with open(_UNLOCKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {str(x) for x in data}
    except Exception:
        pass
    return set()


def save_unlocked_hats(names: set[str]) -> None:
    try:
        with open(_UNLOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(names), f, ensure_ascii=False, indent=2)
    except Exception:
        # best-effort; ignore failures
        pass


def unlock_hat(name: str) -> None:
    name = os.path.basename(name)
    if not name:
        return
    s = load_unlocked_hats()
    if name not in s:
        s.add(name)
        save_unlocked_hats(s)


def list_all_hats() -> list[str]:
    try:
        return [fn for fn in os.listdir(ASSET_HAT_DIR) if fn.lower().endswith((".png", ".jpg", ".jpeg"))]
    except Exception:
        return []
