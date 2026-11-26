"""Importa o workflow no n8n pela API pública, cria as credenciais do Discord e ativa o fluxo.

Lê tudo do .env (nada de chave no código):
  N8N_URL                      (padrão http://localhost:5678)
  N8N_API_KEY                  (Settings > n8n API no n8n)
  API_URL_N8N                  (URL da API vista pelo n8n; padrão http://localhost:8000)
  DISCORD_WEBHOOK_ATENDIMENTO, DISCORD_WEBHOOK_SAC,
  DISCORD_WEBHOOK_OPERACOES,   DISCORD_WEBHOOK_TRIAGEM

Uso:  python scripts/configurar_n8n.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

N8N_URL = os.getenv("N8N_URL", "http://localhost:5678").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY", "")
# "localhost" no Node pode virar IPv6 (::1) e o uvicorn escuta em 127.0.0.1, então forçamos IPv4.
API_URL_N8N = os.getenv("API_URL_N8N", "http://127.0.0.1:8000").rstrip("/").replace("://localhost", "://127.0.0.1")
WORKFLOW = RAIZ / "n8n" / "workflow-classificacao.json"

DISCORD = {
    "Discord - Atendimento": "DISCORD_WEBHOOK_ATENDIMENTO",
    "Discord - SAC": "DISCORD_WEBHOOK_SAC",
    "Discord - Operações": "DISCORD_WEBHOOK_OPERACOES",
    "Discord - Triagem": "DISCORD_WEBHOOK_TRIAGEM",
}


def n8n(metodo: str, caminho: str, corpo: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{N8N_URL}/api/v1{caminho}",
        method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            texto = r.read().decode()
            return json.loads(texto) if texto else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"Erro {e.code} em {metodo} {caminho}: {e.read().decode()[:500]}")


def main():
    if not API_KEY:
        sys.exit("Preencha N8N_API_KEY no .env (n8n > Settings > n8n API > Create API key).")
    faltando = [v for v in DISCORD.values() if not os.getenv(v)]
    if faltando:
        sys.exit(f"Preencha no .env: {', '.join(faltando)}")

    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    existentes = n8n("GET", "/workflows?limit=250").get("data", [])
    atual = next((w for w in existentes if w["name"] == wf["name"]), None)

    # Se o workflow já existe, reaproveita as credenciais já ligadas aos nodes (evita duplicar)
    creds_atuais = {}
    if atual:
        for node in n8n("GET", f"/workflows/{atual['id']}")["nodes"]:
            if node.get("credentials"):
                creds_atuais[node["name"]] = node["credentials"]

    # 1) Credenciais do Discord (uma por setor). Ficam só no n8n, nunca no JSON do repositório.
    for node in wf["nodes"]:
        if node["name"] in creds_atuais:
            node["credentials"] = creds_atuais[node["name"]]
        elif node["name"] in DISCORD:
            cred = n8n("POST", "/credentials", {
                "name": f"Webhook {node['name']}",
                "type": "discordWebhookApi",
                "data": {"webhookUri": os.getenv(DISCORD[node["name"]])},
            })
            node["credentials"] = {"discordWebhookApi": {"id": cred["id"], "name": cred["name"]}}
            print(f"Credencial criada: {cred['name']}")
        if node["type"] == "n8n-nodes-base.httpRequest":
            node["parameters"]["url"] = f"{API_URL_N8N}/classificar"

    # 2) Cria ou atualiza o workflow (mesmo nome = atualiza)
    corpo = {k: wf[k] for k in ("name", "nodes", "connections", "settings")}
    if atual:
        n8n("POST", f"/workflows/{atual['id']}/deactivate")
        wid = n8n("PUT", f"/workflows/{atual['id']}", corpo)["id"]
        print(f"Workflow atualizado: {wid}")
    else:
        wid = n8n("POST", "/workflows", corpo)["id"]
        print(f"Workflow criado: {wid}")

    # 3) Ativa (o webhook de produção passa a responder em /webhook/mensagens)
    n8n("POST", f"/workflows/{wid}/activate")
    print(f"Ativo! Envie mensagens para {N8N_URL}/webhook/mensagens")
    print(f"Abrir no editor: {N8N_URL}/workflow/{wid}")


if __name__ == "__main__":
    main()
