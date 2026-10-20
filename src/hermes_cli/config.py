# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Copyright (c) 2026 Living Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Licensed under Living Sin Proprietary License (LSPL-1.0)
# See LICENSE file for details.
"""Paths, entities and service manifest for Hermes.CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

HOME = Path.home()
REPO_DIR = Path(os.environ.get("HERMES_REPO_DIR", HOME / "github-intricos777" / "hermes-cli"))

DEFAULT_ENTITIES = ["forge", "hermes", "lia", "polsia", "owner"]

# Canonical services that should be kept running.
# match: substrings searched in /proc/*/cmdline
# start: shell command to relaunch (used by `hermes heal`)
DEFAULT_SERVICES: dict[str, dict] = {
    "hermes-gateway": {
        "business": "hermes-self-evolve",
        "match": ["hermes_cli.main gateway run"],
        "start": "",
    },
    "system-resource-optimizer": {
        "business": "system-resource-optimizer",
        "match": ["auto_optimizer.py"],
    },
    "crypto-bot": {
        "business": "crypto-bot",
        "match": ["crypto-bot/node_modules", "crypto-bot"],
        "port": 4123,
    },
}

DEFAULT_CONFIG: dict = {
    "repo_dir": str(REPO_DIR),
    "remote": "https://github.com/intricos777-dot/hermes-cli.git",
    "branch": "main",
    "autopush": True,
    "entities": DEFAULT_ENTITIES,
    "heartbeat_entity_default": "hermes",
    "paths": {
        "polsia_registry": str(HOME / "Projects" / "polsia" / "registry.yaml"),
        "polsia_businesses": str(HOME / "Projects" / "polsia" / "businesses"),
        "polsia_config": str(HOME / ".config" / "polsia" / "config.yaml"),
        "polsia_memory": str(HOME / ".local" / "share" / "polsia" / "memory.json"),
        "polsia_active": str(HOME / ".config" / "polsia" / "active.json"),
        "polsia_cli": "polsia",
        "lia_plan": str(HOME / "github-intricos777" / "lia-cli" / "tasks" / "active-plan.json"),
        "lia_bridge": "http://localhost:4123",
        "lia_history": str(HOME / ".lia-cli" / "history.jsonl"),
        "hermes_gateway_pid": str(HOME / ".hermes" / "gateway.pid"),
        "hermes_kanban": str(HOME / ".hermes" / "kanban.db"),
        "hermes_home": str(HOME / ".hermes"),
    },
    "services": DEFAULT_SERVICES,
}


def config_path() -> Path:
    return REPO_DIR / "config.yaml"


def state_dir() -> Path:
    return REPO_DIR / "state"


def load_config() -> dict:
    cfg_path = config_path()
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as fh:
            overlay = yaml.safe_load(fh) or {}
        _deep_merge(cfg, overlay)
    return cfg


def save_config(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)


def _deep_merge(base: dict, overlay: dict) -> dict:
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def ensure_state_dirs(cfg: dict) -> None:
    sdir = REPO_DIR / "state"
    (sdir / "inbox").mkdir(parents=True, exist_ok=True)
    (sdir / "logs").mkdir(parents=True, exist_ok=True)
    for entity in cfg.get("entities", DEFAULT_ENTITIES):
        (sdir / "inbox" / entity).mkdir(parents=True, exist_ok=True)


def log_dir() -> Path:
    return REPO_DIR / "state" / "logs"