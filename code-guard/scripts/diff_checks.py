#!/usr/bin/env python3
"""Checagens determinísticas sobre o diff: régua afrouxada (embutidas) e checagens aprendidas pela code-guard."""
import argparse
import json
import os
import re
import subprocess
import sys

BUILTIN = [
    {"id": "ts-suppress", "pattern": r"@ts-(ignore|nocheck)\b|@ts-expect-error\s*(\*/)?\s*$",
     "files": r"\.(ts|tsx|js|jsx|mts|cts|vue)$", "message": "Supressão do TypeScript sem motivo.",
     "origin": "review-tipagem/escape"},
    {"id": "lint-suppress", "pattern": r"eslint-disable(?!.*\s--\s)|biome-ignore(?![^:]*:)|#\s*noqa\s*$|pylint:\s*disable",
     "files": r".", "message": "Lint desligado sem motivo (use '-- motivo').", "origin": "review-legibilidade/escape"},
    {"id": "type-ignore", "pattern": r"#\s*type:\s*ignore(?!\[)", "files": r"\.pyi?$",
     "message": "type: ignore sem código de erro.", "origin": "review-tipagem/escape"},
    {"id": "test-skip", "pattern": r"\b(it|test|describe)\.(skip|only|todo)\(|\b(xit|xdescribe|fit|fdescribe)\(|"
                                   r"@pytest\.mark\.skip|pytest\.skip\(|unittest\.skip",
     "files": r".", "message": "Teste desligado ou isolado.", "origin": "test-audit/teste-desligado"},
    {"id": "strict-off", "pattern": r"\"(strict|noImplicitAny|strictNullChecks)\"\s*:\s*false",
     "files": r"tsconfig[^/]*\.json$", "message": "Modo estrito do TypeScript desligado.", "origin": "review-tipagem/tsconfig"},
    {"id": "lint-rule-weakened", "pattern": r"[\"']?[\w@/-]+[\"']?\s*[:=]\s*\[?\s*[\"']?(off|warn)[\"']?|[\"'][\w@/-]+[\"']\s*:\s*[01]\b",
     "files": r"(eslint|biome|\.ruff|ruff\.toml|\.flake8|\.pylintrc)", "message": "Regra de lint afrouxada.",
     "origin": "review-legibilidade/escape"},
]
COVERAGE_FILES = re.compile(r"(jest|vitest|nyc|\.c8rc|karma|pyproject\.toml|setup\.cfg|\.coveragerc)")
COVERAGE_KEY = re.compile(r"\b(branches|functions|lines|statements|fail_under|threshold)\b\D*?(\d+(\.\d+)?)")


def home():
    return os.environ.get("CODE_GUARD_HOME", os.path.expanduser("~/.claude/code-guard"))


def learned_checks():
    path = os.path.join(home(), "learned", "checks.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def changed_lines(repo, base, uncommitted):
    merge_base = _git(repo, "merge-base", base, "HEAD").strip()
    diff = _git(repo, "diff", "--unified=0", merge_base) if uncommitted else _git(repo, "diff", "--unified=0", f"{merge_base}...HEAD")
    added, removed, current, line_no = [], [], None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            line_no = int(re.search(r"\+(\d+)", line).group(1))
        elif current and line.startswith("+"):
            added.append((current, line_no, line[1:]))
            line_no += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            removed.append((current, line[1:]))
    if uncommitted:
        for name in _git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
            try:
                with open(os.path.join(repo, name)) as f:
                    added += [(name, n, text.rstrip("\n")) for n, text in enumerate(f, 1)]
            except (UnicodeDecodeError, OSError):
                continue
    return added, removed


def _finding(index, check, file, line, text):
    return {"id": f"CHK-{index:03d}", "agent": "code-guard-checks", "severity": "MAJOR", "confidence": "alta",
            "category": check["id"], "location": {"repo": "", "file": file, "lines": str(line)},
            "evidence": text.strip()[:300], "problem": check["message"],
            "fix": "Remova a mudança ou registre o motivo na própria linha e no MR.", "auto_fixable": False,
            "effort": "S", "refs": [check.get("origin", "")], "introduced_by_diff": True,
            "verification": "confirmado", "proof_level": 2}


def run(repo, base, uncommitted):
    added, removed = changed_lines(repo, base, uncommitted)
    findings = []
    for check in BUILTIN + learned_checks():
        pattern, files = re.compile(check["pattern"]), re.compile(check.get("files", "."))
        for file, line, text in added:
            if files.search(file) and pattern.search(text):
                findings.append(_finding(len(findings) + 1, check, file, line, text))
    old = {}
    for file, text in removed:
        if COVERAGE_FILES.search(file):
            for key, value, _ in COVERAGE_KEY.findall(text):
                old[(file, key)] = float(value)
    lowered = {"id": "coverage-lowered", "message": "Limite de cobertura reduzido.", "origin": "test-audit/cobertura"}
    for file, line, text in added:
        if COVERAGE_FILES.search(file):
            for key, value, _ in COVERAGE_KEY.findall(text):
                if (file, key) in old and float(value) < old[(file, key)]:
                    findings.append(_finding(len(findings) + 1, lowered, file, line, text))
    return {"agent": "code-guard-checks", "summary": f"{len(findings)} checagens dispararam.", "findings": findings}


def add_check(check, ident):
    try:
        pattern = re.compile(check["pattern"])
    except re.error as exc:
        print(f"regex inválida: {exc}", file=sys.stderr)
        return 1
    samples = []
    ledger = os.path.join(home(), "ledger.jsonl")
    if os.path.exists(ledger):
        with open(ledger) as f:
            for raw in f:
                try:
                    row = json.loads(raw)
                except ValueError:
                    continue
                if row.get("identity") == ident and row.get("evidence"):
                    samples += row["evidence"].splitlines()
    if not any(pattern.search(line) for line in samples):
        print("a checagem não dispara em nenhuma ocorrência real do ledger", file=sys.stderr)
        return 1
    path = os.path.join(home(), "learned", "checks.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    checks = [c for c in learned_checks() if c["id"] != check["id"]] + [check]
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(checks, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    print(json.dumps({"added": check["id"]}))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--repo", default=".")
    r.add_argument("--base", required=True)
    r.add_argument("--uncommitted", action="store_true")
    a = sub.add_parser("add-check")
    for name in ("id", "pattern", "files", "message", "origin", "identity"):
        a.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "run":
        print(json.dumps(run(args.repo, args.base, args.uncommitted), ensure_ascii=False))
        return 0
    check = {"id": args.id, "pattern": args.pattern, "files": args.files, "message": args.message, "origin": args.origin}
    return add_check(check, args.identity)


if __name__ == "__main__":
    sys.exit(main())
