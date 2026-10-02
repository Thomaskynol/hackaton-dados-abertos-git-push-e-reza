"""Camada de resposta via OpenRouter (modelo xiaomi/mimo-v2-flash).

RAG simples: o chamador monta `contexto_dados` em texto a partir dos
dados reais do Mongo; o LLM só reescreve a resposta com esse contexto.
Sem chave, falha de rede/timeout ou resposta inválida → None (nunca raise),
e o chamador cai no fluxo atual (real formatado ou mock).
"""
import os

import httpx

MODEL = "xiaomi/mimo-v2.6-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_S = 15

SYSTEM = (
    "Você é um copiloto da agricultura familiar brasileira. "
    "Fale simples, em PT-BR, direto ao ponto. "
    "Responda usando SÓ o contexto de dados fornecido, sem inventar produtos, janelas ou prazos. "
    "Cite a fonte indicada no contexto. "
    "Não receite agrotóxico nem dose sem orientar a buscar um responsável técnico."
)


def gerar_resposta(intencao, mensagem: str, contexto_dados: str) -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    if not contexto_dados or not contexto_dados.strip():
        return None
    try:
        resp = httpx.post(
            URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"intenção: {intencao}\n"
                            f"pergunta do produtor: {mensagem}\n"
                            f"contexto (dados reais): {contexto_dados}"
                        ),
                    },
                ],
            },
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        texto = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        texto = (texto or "").strip()
        return texto or None
    except Exception:
        return None
