"""
Cookie store — save and load cookies per platform/account.

Storage: ~/.socialcli/accounts/<platform>/<account>.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

DATA_DIR = Path.home() / ".socialcli"
ACCOUNTS_DIR = DATA_DIR / "accounts"


def _account_path(platform: str, account: str = "default") -> Path:
    return ACCOUNTS_DIR / platform / f"{account}.json"


def save_cookies(platform: str, cookies: list[dict], account: str = "default",
                 nickname: str = "", user_id: str = "") -> None:
    """Save cookies and account info to disk."""
    path = _account_path(platform, account)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "platform": platform,
        "account": account,
        "nickname": nickname,
        "user_id": user_id,
        "cookies": cookies,
        "login_time": _now(),
        "status": "active",
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def load_cookies(platform: str, account: str = "default") -> Optional[list[dict]]:
    """Load cookies from disk. Returns None if not found."""
    path = _account_path(platform, account)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("cookies", [])
    except (json.JSONDecodeError, KeyError):
        return None


def load_account_info(platform: str, account: str = "default") -> Optional[dict]:
    """Load full account info."""
    path = _account_path(platform, account)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, KeyError):
        return None


def list_accounts(platform: str = "") -> list[dict]:
    """List all saved accounts, optionally filtered by platform."""
    results = []
    if not ACCOUNTS_DIR.exists():
        return results

    platforms = [platform] if platform else [
        d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()
    ]

    for p in platforms:
        pdir = ACCOUNTS_DIR / p
        if not pdir.exists():
            continue
        for f in pdir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                results.append({
                    "platform": p,
                    "account": f.stem,
                    "nickname": data.get("nickname", ""),
                    "user_id": data.get("user_id", ""),
                    "login_time": data.get("login_time", ""),
                    "status": data.get("status", "unknown"),
                })
            except Exception:
                results.append({"platform": p, "account": f.stem, "status": "corrupted"})

    return results


def delete_account(platform: str, account: str = "default") -> bool:
    """Delete saved account cookies."""
    path = _account_path(platform, account)
    if path.exists():
        path.unlink()
        return True
    return False


def cookie_string(platform: str, account: str = "default") -> str:
    """Get cookies as a semicolon-separated string for HTTP headers."""
    cookies = load_cookies(platform, account)
    if not cookies:
        return ""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c and "value" in c)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
