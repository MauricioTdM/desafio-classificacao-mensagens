from fastapi import FastAPI, HTTPException

from app.classificador import MODELO, SETOR_POR_CATEGORIA, ErroIA, classificar
from app.schemas import ClassificacaoResposta, MensagemEntrada

app = FastAPI(
    title="Classificador de Mensagens de Clientes",
    description="Recebe a mensagem de um cliente, classifica com IA (Gemini) e indica o setor responsável.",
    version="1.0.0",
)


@app.get("/")
def inicio():
    return {"mensagem": "Classificador de mensagens funcionando!", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "modelo": MODELO}


@app.get("/categorias")
def categorias():
    """Mostra as categorias possíveis e para qual setor cada uma é encaminhada."""
    return {c.value: setor for c, setor in SETOR_POR_CATEGORIA.items()}


@app.post("/classificar", response_model=ClassificacaoResposta)
def classificar_mensagem(dados: MensagemEntrada):
    mensagem = dados.mensagem.strip()
    if len(mensagem) < 3:
        raise HTTPException(status_code=422, detail="A mensagem está vazia.")
    dados.mensagem = mensagem

    try:
        ia, setor, revisao = classificar(dados)
    except ErroIA as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return ClassificacaoResposta(
        **ia.model_dump(),
        setor=setor,
        revisao_humana=revisao,
        mensagem_original=mensagem,
        cliente=dados.cliente,
        canal=dados.canal,
        modelo=MODELO,
    )
