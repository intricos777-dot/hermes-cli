# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""The keeper: heal what is down, watch while the owner is away.

Ritual without result is mere ceremony — heal actually relaunches
configured services, then journals what happened.
"""

from __future__ import annotations

import subprocess
import time

from . import health, ledger, msg


def heal(cfg: dict, state, source: str = "hermes-cli") -> list[dict]:
    """Restart every configured service that is not currently running."""
    procs = health.scan_processes()
    rules = health.describe_service_rules(cfg)
    actions = []
    for svc_name, rule in rules.items():
        running, _ = health.service_running(procs, rule)
        start_cmd = rule.get("start", "")
        if running:
            continue
        if not start_cmd:
            actions.append({"service": svc_name, "ok": False, "why": "down and no start command configured"})
            continue
        try:
            code = subprocess.call(start_cmd, shell=True)  # noqa: S602
            ok = code == 0
            actions.append({"service": svc_name, "ok": ok, "why": "restarted" if ok else f"start rc={code}"})
            if ok:
                msg.append_journal(state, source, f"healed: restarted {svc_name}")
        except Exception as exc:  # noqa: BLE001
            actions.append({"service": svc_name, "ok": False, "why": f"start threw {exc}"})
    return actions


def watch_once(cfg: dict, state, source: str = "hermes-cli") -> dict:
    """One keeper pass: reconcile ledger, heal down services, journal."""
    was = ledger.build_ledger(cfg, state)
    actions = heal(cfg, state, source=source)
    msg.stamp_heartbeat(state, cfg.get("heartbeat_entity_default", "hermes"), note="watch pass")
    return {"restarted": [a for a in actions if a.get("ok")], "failed": [a for a in actions if not a.get("ok")]}


def watch_loop(cfg: dict, state, interval: int = 900, stop_after: int | None = None, source: str = "hermes-cli") -> None:
    import logging
    import sys
    from pathlib import Path

    from . import config

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[logging.FileHandler(config.log_dir() / "watch.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    started = time.time()
    runs = 0
    while True:
        runs += 1
        try:
            result = watch_once(cfg, state, source=source)
            logging.info("watch pass %d: restarted=%s failed=%s", runs, len(result["restarted"]), len(result["failed"]))
        except Exception as exc:  # noqa: BLE001
            logging.error("watch pass %d failed: %s", runs, exc)
        if stop_after and runs >= stop_after:
            break
        if stop_after is None:
            time.sleep(interval)
        else:
            time.sleep(interval if runs < stop_after else 0)