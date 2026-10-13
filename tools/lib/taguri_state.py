"""Shared mutable storage paths. A configured directory needs a persistent mount.

No user identifiers, secrets, request bodies or exception messages enter logs.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def state_dir() -> Path | None:
    value = os.environ.get("TAGURI_STATE_DIR", "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("TAGURI_STATE_DIR must be absolute")
    path = path.resolve()
    catalog = (ROOT / "data").resolve()
    if path == catalog or catalog in path.parents or path in catalog.parents:
        raise ValueError("TAGURI_STATE_DIR must be separate from catalog data")
    return path


def ratings_path() -> Path:
    return (state_dir() / "review" / "ratings.db") if state_dir() else ROOT / "data" / "review" / "ratings.db"


def auth_path() -> Path:
    return (state_dir() / "auth" / "auth.db") if state_dir() else ROOT / "data" / "auth" / "auth.db"


def pepper_path() -> Path:
    return (state_dir() / "auth" / "auth_pepper.txt") if state_dir() else Path.home() / ".config" / "taguri" / "auth_pepper.txt"


def exposure_path() -> Path:
    root = state_dir() or ROOT / "state"
    return Path(os.environ.get("TAGURI_EXPOSURE_DB", str(root / "recommendation_exposure.db")))


def storage_status() -> dict:
    # Configuration alone cannot prove a host volume survives redeployment.
    return {"version": "state-storage-v1", "mode": "configured" if state_dir() else "temporary",
            "persistent_mount_required": bool(state_dir())}


def event(name: str, *, outcome: str = "ok", operation: str = "", status: int | None = None) -> None:
    """Allowlisted fields only. Callers must use fixed event/operation constants."""
    allowed_events = {"storage_ready", "storage_prepare", "catalog_refresh", "server_start",
                      "server_stop", "write_result", "request_failed", "demo_seed"}
    allowed_ops = {"", "rate", "note", "visit_note", "react", "favourite", "ticket", "other"}
    if name not in allowed_events or operation not in allowed_ops or outcome not in {"ok", "failed", "temporary", "rejected"}:
        raise ValueError("invalid operational event")
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": name, "outcome": outcome}
    if operation:
        record["operation"] = operation
    if status is not None:
        record["status"] = int(status)
    try:
        print(json.dumps(record, ensure_ascii=True), flush=True)
    except OSError:
        # A broken log sink must not turn a committed user write into an error.
        pass


def _has_users(path: Path) -> bool:
    if not path.exists():
        return False
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        return bool(exists and conn.execute("SELECT 1 FROM users LIMIT 1").fetchone())


def prepare_storage() -> None:
    """Prepare before serving. Legacy migration is explicit and all-or-nothing.

    Existing destination files are never overwritten. Migration happens in a
    sibling directory, using SQLite backup so WAL transactions are included.
    Run while the old server is stopped; concurrent writers are unsupported.
    """
    try:
        target = state_dir()
        if target is None:
            event("storage_ready", outcome="temporary")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        source_auth = ROOT / "data" / "auth" / "auth.db"
        source_ratings = ROOT / "data" / "review" / "ratings.db"
        source_pepper = Path.home() / ".config" / "taguri" / "auth_pepper.txt"
        legacy = source_auth.exists() or source_ratings.exists()
        # A newly mounted volume often already has an empty mount directory.
        empty_target = target.is_dir() and not any(target.iterdir())
        if empty_target and legacy and os.environ.get("TAGURI_MIGRATE_LEGACY_STATE") != "1":
            raise RuntimeError("legacy storage requires explicit migration")
        if empty_target and legacy and os.environ.get("TAGURI_MIGRATE_LEGACY_STATE") == "1":
            # Never remove the mount itself: use a child directory as state root.
            if os.path.ismount(target):
                raise RuntimeError("use a child directory inside the persistent mount for migration")
            target.rmdir()
        if not target.exists() and legacy:
            if os.environ.get("TAGURI_MIGRATE_LEGACY_STATE") != "1":
                raise RuntimeError("legacy storage requires explicit migration")
            if _has_users(source_auth) and not source_pepper.exists():
                raise RuntimeError("legacy authentication pepper is missing")
            if source_pepper.exists() and len(bytes.fromhex(source_pepper.read_text().strip())) != 32:
                raise RuntimeError("legacy authentication pepper is invalid")
            staging = Path(tempfile.mkdtemp(prefix=".taguri-state-", dir=target.parent))
            try:
                for source, relative in ((source_auth, "auth/auth.db"), (source_ratings, "review/ratings.db")):
                    if source.exists():
                        dest = staging / relative
                        dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as old:
                            with sqlite3.connect(dest) as new:
                                old.backup(new)
                        dest.chmod(0o600)
                if source_pepper.exists():
                    dest = staging / "auth" / "auth_pepper.txt"
                    dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    shutil.copyfile(source_pepper, dest)
                    dest.chmod(0o600)
                staging.rename(target)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.chmod(0o700)
        if legacy and _has_users(source_auth) and not (target / "auth" / "auth.db").exists():
            raise RuntimeError("legacy users were not migrated")
        if source_ratings.exists() and not (target / "review" / "ratings.db").exists():
            raise RuntimeError("legacy ratings were not migrated")
        if _has_users(target / "auth" / "auth.db") and not (target / "auth" / "auth_pepper.txt").exists():
            raise RuntimeError("authentication pepper is missing; refusing to replace it")
        key = target / "auth" / "auth_pepper.txt"
        if key.exists() and len(bytes.fromhex(key.read_text().strip())) != 32:
            raise RuntimeError("authentication pepper is invalid")
        for subdir in (target / "auth", target / "review"):
            subdir.mkdir(exist_ok=True, mode=0o700)
            subdir.chmod(0o700)
        # Detect unwritable/missing mounts before accepting visitor writes.
        with tempfile.TemporaryFile(dir=target) as probe:
            probe.write(b"storage probe")
            probe.flush()
            os.fsync(probe.fileno())
        event("storage_ready")
    except Exception:
        event("storage_prepare", outcome="failed")
        raise RuntimeError("storage preparation failed; check configuration and restore intact state") from None
