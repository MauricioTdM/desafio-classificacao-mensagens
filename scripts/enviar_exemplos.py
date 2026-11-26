"""Envia as mensagens de exemplo para o webhook do n8n (ou direto para a API) e mostra o resultado.

Uso:
  python scripts/enviar_exemplos.py                 # via n8n  (http://localhost:5678/webhook/mensagens)
  python scripts/enviar_exemplos.py --api           # direto na API (http://localhost:8000/classificar)
  python scripts/enviar_exemplos.py --url <URL>     # outra URL (ex.: /webhook-test/mensagens)
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos" / "mensagens.json"

url = "http://localhost:5678/webhook/mensagens"
if "--api" in sys.argv:
    url = "http://localhost:8000/classificar"
if "--url" in sys.argv:
    url = sys.argv[sys.argv.index("--url") + 1]

for msg in json.loads(EXEMPLOS.read_text(encoding="utf-8")):
    req = urllib.request.Request(url, data=json.dumps(msg).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            corpo = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        corpo = {"erro": e.code, "detalhe": e.read().decode()[:300]}
    c = corpo.get("classificacao", corpo)
    print(f"- {msg['mensagem'][:60]!r}")
    print(f"  -> {c.get('categoria')} | setor={c.get('setor')} | urgencia={c.get('urgencia')} "
          f"| confianca={c.get('confianca')} | revisao={c.get('revisao_humana')}"
          if "categoria" in c else f"  -> {corpo}")
