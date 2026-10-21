#!/usr/bin/env python3
"""Acha o overlay de empresa que vale para um repo, pelo remote do git."""
import json
import os
import subprocess
import sys


def overlays_home():
    return os.environ.get("OVERLAYS_HOME", os.path.expanduser("~/.claude/overlays"))


def match(repo_path):
    config = os.path.join(overlays_home(), "overlays.json")
    if not os.path.exists(config):
        return {}
    with open(config) as f:
        overlays = json.load(f).get("overlays", [])
    result = subprocess.run(["git", "-C", repo_path, "remote", "-v"], capture_output=True, text=True)
    remotes = result.stdout.lower()
    for entry in overlays:
        if any(term.lower() in remotes for term in entry.get("remote_contains", [])):
            return {**entry, "dir": overlays_home()}
    return {}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "match":
        print("uso: overlay.py match <repo_path>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(match(sys.argv[2]), ensure_ascii=False))
