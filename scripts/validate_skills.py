#!/usr/bin/env python3
"""Valida as skills do repo (frontmatter, arquivos citados) e aproxima o roteamento pela descrição, sem token."""
import json
import math
import os
import re
import sys
import unicodedata

STOPWORDS = set("""a o os as de da do das dos e em no na nos nas um uma uns umas para por com sem que se ao aos
isso esse essa este esta desse dessa deste desta aqui ali the and for use with via não nao como mais sobre
pr mr diff""".split())
REF = re.compile(r"`((?:references|scripts|prompts|domains)/[\w./-]+)`")
ABS_REF = re.compile(r"~/\.claude/skills/([\w-]+)/([\w./-]+)")


def _frontmatter(text):
    if not text.startswith("---\n"):
        return {}
    block = text[4:text.find("\n---", 4)]
    meta = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"')
    return meta


def load_skills(root):
    skills = {}
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(path):
            with open(path) as f:
                text = f.read()
            skills[name] = {"meta": _frontmatter(text), "text": text, "dir": os.path.join(root, name)}
    return skills


def validate(root):
    errors = []
    skills = load_skills(root)
    for name, skill in skills.items():
        meta = skill["meta"]
        if meta.get("name") != name:
            errors.append({"skill": name, "code": "name_mismatch", "found": meta.get("name")})
        description = meta.get("description", "")
        if not description or description == ">":
            if not re.search(r"^description:\s*>\s*\n\s+\S", skill["text"], re.M):
                errors.append({"skill": name, "code": "missing_description"})
        elif len(description) > 1024:
            errors.append({"skill": name, "code": "description_too_long", "length": len(description)})
        for ref in REF.findall(skill["text"]):
            if any(c in ref for c in "<*{") or ref.endswith("/"):
                continue
            if not os.path.exists(os.path.join(skill["dir"], ref)):
                errors.append({"skill": name, "code": "missing_reference", "ref": ref})
        for other, ref in ABS_REF.findall(skill["text"]):
            if other in skills and not any(c in ref for c in "<*{") and not ref.endswith("/"):
                if not os.path.exists(os.path.join(root, other, ref)):
                    errors.append({"skill": name, "code": "missing_reference", "ref": f"{other}/{ref}"})
    return errors


def _tokens(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {t for t in re.split(r"[^a-z0-9+]+", text) if len(t) >= 2 and t not in STOPWORDS}


def _description(skill):
    text = skill["text"]
    match = re.search(r"^description:\s*(>\s*\n((?:\s+.+\n)+)|.+)", text, re.M)
    text = (match.group(2) or match.group(1)) if match else ""
    # o que a skill diz que NÃO cobre não pode virar gatilho
    return re.split(r"(?i)\bn[aã]o cobre\b", text)[0]


def route(prompt, skills):
    docs = {name: _tokens(_description(s)) for name, s in skills.items()}
    names = {name: _tokens(name.replace("-", " ")) for name in skills}
    count = len(docs)
    idf = {}
    for tokens in docs.values():
        for t in tokens:
            idf[t] = idf.get(t, 0) + 1
    words = _tokens(prompt)

    def score(name):
        hit = sum(math.log(1 + count / idf[t]) for t in words if t in docs[name])
        return hit + 2 * sum(math.log(1 + count) for t in words if t in names[name])

    return sorted(skills, key=lambda n: (-score(n), n))


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errors = validate(root)
    print(json.dumps(errors, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
