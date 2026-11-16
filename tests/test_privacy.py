"""Privacy scan of every tracked file: no emails, keys, tokens or local paths."""

import os
import re
import subprocess

from fcp.fetch import ROOT

SELF = "tests/test_privacy.py"
BINARY = (".xlsx", ".xls", ".png", ".jpg", ".gif", ".ico", ".pdf", ".zip", ".mp4")

PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "openai_like_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer_literal": re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),
    "windows_user_path": re.compile(r"[A-Za-z]:[\\/]+(Users|dev)[\\/]", re.I),
    "wsl_mount_path": re.compile(r"/mnt/[a-z]/"),
    "root_home_path": re.compile(r"/root/"),
    "home_path": re.compile(r"/home/[a-z]"),
    "appdata": re.compile(r"AppData", re.I),
}
# Public data files contain text we do not control; only these patterns apply there.
RAW_PATTERNS = ("email", "aws_key", "github_token", "openai_like_key", "slack_token", "private_key", "bearer_literal")


def tracked_files():
    if os.path.isdir(os.path.join(ROOT, ".git")) or os.path.isfile(os.path.join(ROOT, ".git")):
        out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
        return [p for p in out.splitlines() if p and p != SELF]
    # Plain copy (e.g. a Desktop save): scan every file except caches.
    files = []
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", ".pytest_cache", ".hydradb")]
        for n in names:
            rel = os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/")
            if rel != SELF and rel != "SAVE-INFO.txt":
                files.append(rel)
    return files


def test_no_private_data_in_tracked_files():
    hits = []
    for rel in tracked_files():
        if rel.lower().endswith(BINARY):
            continue
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
            text = f.read()
        names = RAW_PATTERNS if rel.startswith("data/raw/") else PATTERNS
        for name in names:
            m = PATTERNS[name].search(text)
            if m:
                hits.append((rel, name, m.group(0)[:40]))
    assert not hits, hits


def test_current_hydradb_token_not_committed():
    tok_path = os.path.join(ROOT, ".hydradb", "token")
    if not os.path.exists(tok_path):
        return
    with open(tok_path, encoding="utf-8") as f:
        token = f.read().strip()
    assert len(token) >= 32
    for rel in tracked_files():
        with open(os.path.join(ROOT, rel), "rb") as f:
            assert token.encode() not in f.read(), rel


def test_token_and_run_dirs_are_ignored():
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        ignore = f.read()
    assert ".hydradb/" in ignore
