#!/usr/bin/env python3
"""Gera o apps.json do Windex varrendo as pastas das abas.

Uso (na raiz do repositório):  python3 gerar_apps_json.py
O Windex lê o apps.json ao abrir e adiciona sozinho os apps novos.
Regras:
  - cada pasta abaixo corresponde a uma aba do Windex;
  - todo arquivo .html/.htm da pasta (e subpastas) vira um app;
  - se existir um .png com o mesmo nome, ele é usado como ícone.
"""
import json
import pathlib

PASTAS = {            # letra da aba -> pasta (iguais às do Windex)
    "p": "português",
    "m": "matemática",
    "g": "games",
    "u": "multimídia",
    "o": "outros",
}

raiz = pathlib.Path(__file__).resolve().parent
apps = []
for chave, pasta in PASTAS.items():
    base = raiz / pasta
    if not base.is_dir():
        continue
    for arq in sorted(base.rglob("*")):
        if not arq.is_file() or arq.suffix.lower() not in (".html", ".htm"):
            continue
        rel = arq.relative_to(base).as_posix()
        if any(p.startswith((".", "_")) for p in rel.split("/")):
            continue
        nome = arq.stem.replace("_", " ").replace("-", " ").strip()
        item = {"name": nome[:1].upper() + nome[1:], "url": rel, "category": chave}
        icone = arq.with_suffix(".png")
        if icone.is_file():
            item["icon"] = icone.relative_to(base).as_posix()
        apps.append(item)

(raiz / "apps.json").write_text(
    json.dumps({"version": 1, "apps": apps}, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"apps.json gerado com {len(apps)} apps")
