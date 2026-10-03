"""Camada de resposta via OpenRouter (modelo xiaomi/mimo-v2-flash).

RAG simples: o chamador monta `contexto_dados` em texto a partir dos
dados reais do Mongo; o LLM só reescreve a resposta com esse contexto.
Sem chave, falha de rede/timeout ou resposta inválida → None (nunca raise),
e o chamador cai no fluxo atual (real formatado ou mock).
"""
import json
import os

import httpx

MODEL = "xiaomi/mimo-v2.6-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_S = 60

SYSTEM = (
    "Você é um copiloto da agricultura familiar brasileira. "
    "Fale PT-BR simples, frases curtas, direto ao ponto. "
    "Responda usando SÓ o contexto de dados fornecido, sem inventar produtos, janelas ou prazos. "
    "REGRAS DURAS DE LINGUAGEM (corpo da resposta): "
    "proibido jargão cru — nunca escreva dec/década/ad1/sequeiro/grupo_X/código cru; "
    "traduza: década->período do mês (ex: 'década 27' vira 'fim de setembro'), "
    "ad1->tipo de solo simples, sequeiro->sem irrigação; "
    "proibido número de Portaria no corpo (use só no rodapé de fontes); "
    "siglas sempre expandidas na primeira vez (ex: ZARC = zoneamento agrícola...); "
    "no máximo 2-3 números no corpo; "
    "termine com UMA pergunta de acompanhamento, no máximo. "
    "Cite a fonte curta no fim (ex: Fonte: ZARC soja ...). "
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


def _payload(intencao, mensagem: str, contexto_dados: str, stream: bool) -> dict:
    body = {
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
    }
    if stream:
        body["stream"] = True
    return body


def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def gerar_resposta_stream(intencao, mensagem: str, contexto_dados: str):
    """Yielda chunks str via SSE OpenRouter. Sem chave/contexto/falha -> nada. Nunca raise."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return
    if not contexto_dados or not contexto_dados.strip():
        return
    try:
        with httpx.stream(
            "POST", URL, headers=_headers(key),
            json=_payload(intencao, mensagem, contexto_dados, True),
            timeout=TIMEOUT_S,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    try:
                        line = line.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except Exception:
                    continue
                try:
                    chunk = (data.get("choices") or [{}])[0].get("delta", {}).get("content", "")
                except Exception:
                    chunk = ""
                if chunk:
                    yield chunk
    except Exception:
        return


# --- Agente com tool-calling (OpenAI-compatible via OpenRouter) ---

try:
    from .tools import TOOLS_SCHEMA, dispatch
except Exception:
    try:
        from app.tools import TOOLS_SCHEMA, dispatch  # type: ignore
    except Exception:
        TOOLS_SCHEMA = []
        dispatch = None

SYSTEM_AGENT = (
    "Você é um copiloto da agricultura familiar brasileira. "
    "Fale PT-BR simples, frases curtas, direto ao ponto. "
    "ANTES de responder qualquer pergunta sobre plantio, praga, clima, risco, area, municipio, "
    "venda, preco ou cotacao: "
    "chame as ferramentas (buscar_janelas_zarc, buscar_produtos_agrofit, buscar_risco_psr, "
    "buscar_area_sigef, buscar_irrigacao_ana, buscar_municipio, buscar_preco_conab) para obter dados reais. "
    "Para venda/preco use buscar_preco_conab e NUNCA recomende 'vender agora'; "
    "explique o piso e oriente comparar com o preco do dia (Cepea) e os canais PAA/PNAE. "
    "Nunca responda de memória nem invente valores. "
    "Se faltar cultura ou municipio na pergunta, use cultura/objetivo detectado na mensagem, "
    "municipio Araraquara/SP 3503208 como padrão, e CHAME a ferramenta mesmo assim. "
    "Saudação simples (oi/bom dia) pode responder direto sem ferramenta. "
    "Se os dados vierem vazios, diga o que falta e peça a informação necessária. "
    "REGRAS DURAS DE LINGUAGEM (corpo da resposta): "
    "proibido jargão cru — nunca escreva dec/década/ad1/sequeiro/grupo_X/código cru; "
    "traduza: década->período do mês (ex: 'década 27' vira 'fim de setembro'), "
    "ad1->tipo de solo simples, sequeiro->sem irrigação; "
    "proibido número de Portaria no corpo (use só no rodapé de fontes); "
    "siglas sempre expandidas na primeira vez (ex: ZARC = zoneamento agrícola...); "
    "no máximo 2-3 números no corpo; "
    "termine com UMA pergunta de acompanhamento, no máximo. "
    "Cite a fonte curta no fim (ex: Fonte: ZARC soja ...). "
    "Não receite agrotóxico nem dose sem orientar a buscar um responsável técnico."
)

_MAX_ROUNDS = 3
_RESUMO_TXT = 2000


def _ctx_usuario(mensagem: str, produtor_id=None, contexto_extra=None) -> str:
    txt = f"pergunta do produtor: {mensagem}"
    if produtor_id:
        txt += f"\nprodutor_id: {produtor_id}"
    extra = str(contexto_extra or "").strip()
    if extra:
        txt += f"\n{extra[:2000]}"
    return txt


def _first_choice(data):
    try:
        choices = data.get("choices") or []
        return choices[0] if choices else None
    except Exception:
        return None


def _parse_calls(tool_calls):
    out = []
    for c in tool_calls or []:
        try:
            fn = (c or {}).get("function") or {}
            name = fn.get("name")
            if not name:
                continue
            raw = fn.get("arguments")
            if isinstance(raw, str):
                try:
                    args = json.loads(raw or "{}")
                except Exception:
                    args = {}
                raw_s = raw
            elif isinstance(raw, dict):
                args = raw
                raw_s = json.dumps(raw, ensure_ascii=False)
            else:
                args, raw_s = {}, "{}"
            if not isinstance(args, dict):
                args = {}
            out.append({"id": (c or {}).get("id") or f"call_{len(out)}",
                        "name": name, "args": args, "args_raw": raw_s})
        except Exception:
            continue
    return out


def _cap_obj(o):
    if isinstance(o, str):
        return o[:_RESUMO_TXT]
    if isinstance(o, list):
        return [_cap_obj(x) for x in o[:5]]
    if isinstance(o, dict):
        return {str(k)[:80]: _cap_obj(v) for k, v in list(o.items())[:30]}
    return o


def _seguro(obj):
    try:
        return _cap_obj(json.loads(json.dumps(obj, ensure_ascii=False, default=str)))
    except Exception:
        return {"erro": "resultado nao serializavel"}


def _post_tools(key: str, messages: list):
    resp = httpx.post(
        URL, headers=_headers(key),
        json={"model": MODEL, "messages": messages,
              "tools": TOOLS_SCHEMA, "tool_choice": "auto"},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()


def _tool_msgs(calls):
    return [{"id": c["id"], "type": "function",
             "function": {"name": c["name"], "arguments": c["args_raw"]}} for c in calls]


def _assistant_tool_msg(msg, calls):
    return {"role": "assistant", "content": msg.get("content"),
            "tool_calls": _tool_msgs(calls)}


def responder_com_tools(mensagem: str, db=None, produtor_id=None, max_rounds=3,
                        contexto_extra=None):
    """Loop agente sync. Retorna (texto|None, usadas). Nunca raise."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or not TOOLS_SCHEMA or dispatch is None:
        return None, []
    if not (mensagem or "").strip():
        return None, []
    try:
        rounds = max(1, min(_MAX_ROUNDS, int(max_rounds or _MAX_ROUNDS)))
    except Exception:
        rounds = _MAX_ROUNDS
    messages = [{"role": "system", "content": SYSTEM_AGENT},
                {"role": "user", "content": _ctx_usuario(mensagem, produtor_id, contexto_extra)}]
    usadas = []
    try:
        for _ in range(rounds):
            try:
                data = _post_tools(key, messages)
            except Exception:
                return None, usadas
            choice = _first_choice(data)
            if choice is None:
                return None, usadas
            msg = choice.get("message") or {}
            calls = _parse_calls(msg.get("tool_calls"))
            if calls:
                messages.append(_assistant_tool_msg(msg, calls))
                for c in calls:
                    try:
                        result = dispatch(db, c["name"], c["args"])
                    except Exception:
                        result = {"erro": f"falha em {c['name']}"}
                    res = _seguro(result)
                    usadas.append({"name": c["name"], "args": c["args"],
                                   "result_resumo": res})
                    messages.append({"role": "tool", "tool_call_id": c["id"],
                                     "content": json.dumps(res, ensure_ascii=False)})
                continue
            texto = (msg.get("content") or "").strip()
            return (texto or None), usadas
        try:
            resp = httpx.post(
                URL, headers=_headers(key),
                json={"model": MODEL, "messages": messages + [
                    {"role": "user", "content": "Responda agora em PT-BR com os dados coletados, citando as fontes."}]},
                timeout=TIMEOUT_S,
            )
            resp.raise_for_status()
            choice = _first_choice(resp.json())
            texto = ((choice or {}).get("message") or {}).get("content", "")
            return ((texto or "").strip() or None), usadas
        except Exception:
            return None, usadas
    except Exception:
        return None, usadas


def responder_com_tools_stream(mensagem: str, db=None, produtor_id=None, max_rounds=3,
                               contexto_extra=None):
    """Gera ("tool", {name, args}) por call executada, depois ("delta", chunk). Nunca raise."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or not TOOLS_SCHEMA or dispatch is None:
        return
    if not (mensagem or "").strip():
        return
    try:
        rounds = max(1, min(_MAX_ROUNDS, int(max_rounds or _MAX_ROUNDS)))
    except Exception:
        rounds = _MAX_ROUNDS
    messages = [{"role": "system", "content": SYSTEM_AGENT},
                {"role": "user", "content": _ctx_usuario(mensagem, produtor_id, contexto_extra)}]
    try:
        for _ in range(rounds):
            try:
                data = _post_tools(key, messages)
            except Exception:
                return
            choice = _first_choice(data)
            if choice is None:
                return
            msg = choice.get("message") or {}
            calls = _parse_calls(msg.get("tool_calls"))
            if calls:
                messages.append(_assistant_tool_msg(msg, calls))
                for c in calls:
                    yield ("tool", {"name": c["name"], "args": c["args"]})
                    try:
                        result = dispatch(db, c["name"], c["args"])
                    except Exception:
                        result = {"erro": f"falha em {c['name']}"}
                    res = _seguro(result)
                    messages.append({"role": "tool", "tool_call_id": c["id"],
                                     "content": json.dumps(res, ensure_ascii=False)})
                continue
            texto = (msg.get("content") or "").strip()
            if texto:
                yield ("delta", texto)
            return
        try:
            with httpx.stream(
                "POST", URL, headers=_headers(key),
                json={"model": MODEL, "messages": messages + [
                    {"role": "user", "content": "Responda agora em PT-BR com os dados coletados, citando as fontes."}],
                    "stream": True},
                timeout=TIMEOUT_S,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        try:
                            line = line.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        data = json.loads(payload)
                    except Exception:
                        continue
                    try:
                        chunk = (data.get("choices") or [{}])[0].get("delta", {}).get("content", "")
                    except Exception:
                        chunk = ""
                    if chunk:
                        yield ("delta", chunk)
        except Exception:
            return
    except Exception:
        return


# --- Análise comercial (consultor de venda) via OpenRouter ---

SYSTEM_COMERCIAL = (
    "Você é um consultor comercial da agricultura familiar brasileira. "
    "Fale PT-BR simples, acolhedor, frases curtas, como quem conversa com o Seu produtor. "
    "Explique o contexto de preço para AJUDAR A PLANEJAR a venda — NUNCA diga 'venda agora' "
    "nem 'espere para vender'; a decisão é do produtor. "
    "Use SÓ os números do contexto fornecido; nunca invente cotação. "
    "Se só houver o preço mínimo (piso PGPM), explique que ele é a rede de proteção e oriente "
    "comparar com o preço do dia no Cepea e com os canais (cooperativa, PAA, PNAE, feira). "
    "Destaque que PAA/PNAE costumam pagar prêmio sobre o mercado para a agricultura familiar. "
    "No máximo 2 números no corpo. Sem jargão. Termine com UMA sugestão prática de próximo passo. "
    "Cite a fonte curta no fim (ex: Fonte: CONAB/PGPM). "
    "Responda em 3 a 5 frases, no máximo."
)


def gerar_analise_comercial(contexto_dados: str) -> str | None:
    """Recomendação comercial curta via LLM. Sem chave/contexto/falha -> None."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or not (contexto_dados or "").strip():
        return None
    try:
        resp = httpx.post(
            URL, headers=_headers(key),
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_COMERCIAL},
                    {"role": "user", "content": contexto_dados},
                ],
            },
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        texto = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
        return (texto or "").strip() or None
    except Exception:
        return None
