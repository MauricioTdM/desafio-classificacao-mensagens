"""Modelos de dados (entrada, saída da IA e resposta da API).

Os mesmos modelos servem para três coisas:
1. validar o que chega na API;
2. dizer ao Gemini exatamente qual JSON ele deve devolver (response_schema);
3. validar de novo o JSON que o Gemini devolveu antes de repassar ao n8n.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Categoria(str, Enum):
    DUVIDA = "duvida"
    RECLAMACAO = "reclamacao"
    SOLICITACAO = "solicitacao"
    ELOGIO = "elogio"
    OUTRO = "outro"


class Urgencia(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class Sentimento(str, Enum):
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"


class MensagemEntrada(BaseModel):
    """O que a API recebe (normalmente enviado pelo n8n)."""

    mensagem: str = Field(min_length=3, max_length=2000, description="Texto escrito pelo cliente")
    cliente: str | None = Field(default=None, max_length=120, description="Nome do cliente (opcional)")
    canal: str | None = Field(default=None, max_length=40, description="Origem: email, whatsapp, site...")


class ClassificacaoIA(BaseModel):
    """Formato que o Gemini é obrigado a devolver."""

    categoria: Categoria = Field(description="Tipo principal da mensagem")
    assunto: str = Field(description="Assunto em poucas palavras, ex.: 'atraso na entrega'")
    urgencia: Urgencia = Field(description="Quão rápido a empresa precisa agir")
    sentimento: Sentimento = Field(description="Tom emocional do cliente")
    resumo: str = Field(description="Resumo da mensagem em uma frase")
    resposta_sugerida: str = Field(description="Primeira resposta curta e educada ao cliente")
    confianca: float = Field(ge=0, le=1, description="Confiança da classificação, de 0 a 1")


class ClassificacaoResposta(ClassificacaoIA):
    """Resposta final da API: o que a IA disse + o roteamento decidido pelo código."""

    setor: str = Field(description="Setor responsável (definido por regra, não pela IA)")
    revisao_humana: bool = Field(description="True quando a confiança é baixa ou a categoria é 'outro'")
    mensagem_original: str
    cliente: str | None = None
    canal: str | None = None
    modelo: str
