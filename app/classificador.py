"""Integração com o Gemini e regras de roteamento."""

import os

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from app.prompts import SYSTEM_PROMPT, montar_mensagem_usuario
from app.schemas import Categoria, ClassificacaoIA, MensagemEntrada

load_dotenv()

MODELO = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
LIMIAR_CONFIANCA = float(os.getenv("LIMIAR_CONFIANCA", "0.6"))

# Roteamento: a IA só classifica; QUEM recebe é decidido por regra fixa e auditável.
SETOR_POR_CATEGORIA = {
    Categoria.DUVIDA: "atendimento",
    Categoria.RECLAMACAO: "sac",
    Categoria.SOLICITACAO: "operacoes",
    Categoria.ELOGIO: "atendimento",
    Categoria.OUTRO: "triagem",
}


class ErroIA(Exception):
    """A IA não respondeu ou respondeu fora do formato."""


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ErroIA("Configure a variável de ambiente GEMINI_API_KEY.")
        _client = genai.Client(api_key=api_key)
    return _client


def chamar_gemini(entrada: MensagemEntrada) -> str:
    """Chama o modelo pedindo saída JSON no esquema ClassificacaoIA. Retorna o texto bruto."""
    resposta = _get_client().models.generate_content(
        model=MODELO,
        contents=montar_mensagem_usuario(entrada.mensagem, entrada.cliente, entrada.canal),
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.1,  # baixa: queremos consistência, não criatividade
            "max_output_tokens": 600,
            "response_mime_type": "application/json",
            "response_schema": ClassificacaoIA,
        },
    )
    if not resposta.text:
        raise ErroIA("O Gemini não retornou texto.")
    return resposta.text


def classificar(entrada: MensagemEntrada) -> tuple[ClassificacaoIA, str, bool]:
    """Classifica a mensagem e devolve (classificação, setor, precisa_revisao_humana).

    Tenta duas vezes: se o JSON vier inválido na primeira, chama de novo.
    """
    ultimo_erro: Exception | None = None
    for _ in range(2):
        try:
            texto = chamar_gemini(entrada)
            ia = ClassificacaoIA.model_validate_json(texto)
            break
        except ValidationError as e:
            ultimo_erro = e
        except ErroIA:
            raise
        except Exception as e:  # erro de rede / API
            raise ErroIA(f"Falha ao chamar o Gemini: {e}") from e
    else:
        raise ErroIA(f"O Gemini devolveu um JSON fora do formato esperado: {ultimo_erro}")

    setor = SETOR_POR_CATEGORIA[ia.categoria]
    revisao = ia.confianca < LIMIAR_CONFIANCA or ia.categoria == Categoria.OUTRO
    return ia, setor, revisao
