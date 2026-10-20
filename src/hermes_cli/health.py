# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Copyright (c) 2026 Living Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Licensed under Living Sin Proprietary License (LSPL-1.0)
# See LICENSE file for details.
"""Runtime health: scan /proc for the businesses' living processes.

Truth is in the running kernel: if a process carries a business path or
service name in its command line, that business is alive. We also probe
declared ports for services that should be reachable.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path


class ProcessInfo(dict):
    """A snapshot of a live process: pid, started at, matched cmdline."""


def scan_processes() -> list[dict]:
    """Return [{pid, start, cmdline}] for every readable process."""
    procs = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", errors="ignore")
            if not cmdline:
                continue
            start = _proc_start(entry)
            procs.append({"pid": pid, "start": start, "cmdline": cmdline.replace("\x00", " ")})
        except (OSError, PermissionError):
            continue
    return procs


def _proc_start(proc_dir: Path) -> str:
    try:
        raw = (proc_dir / "stat").read_bytes().decode("utf-8", errors="ignore")
        # field 22 of stat is starttime in clock ticks since boot
        import os

        parts = raw.rsplit(")", 1)
        if len(parts) != 2:
            return ""
        fields = parts[1].split()
        if len(fields) < 20:
            return ""
        ticks = int(fields[19])
        clock = os.sysconf("SC_CLK_TCK")
        boot = _boot_time()
        return iso_from_epoch(boot + ticks / clock)
    except Exception:  # noqa: BLE001
        return ""


def _boot_time() -> float:
    try:
        for line in Path("/proc/stat").read_text().splitlines():
            if line.startswith("btime "):
                return float(line.split()[1])
    except Exception:  # noqa: BLE001
        pass
    return 0.0


def iso_from_epoch(epoch: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def match_business_processes(procs: list[dict], business: dict, service_rules: dict | None) -> list[dict]:
    """Which live processes belong to a business?

    Matches when the cmdline contains the business path or its name,
    OR when a configured service rule for this business matches.
    """
    name = business.get("name", "")
    path = business.get("path", "")
    hits = []
    for p in procs:
        cmd = p["cmdline"]
        if path and path in cmd:
            hits.append({**p, "via": "business-path"})
            continue
        if name and f"/{name}/" in cmd or (name and f" {name}" in cmd):
            hits.append({**p, "via": "business-name"})
            continue
        if service_rules:
            for svc_name, rule in service_rules.items():
                if rule.get("business") != name:
                    continue
                if all(m in cmd for m in rule.get("match", [])):
                    hits.append({**p, "via": f"service:{svc_name}"})
    return hits


def service_running(procs: list[dict], rule: dict) -> tuple[bool, list[dict]]:
    """Apply a service rule's match list against all processes."""
    matches = [m for m in rule.get("match", [])]
    if not matches:
        return False, []
    hits = []
    for p in procs:
        cmd = p["cmdline"]
        if all(m in cmd for m in matches):
            hits.append(p)
    return bool(hits), hits


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    if not port:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def describe_service_rules(cfg: dict) -> dict:
    """Normalize config service rules for scanning."""
    rules = cfg.get("services", {})
    return {name: rule for name, rule in rules.items() if isinstance(rule, dict)}