#!/usr/bin/env python3
"""Offline backup/restore of visitor records and authentication. No network.

Stop all server/batch writers before either command. --server-stopped records
the operator's acknowledgement; it cannot detect writers in other processes.
The backup contains private records, session tokens and the authentication key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "lib"))
import taguri_state as STATE

FORMAT = "taguri-state-backup-v1"
FILES = ("auth/auth.db", "auth/auth_pepper.txt", "review/ratings.db")
SCHEMAS = {"auth/auth.db": {"users": {"user_id"}, "sessions": {"session_token", "user_id"}},
           "review/ratings.db": {"works": {"user_id", "work_key"}}}


class BackupError(Exception):
    """Failures are reported with fixed messages, without sensitive details."""


def _file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise BackupError("required regular file is missing")


def _key(path: Path) -> None:
    _file(path)
    # Limit input before reading an accidentally unrelated or malicious file.
    if path.stat().st_size > 256:
        raise BackupError("invalid authentication key")
    try:
        value = path.read_text(encoding="ascii").strip()
    except (UnicodeError, OSError):
        raise BackupError("invalid authentication key") from None
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise BackupError("invalid authentication key")


def _open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)


def _database(path: Path, relative: str) -> None:
    _file(path)
    with closing(_open_readonly(path)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise BackupError("database integrity check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BackupError("database relation check failed")
        for table, required in SCHEMAS[relative].items():
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if not required <= columns:
                raise BackupError("required database schema is missing")


def _digest(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def _sync_file(path: Path) -> None:
    path.chmod(0o600)
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _destination(path: Path, *, allow_empty: bool) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise BackupError("destination must be an absolute non-link path")
    target = path.resolve()
    catalog = (ROOT / "data").resolve()
    if target == catalog or catalog in target.parents or target in catalog.parents:
        raise BackupError("destination must be separate from catalog data")
    if target.exists():
        if not allow_empty or not target.is_dir() or any(target.iterdir()):
            raise BackupError("destination already contains data")
        if os.path.ismount(target):
            raise BackupError("use a child directory inside the mount")
    if not target.parent.is_dir():
        raise BackupError("destination parent does not exist")
    return target


def _separate(target: Path, sources: tuple[Path, ...]) -> None:
    for source in sources:
        source = source.resolve()
        if target == source or target in source.parents or source in target.parents:
            raise BackupError("source and destination must be separate")


def _publish(staging: Path, target: Path, *, allow_empty: bool) -> None:
    # Recheck immediately before publication. rename of a directory cannot
    # replace an existing nonempty directory or a regular file on POSIX.
    _destination(target, allow_empty=allow_empty)
    for subdir in (staging / "auth", staging / "review"):
        subdir.chmod(0o700)
        _sync_dir(subdir)
    _sync_dir(staging)
    staging.rename(target)
    _sync_dir(target.parent)


def backup_state(output: Path, *, server_stopped: bool = False) -> None:
    """Publish a complete snapshot to a previously nonexistent output directory."""
    if not server_stopped:
        raise BackupError("stop all writers and acknowledge server-stopped")
    target = _destination(Path(output), allow_empty=False)
    sources = (STATE.auth_path(), STATE.pepper_path(), STATE.ratings_path())
    _separate(target, tuple(path.parent for path in sources))
    _key(sources[1])
    _database(sources[0], "auth/auth.db")
    _database(sources[2], "review/ratings.db")
    staging = Path(tempfile.mkdtemp(prefix=".taguri-backup-", dir=target.parent))
    try:
        for relative, source in zip(FILES, sources):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if relative.endswith(".db"):
                with closing(_open_readonly(source)) as old:
                    with closing(sqlite3.connect(destination)) as new:
                        deadline = time.monotonic() + 30
                        def progress(status: int, remaining: int, total: int) -> None:
                            if time.monotonic() >= deadline:
                                raise BackupError("database backup timed out")
                        old.backup(new, pages=256, progress=progress, sleep=0.1)
                        new.commit()
                        # Standalone snapshots must not rely on WAL sidecars.
                        new.execute("PRAGMA journal_mode=DELETE")
                _database(destination, relative)
            else:
                shutil.copyfile(source, destination)
                _key(destination)
            _sync_file(destination)
        manifest = {"format": FORMAT, "created_at": datetime.now(timezone.utc).isoformat(),
                    "files": {relative: _digest(staging / relative) for relative in FILES}}
        path = staging / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
        _sync_file(path)
        _publish(staging, target, allow_empty=False)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _validate_snapshot(source: Path) -> dict:
    if not source.is_absolute() or source.is_symlink() or not source.is_dir():
        raise BackupError("backup directory is invalid")
    # Exactly the known files; links and unexpected WAL/sidecar data are rejected.
    expected = set(FILES) | {"manifest.json", "auth", "review"}
    entries = list(source.rglob("*"))
    if any(path.is_symlink() for path in entries) or {str(path.relative_to(source)) for path in entries} != expected:
        raise BackupError("backup contents are invalid")
    path = source / "manifest.json"
    _file(path)
    if path.stat().st_size > 64 * 1024:
        raise BackupError("backup manifest is invalid")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or set(manifest.get("files", {})) != set(FILES):
        raise BackupError("backup manifest is invalid")
    for relative in FILES:
        _file(source / relative)
        if manifest["files"][relative] != _digest(source / relative):
            raise BackupError("backup checksum check failed")
    _key(source / "auth" / "auth_pepper.txt")
    for relative in SCHEMAS:
        _database(source / relative, relative)
    return manifest["files"]


def restore_state(backup: Path, target: Path, *, server_stopped: bool = False) -> None:
    """Restore to a nonexistent or empty directory. Never overwrite live state."""
    if not server_stopped:
        raise BackupError("stop all writers and acknowledge server-stopped")
    source = Path(backup)
    destination = _destination(Path(target), allow_empty=True)
    _separate(destination, (source,))
    expected = _validate_snapshot(source)
    staging = Path(tempfile.mkdtemp(prefix=".taguri-restore-", dir=destination.parent))
    try:
        for relative in FILES:
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(source / relative, path)
            _sync_file(path)
        _key(staging / "auth" / "auth_pepper.txt")
        for relative in SCHEMAS:
            _database(staging / relative, relative)
        # Check copied bytes against the validated snapshot, including its key.
        for relative in FILES:
            if _digest(staging / relative) != expected[relative]:
                raise BackupError("restored checksum check failed")
        _publish(staging, destination, allow_empty=True)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # Default argparse echoes arbitrary CLI input, which might contain keys.
        raise BackupError("invalid command arguments")


def main(argv: list[str] | None = None) -> int:
    operation = "unknown"
    try:
        parser = _Parser(description=__doc__)
        commands = parser.add_subparsers(dest="operation", required=True, parser_class=_Parser)
        backup = commands.add_parser("backup")
        backup.add_argument("--output", type=Path, required=True)
        backup.add_argument("--server-stopped", action="store_true")
        restore = commands.add_parser("restore")
        restore.add_argument("--backup", type=Path, required=True)
        restore.add_argument("--target", type=Path, required=True)
        restore.add_argument("--server-stopped", action="store_true")
        args = parser.parse_args(argv)
        operation = args.operation
        if operation == "backup":
            backup_state(args.output, server_stopped=args.server_stopped)
        else:
            restore_state(args.backup, args.target, server_stopped=args.server_stopped)
    except Exception:
        print(json.dumps({"event": "state_snapshot", "operation": operation, "outcome": "failed"}), flush=True)
        return 1
    print(json.dumps({"event": "state_snapshot", "operation": operation, "outcome": "ok"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
