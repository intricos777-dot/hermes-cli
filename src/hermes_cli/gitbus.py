# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""Git backchannel: pull/rebase → write → commit → push.

GitHub is the durable bus: the ledger, journal and inboxes live in the
repo itself. A sync means pull any remote truths, then push local truths.
Works even when no one is watching the machine.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


class GitBusError(RuntimeError):
    pass


def _run(cwd: Path, args: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        raise GitBusError(f"git {' '.join(args)} timed out")


def pull(cfg: dict, repo_dir: Path) -> str:
    """Fetch and rebase onto the remote. Tolerates first-run / no-remote."""
    branch = cfg.get("branch", "main")
    if not (repo_dir / ".git").exists():
        _run(repo_dir, ["init", "-b", branch])
    remote = cfg.get("remote", "")
    if remote:
        rc, out = _run(repo_dir, ["remote", "get-url", "origin"])
        if rc != 0 or "origin" not in out:
            _run(repo_dir, ["remote", "add", "origin", remote])
        code, msg = _run(repo_dir, ["fetch", "origin", branch], timeout=90)
        if code == 0:
            _run(repo_dir, ["rebase", f"origin/{branch}"])
        else:
            msg = "fetch failed (offline or unborn remote); continuing locally"
    else:
        msg = "no remote configured; skipping pull"
    return msg


def dirty(repo_dir: Path) -> bool:
    code, out = _run(repo_dir, ["status", "--porcelain"])
    if code != 0:
        return False
    return bool(out.strip())


def commit_and_push(cfg: dict, repo_dir: Path, message: str) -> str:
    """Commit any pending changes and push. Returns a report string."""
    if not dirty(repo_dir):
        return "no changes to sync"

    # Ensure identity exists (per-repo, does not touch global config).
    who, email = _git_identity(repo_dir)
    if not who or not email:
        _run(repo_dir, ["config", "user.name", "Hermes.CLI"])
        _run(repo_dir, ["config", "user.email", "intricos777@gmail.com"])

    _run(repo_dir, ["add", "-A"])
    rc, out = _run(repo_dir, ["commit", "-m", message])
    if rc != 0:
        return f"commit failed: {out.strip()}"

    remote = cfg.get("remote", "")
    branch = cfg.get("branch", "main")
    if remote and cfg.get("autopush", True):
        code, out = _run(repo_dir, ["push", "origin", f"HEAD:{branch}"], timeout=90)
        if code != 0:
            return f"committed; push pending: {out.strip()}"
        return f"committed + pushed: {out.strip()}"
    return "committed locally (no remote or autopush off)"


def _git_identity(repo_dir: Path) -> tuple[str, str]:
    who = _run(repo_dir, ["config", "user.name"])[1].strip()
    email = _run(repo_dir, ["config", "user.email"])[1].strip()
    return who, email


def sync(cfg: dict, repo_dir: Path, message: str) -> tuple[str, str]:
    """Pull, then commit/push. Returns (pull_report, push_report)."""
    pull_report = pull(cfg, repo_dir)
    time.sleep(0.3)
    push_report = commit_and_push(cfg, repo_dir, message)
    return pull_report, push_report