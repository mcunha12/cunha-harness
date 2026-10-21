#!/usr/bin/env python3
"""Confere o teto de linhas e a origem de cada regra da code-guard."""
import glob
import json
import os
import re
import sys

LIMITS = {"core": 150, "domain": 120, "learned": 80}
RULE = re.compile(r"^- \[[A-Z0-9]+\] ")
ORIGIN = re.compile(r" — origem: review-[a-z0-9-]+/\S")


def check_file(path, limit):
    issues = []
    with open(path) as f:
        lines = f.read().splitlines()
    if len(lines) > limit:
        issues.append({"file": path, "code": "over_budget", "lines": len(lines), "limit": limit})
    for n, line in enumerate(lines, 1):
        if RULE.match(line) and not ORIGIN.search(line):
            issues.append({"file": path, "code": "missing_origin", "line": n})
    return issues


def check(root, learned=None):
    issues = []
    core = os.path.join(root, "core.md")
    if os.path.exists(core):
        issues += check_file(core, LIMITS["core"])
    for path in sorted(glob.glob(os.path.join(root, "domains", "*.md"))):
        issues += check_file(path, LIMITS["domain"])
    for path in sorted(glob.glob(os.path.join(learned, "*.md"))) if learned else []:
        issues += check_file(path, LIMITS["learned"])
    return issues


def main(argv):
    if len(argv) < 2:
        print("uso: check_budget.py <code-guard dir> [--learned <dir>]", file=sys.stderr)
        return 2
    learned = argv[argv.index("--learned") + 1] if "--learned" in argv else None
    issues = check(argv[1], learned)
    print(json.dumps(issues, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
