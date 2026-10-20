# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""Journal, inboxes and heartbeats — the words between the worlds."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def journal_path(state: Path) -> Path:
    return state / "journal.ndjson"


def append_journal(state: Path, source: str, msg: str, to: str = "*") -> dict:
    entry = {"ts": _now(), "from": source, "to": to, "msg": msg, "id": uuid.uuid4().hex[:12]}
    with journal_path(state).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def read_journal(state: Path, limit: int = 40, source: str | None = None) -> list[dict]:
    jp = journal_path(state)
    if not jp.exists():
        return []
    entries = []
    for line in jp.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if source and entry.get("from") != source:
            continue
        entries.append(entry)
    return entries[-limit:]


# --- inbox ---

def inbox_path(state: Path, entity: str) -> Path:
    return state / "inbox" / entity / f"{entity}.ndjson"


def send_message(state: Path, to_entity: str, from_entity: str, msg: str) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": _now(),
        "from": from_entity,
        "to": to_entity,
        "msg": msg,
        "read": False,
    }
    with inbox_path(state, to_entity).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def read_inbox(state: Path, entity: str, mark_read: bool = True) -> list[dict]:
    ip = inbox_path(state, entity)
    if not ip.exists():
        return []
    lines = ip.read_text(encoding="utf-8", errors="ignore").splitlines()
    entries = []
    pending = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if mark_read and not entry.get("read"):
            entry["read"] = True
        pending.append(json.dumps(entry))
        entries.append(entry)
    if mark_read:
        ip.write_text("\n".join(pending) + "\n", encoding="utf-8")
    return entries


# --- heartbeat ---

def heartbeat_path(state: Path) -> Path:
    return state / "heartbeat.json"


def load_heartbeats(state: Path) -> dict:
    hp = heartbeat_path(state)
    if hp.exists():
        try:
            return json.loads(hp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def stamp_heartbeat(state: Path, entity: str, note: str = "") -> dict:
    beats = load_heartbeats(state)
    beats[entity] = {"last": _now(), "note": note, "source": "hermes-cli"}
    with heartbeat_path(state).open("w", encoding="utf-8") as fh:
        json.dump(beats, fh, indent=2)
    return beats[entity]


def render_heartbeats(state: Path) -> list[tuple[str, dict]]:
    beats = load_heartbeats(state)
    return sorted(beats.items())