"""Testes da API sem gastar chamadas reais ao Gemini (a chamada é simulada)."""

import json
import os

os.environ.setdefault("GEMINI_API_KEY", "chave-falsa-para-teste")

import pytest
from fastapi.testclient import TestClient

from app import classificador
from app.main import app

client = TestClient(app)


def resposta_ia(**sobrescrever):
    base = {
        "categoria": "reclamacao",
        "assunto": "produto com defeito",
        "urgencia": "alta",
        "sentimento": "negativo",
        "resumo": "Cliente informa que o produto chegou quebrado.",
        "resposta_sugerida": "Sentimos muito! Vamos resolver isso para você.",
        "confianca": 0.93,
    }
    base.update(sobrescrever)
    return json.dumps(base)


@pytest.fixture
def gemini_falso(monkeypatch):
    respostas = []

    def fake(_entrada):
        return respostas.pop(0)

    monkeypatch.setattr(classificador, "chamar_gemini", fake)
    return respostas


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_classifica_e_roteia_reclamacao(gemini_falso):
    gemini_falso.append(resposta_ia())
    r = client.post("/classificar", json={"mensagem": "Meu fone chegou quebrado!", "cliente": "Ana"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["categoria"] == "reclamacao"
    assert corpo["setor"] == "sac"
    assert corpo["revisao_humana"] is False
    assert corpo["cliente"] == "Ana"


@pytest.mark.parametrize(
    "categoria,setor",
    [("duvida", "atendimento"), ("solicitacao", "operacoes"), ("elogio", "atendimento"), ("outro", "triagem")],
)
def test_setor_por_categoria(gemini_falso, categoria, setor):
    gemini_falso.append(resposta_ia(categoria=categoria))
    assert client.post("/classificar", json={"mensagem": "texto qualquer"}).json()["setor"] == setor


def test_confianca_baixa_pede_revisao(gemini_falso):
    gemini_falso.append(resposta_ia(confianca=0.4))
    assert client.post("/classificar", json={"mensagem": "hmm"}).json()["revisao_humana"] is True


def test_json_invalido_tenta_de_novo(gemini_falso):
    gemini_falso.extend(["isso não é json", resposta_ia(categoria="duvida")])
    r = client.post("/classificar", json={"mensagem": "Qual o prazo?"})
    assert r.status_code == 200
    assert r.json()["categoria"] == "duvida"


def test_json_invalido_duas_vezes_retorna_502(gemini_falso):
    gemini_falso.extend(["{}", resposta_ia(categoria="inexistente")])
    assert client.post("/classificar", json={"mensagem": "Qual o prazo?"}).status_code == 502


def test_mensagem_vazia_rejeitada():
    assert client.post("/classificar", json={"mensagem": "     "}).status_code == 422
    assert client.post("/classificar", json={}).status_code == 422
