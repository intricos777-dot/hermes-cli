# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Copyright (c) 2026 Living Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Licensed under Living Sin Proprietary License (LSPL-1.0)
# See LICENSE file for details.
"""The ledger: polsia registry + runtime health + liaison tasks → one truth.

Solve et coagula: dissolve each source's local claims, coalesce them into
a single synced view that survives anywhere via git.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from . import health, sources


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ledger_path(state: Path) -> Path:
    return state / "ledger.json"


def empty_ledger() -> dict:
    return {
        "schema": "hermes-ledger/v1",
        "updated_at": _now(),
        "active_business": "",
        "agents": {},
        "services": {},
        "gateway": {},
        "lia": {},
        "businesses": [],
    }


def load_ledger(state: Path) -> dict:
    lp = ledger_path(state)
    if lp.exists():
        try:
            return json.loads(lp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return empty_ledger()


def build_ledger(cfg: dict, state: Path) -> dict:
    ledger = load_ledger(state)
    ledger["updated_at"] = _now()

    ptruth = sources.polsia_truth(cfg)
    ltruth = sources.lia_truth(cfg)
    htruth = sources.hermes_truth(cfg)

    procs = health.scan_processes()
    service_rules = health.describe_service_rules(cfg)

    ledger["active_business"] = ptruth.get("active", "")
    ledger["agents"] = ptruth.get("agent_states", {})
    ledger["gateway"] = htruth
    ledger["lia"] = {
        "supervisor": ltruth.get("supervisor", ""),
        "bridge_up": ltruth.get("bridge_up", False),
        "bridge_note": ltruth.get("bridge_note", ""),
        "projects": ltruth.get("projects", [])[:6],
        "projects_total": len(ltruth.get("projects", [])),
    }

    # --- services health ---
    svc_status = {}
    for svc_name, rule in service_rules.items():
        running, hits = health.service_running(procs, rule)
        svc_status[svc_name] = {
            "running": running,
            "pids": [h["pid"] for h in hits],
            "business": rule.get("business", ""),
            "port": rule.get("port"),
            "port_open": health.port_open(rule["port"]) if rule.get("port") else None,
        }
    ledger["services"] = svc_status

    # --- per-business health ---
    old = {b.get("name"): b for b in ledger.get("businesses", [])}
    fresh_businesses = []
    for biz in ptruth.get("businesses", []):
        name = biz.get("name", "")
        if not name:
            continue
        biz_dir = Path(biz.get("path", ""))
        exists = biz_dir.exists()
        running_procs = health.match_business_processes(procs, biz, None)
        svc_hits = [
            s
            for s, info in svc_status.items()
            if info.get("business") == name and info.get("running")
        ]

        prev = old.get(name, {})
        last_healthy = prev.get("last_healthy", "")
        if running_procs or svc_hits:
            if not last_healthy:
                last_healthy = _now()
            status = "running"
        elif exists:
            status = "monitoring"
        else:
            status = "missing"

        fresh_businesses.append(
            {
                "name": name,
                "category": biz.get("category", ""),
                "language": biz.get("language", ""),
                "path": biz.get("path", ""),
                "entrypoints": biz.get("entrypoints", []),
                "exists": exists,
                "status": status,
                "running_procs": [{"pid": p["pid"], "via": p.get("via", "")} for p in running_procs[:5]],
                "services": svc_hits,
                "last_checked": _now(),
                "last_healthy": last_healthy,
                "notes": prev.get("notes", [])[-20:],
            }
        )
    ledger["businesses"] = fresh_businesses

    with ledger_path(state).open("w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2)
    return ledger


def render_ledger(ledger: dict) -> str:
    lines = []
    lines.append(f"Ledger v{ledger.get('schema', '?').split('/')[-1]} — updated {ledger.get('updated_at', '?')}")
    active = ledger.get("active_business", "")
    if active:
        lines.append(f"Active business: {active}")
    lines.append("")

    svc = ledger.get("services", {})
    if svc:
        lines.append("Services:")
        for name, info in svc.items():
            state = "●" if info.get("running") else "○"
            lives = "".join(f"pid {p} " for p in info.get("pids", []))
            port = f" (port {info.get('port')} {'open' if info.get('port_open') else 'closed'})" if info.get("port") else ""
            lines.append(f"  {state} {name} {lives}{port}")
        lines.append("")

    gw = ledger.get("gateway", {})
    lines.append(
        f"Gateway: {'up' if gw.get('gateway_up') else 'down'} "
        f"(pid {gw.get('gateway_pid') or '—'}, kanban {gw.get('kanban_bytes', 0)} B)"
    )
    lia = ledger.get("lia", {})
    lines.append(
        f"Lia: bridge {'●' if lia.get('bridge_up') else '○'} "
        f"({lia.get('bridge_note')}) projects {lia.get('projects_total', 0)}"
    )
    lines.append("")

    agents = ledger.get("agents", {})
    if agents:
        lines.append("Polsia agents:")
        for name, info in sorted(agents.items()):
            last_run = info.get("last_run", "—") if isinstance(info, dict) else "—"
            lines.append(f"  {name}: last_run {last_run}")
        lines.append("")

    businesses = ledger.get("businesses", [])
    running = sum(1 for b in businesses if b.get("status") == "running")
    missing = sum(1 for b in businesses if b.get("status") == "missing")
    lines.append(f"Businesses: {len(businesses)} tracked | {running} running | {missing} missing")
    for b in businesses[:40]:
        mark = {"running": "●", "monitoring": "◐", "missing": "✕", "down": "○"}.get(b.get("status", ""), "?")
        svcs = f" [{', '.join(b.get('services', []))}]" if b.get("services") else ""
        lines.append(f"  {mark} {b['name']:32s} {b.get('category', ''):18s}{svcs}")
    if len(businesses) > 40:
        lines.append(f"  … and {len(businesses) - 40} more")

    return "\n".join(lines)