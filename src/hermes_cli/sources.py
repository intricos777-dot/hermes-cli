# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""Local truths from Polsia, Lia and the Hermes gateway.

These read the on-disk stores the CLIs already maintain, so Hermes.CLI
needs no active session — it can observe their state whenever it runs.
"""

from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path

import yaml


def _read_json(path: str | Path) -> dict | list | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_yaml(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def polsia_truth(cfg: dict) -> dict:
    paths = cfg["paths"]
    registry = _read_yaml(paths["polsia_registry"]) or {}
    active = _read_json(paths["polsia_active"]) or {}
    memory = _read_json(paths["polsia_memory"]) or {}
    pconfig = _read_yaml(paths["polsia_config"]) or {}

    agent_states: dict[str, dict] = {}
    for key, val in memory.items():
        if key.startswith("agent_state."):
            name = key.split(".", 1)[1]
            agent_states[name] = val if isinstance(val, dict) else {"note": str(val)}

    businesses = registry.get("businesses", [])
    if not isinstance(businesses, list):
        businesses = []

    return {
        "businesses": businesses,
        "active": active.get("active", ""),
        "agent_states": agent_states,
        "config": {
            "agents": pconfig.get("agents", {}),
            "business": pconfig.get("business", {}),
        },
        "registry_path": paths["polsia_registry"],
        "businesses_dir": paths["polsia_businesses"],
    }


def lia_truth(cfg: dict) -> dict:
    paths = cfg["paths"]
    plan = _read_json(paths["lia_plan"]) or {}

    projects = []
    if isinstance(plan, dict):
        for proj in plan.get("projects", []):
            if not isinstance(proj, dict):
                continue
            tasks = proj.get("tasks", [])
            done = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "completed")
            projects.append(
                {
                    "name": proj.get("name", "?"),
                    "status": proj.get("status", "unknown"),
                    "task_count": len(tasks),
                    "tasks_done": done,
                    "repo": proj.get("repo", ""),
                }
            )

    # Bridge liveness on the Lia API port.
    bridge_up, bridge_note = _probe_http(paths["lia_bridge"], timeout=2)

    history_lines = 0
    hist = Path(paths["lia_history"])
    if hist.exists():
        history_lines = sum(1 for _ in hist.open(encoding="utf-8", errors="ignore"))

    return {
        "supervisor": plan.get("supervisor", "lia-cli") if isinstance(plan, dict) else "lia-cli",
        "projects": projects,
        "bridge_up": bridge_up,
        "bridge_note": bridge_note,
        "history_entries": history_lines,
        "updated_at": plan.get("updated_at", "") if isinstance(plan, dict) else "",
    }


def hermes_truth(cfg: dict) -> dict:
    paths = cfg["paths"]
    gateway_up = False
    pid = None
    pid_file = Path(paths["hermes_gateway_pid"])
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip() or "0")
        except ValueError:
            pid = None
    if pid and _proc_exists(pid):
        gateway_up = True

    kanban = Path(paths["hermes_kanban"])
    kanban_bytes = kanban.stat().st_size if kanban.exists() else 0

    hermes_home = Path(paths["hermes_home"])
    sessions = 0
    sessions_dir = hermes_home / "sessions"
    if sessions_dir.exists():
        sessions = sum(1 for p in sessions_dir.rglob("*") if p.is_file())

    return {
        "gateway_up": gateway_up,
        "gateway_pid": pid,
        "kanban_bytes": kanban_bytes,
        "session_files": sessions,
    }


def _proc_exists(pid: int | None) -> bool:
    if not pid:
        return False
    return (Path("/proc") / str(pid)).exists()


def _probe_http(base: str, timeout: float = 2) -> tuple[bool, str]:
    if not base:
        return False, "no endpoint configured"
    url = base.rstrip("/") + "/"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return resp.status < 500, f"http {resp.status}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unreachable ({exc.__class__.__name__})"