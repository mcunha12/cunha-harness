#!/usr/bin/env python3
# Barra dado pessoal em fixture de teste antes do commit: e-mail de provedor público, cidade/UF real, nome com sobrenome, telefone fora da faixa fictícia.
import json
import re
import subprocess
import sys

PUBLIC_MAIL = re.compile(r"[\w.+-]+@(gmail|hotmail|outlook|yahoo|icloud|live|uol|bol|terra|me)\.[\w.]+", re.I)
UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
       "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
NAME_KEYS = {"nome", "name", "nome_aluno", "nome_completo", "aluno_nome"}
CITY_KEYS = {"cidade", "city", "municipio"}
UF_KEYS = {"uf", "estado", "state"}
PHONE_KEYS = {"telefone", "phone", "fone", "celular", "phone_number", "whatsapp"}
PAIR = re.compile(r'"([A-Za-z_]+)"\s*:\s*"([^"]*)"')
SYNTHETIC = re.compile(r"exemplo|example|teste|test|fict|sint|aluno|fulano|zz", re.I)
# Faixa fictícia aceita: 11900xxxxxx e DDD + (9) + um dígito repetido.
FAKE_PHONE = re.compile(r"^11900\d{6}$|^\d\d9?(\d)\1{7,}$")


def _pair_findings(key, value):
    k = key.lower()
    if k in CITY_KEYS and value and not SYNTHETIC.search(value):
        return ["cidade"]
    if k in UF_KEYS and value.upper() in UFS:
        return ["uf"]
    if k in NAME_KEYS and len(value.split()) >= 2 and not SYNTHETIC.search(value):
        return ["nome"]
    digits = re.sub(r"\D", "", value)
    digits = digits[2:] if digits.startswith("55") and len(digits) > 11 else digits
    if k in PHONE_KEYS and len(digits) >= 10 and not FAKE_PHONE.match(digits):
        return ["telefone"]
    return []


def scan_text(text):
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in PUBLIC_MAIL.finditer(line):
            found.append({"kind": "email", "line": n, "value": m.group(0)})
        for key, value in PAIR.findall(line):
            for kind in _pair_findings(key, value):
                found.append({"kind": kind, "line": n, "value": value})
    return found


def scan_file(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [{**x, "path": path} for x in scan_text(f.read())]


def changed_test_files(repo, base):
    out = subprocess.run(["git", "-C", repo, "diff", "--name-only", "--diff-filter=AM", f"{base}...HEAD"],
                         capture_output=True, text=True, check=True).stdout.split()
    out += subprocess.run(["git", "-C", repo, "diff", "--name-only", "--diff-filter=AM"],
                          capture_output=True, text=True, check=True).stdout.split()
    return sorted({p for p in out if "test" in p.lower() or "fixture" in p.lower()})


def main(argv):
    if len(argv) != 3:
        print("uso: fixture_pii.py <repo> <base>  (exit 1 = achou dado pessoal)", file=sys.stderr)
        return 2
    repo, base = argv[1], argv[2]
    found = []
    for rel in changed_test_files(repo, base):
        try:
            found += scan_file(f"{repo}/{rel}")
        except FileNotFoundError:
            continue
    print(json.dumps(found, ensure_ascii=False, indent=1))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
