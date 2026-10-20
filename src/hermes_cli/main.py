# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Copyright (c) 2026 Living Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Licensed under Living Sin Proprietary License (LSPL-1.0)
# See LICENSE file for details.
"""Hermes.CLI — main entry point.

Sync messenger and business ledger keeper.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import config, gitbus, health, keeper, ledger, msg, sources


def _load_state(cfg: dict) -> Path:
    state = Path(cfg.get("repo_dir", config.REPO_DIR)) / "state"
    state.mkdir(parents=True, exist_ok=True)
    config.ensure_state_dirs(cfg)
    return state


def cmd_sync(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    message = " ".join(args) if args else f"sync {config._now()}"
    pull_report, push_report = gitbus.sync(cfg, Path(cfg["repo_dir"]), message)
    print(f"pull: {pull_report}")
    print(f"push: {push_report}")
    return 0


def cmd_ledger(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    ledger_data = ledger.build_ledger(cfg, state)
    print(ledger.render_ledger(ledger_data))
    return 0


def cmd_heal(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    actions = keeper.heal(cfg, state)
    for a in actions:
        status = "✓" if a.get("ok") else "✗"
        print(f"  {status} {a['service']}: {a['why']}")
    return 0


def cmd_watch(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    interval = int(args[0]) if args else 900
    stop_after = int(args[1]) if len(args) > 1 else None
    keeper.watch_loop(cfg, state, interval=interval, stop_after=stop_after)
    return 0


def cmd_journal(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    limit = int(args[0]) if args else 40
    source = args[1] if len(args) > 1 else None
    entries = msg.read_journal(state, limit=limit, source=source)
    for e in entries:
        print(f"[{e['ts']}] {e['from']} -> {e['to']}: {e['msg']}")
    return 0


def cmd_send(args: list[str]) -> int:
    if len(args) < 3:
        print("usage: hermes send <to_entity> <from_entity> <message>")
        return 1
    cfg = config.load_config()
    state = _load_state(cfg)
    to_entity, from_entity = args[0], args[1]
    message = " ".join(args[2:])
    entry = msg.send_message(state, to_entity, from_entity, message)
    print(f"sent: {entry['id']}")
    return 0


def cmd_inbox(args: list[str]) -> int:
    if not args:
        print("usage: hermes inbox <entity> [--no-mark-read]")
        return 1
    cfg = config.load_config()
    state = _load_state(cfg)
    entity = args[0]
    mark_read = "--no-mark-read" not in args
    entries = msg.read_inbox(state, entity, mark_read=mark_read)
    for e in entries:
        status = "●" if e.get("read") else "○"
        print(f"[{e['ts']}] {status} {e['from']}: {e['msg']}")
    return 0


def cmd_heartbeat(args: list[str]) -> int:
    cfg = config.load_config()
    state = _load_state(cfg)
    if args:
        entity = args[0]
        note = " ".join(args[1:]) if len(args) > 1 else ""
        msg.stamp_heartbeat(state, entity, note)
        print(f"heartbeat stamped for {entity}")
    else:
        beats = msg.render_heartbeats(state)
        for entity, info in beats:
            print(f"  {entity}: {info['last']} — {info['note']}")
    return 0


def cmd_config(args: list[str]) -> int:
    cfg = config.load_config()
    import yaml
    print(yaml.dump(cfg, sort_keys=False, allow_unicode=True))
    return 0


def cmd_services(args: list[str]) -> int:
    cfg = config.load_config()
    procs = health.scan_processes()
    rules = health.describe_service_rules(cfg)
    for svc_name, rule in rules.items():
        running, hits = health.service_running(procs, rule)
        status = "●" if running else "○"
        pids = " ".join(f"pid {h['pid']}" for h in hits)
        port = f" port={rule.get('port')}" if rule.get("port") else ""
        print(f"  {status} {svc_name}{port} [{pids}]")
    return 0


COMMANDS = {
    "sync": cmd_sync,
    "ledger": cmd_ledger,
    "heal": cmd_heal,
    "watch": cmd_watch,
    "journal": cmd_journal,
    "send": cmd_send,
    "inbox": cmd_inbox,
    "heartbeat": cmd_heartbeat,
    "config": cmd_config,
    "services": cmd_services,
}


def _print_help() -> None:
    print(__doc__.strip())
    print("\nCommands:")
    for name in sorted(COMMANDS):
        print(f"  hermes {name}")
    print("\nUse 'hermes <command> --help' for command-specific help.")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        _print_help()
        return 0 if len(sys.argv) > 1 else 1

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        _print_help()
        return 1

    if len(sys.argv) > 2 and sys.argv[2] in ("-h", "--help"):
        # Could add per-command help here
        pass

    return COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())