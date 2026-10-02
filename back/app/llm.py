"""Camada de resposta via OpenRouter / Groq (modelo configurável por env).

RAG simples: o chamador monta `contexto_dados` em texto a partir dos
dados reais do Mongo; o LLM só reescreve a resposta com esse contexto.
Sem chave, falha de rede/timeout ou resposta inválida → None (nunca raise),
e o chamador cai no fluxo atual (real formatado ou mock).

Variáveis de ambiente (qualquer uma serve):
  OPENROUTER_API_KEY  → usa OpenRouter (https://openrouter.ai)
  GROQ_API_KEY        → usa Groq (https://api.groq.com)
"""
import json
import os

import httpx

# --- Configuração por provider ---
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama3-8b-8192"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_MODEL = "xiaomi/mimo-v2.6-flash"

TIMEOUT_S = 60


def _get_key() -> tuple[str | None, str, str]:
    """Retorna (api_key, url, model) para o provider disponível. None se nenhum."""
    groq = os.getenv("GROQ_API_KEY")
    if groq:
        return groq, _GROQ_URL, _GROQ_MODEL
    openrouter = os.getenv("OPENROUTER_API_KEY")
    if openrouter:
        return openrouter, _OPENROUTER_URL, _OPENROUTER_MODEL
    return None, _OPENROUTER_URL, _OPENROUTER_MODEL


# Aliases de compatibilidade (usados em tools.py e tests)
MODEL = _OPENROUTER_MODEL
URL = _OPENROUTER_URL

SYSTEM = (
    "Você é o AgroPilot, copiloto da agricultura familiar brasileira. "
    "Fale simples, em PT-BR, acolhedor e direto ao ponto. "
    "Responda usando SÓ o contexto de dados fornecido — ZARC, Agrofit, PSR, SIGEF, ANA. "
    "Não invente produtos, janelas, preços ou prazos. "
    "Cite sempre a fonte indicada no contexto. "
    "Não receite agrotóxico nem dose sem orientar a buscar um responsável técnico. "
    "Se não souber, diga honestamente e sugira onde o produtor pode buscar ajuda."
)

SYSTEM_AGENT = (
    "Você é o AgroPilot, copiloto da agricultura familiar brasileira com acesso a dados abertos oficiais: "
    "ZARC (janelas de plantio e riscos climáticos), Agrofit/MAPA (defensivos registrados), "
    "PSR/SISSER (seguro rural), SIGEF (sementes certificadas) e ANA (irrigação). "
    "Use as ferramentas disponíveis para buscar dados reais antes de responder. "
    "Sempre cite a fonte. Nunca invente dados. "
    "Responda em PT-BR, de forma simples e direta para pequenos produtores rurais."
)


def gerar_resposta(intencao, mensagem: str, contexto_dados: str) -> str | None:
    key, url, model = _get_key()
    if not key:
        return None
    if not contexto_dados or not contexto_dados.strip():
        return None
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
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
    """Yielda chunks str via SSE. Sem chave/contexto/falha -> nada. Nunca raise."""
    key, url, model = _get_key()
    if not key:
        return
    if not contexto_dados or not contexto_dados.strip():
        return
    try:
        with httpx.stream(
            "POST", url, headers=_headers(key),
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


_MAX_ROUNDS = 3
_RESUMO_TXT = 2000


def _ctx_usuario(mensagem: str, produtor_id=None) -> str:
    txt = f"pergunta do produtor: {mensagem}"
    if produtor_id:
        txt += f"\nprodutor_id: {produtor_id}"
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


def _post_tools(key: str, messages: list, url: str = None, model: str = None):
    resp = httpx.post(
        url or URL, headers=_headers(key),
        json={"model": model or MODEL, "messages": messages,
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


def responder_com_tools(mensagem: str, db=None, produtor_id=None, max_rounds=3):
    """Loop agente sync. Retorna (texto|None, usadas). Nunca raise."""
    key, url, model = _get_key()
    if not key or not TOOLS_SCHEMA or dispatch is None:
        return None, []
    if not (mensagem or "").strip():
        return None, []
    try:
        rounds = max(1, min(_MAX_ROUNDS, int(max_rounds or _MAX_ROUNDS)))
    except Exception:
        rounds = _MAX_ROUNDS
    messages = [{"role": "system", "content": SYSTEM_AGENT},
                {"role": "user", "content": _ctx_usuario(mensagem, produtor_id)}]
    usadas = []
    try:
        for _ in range(rounds):
            try:
                data = _post_tools(key, messages, url, model)
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


def responder_com_tools_stream(mensagem: str, db=None, produtor_id=None, max_rounds=3):
    """Gera ("tool", {name, args}) por call executada, depois ("delta", chunk). Nunca raise."""
    key, url, model = _get_key()
    if not key or not TOOLS_SCHEMA or dispatch is None:
        return
    if not (mensagem or "").strip():
        return
    try:
        rounds = max(1, min(_MAX_ROUNDS, int(max_rounds or _MAX_ROUNDS)))
    except Exception:
        rounds = _MAX_ROUNDS
    messages = [{"role": "system", "content": SYSTEM_AGENT},
                {"role": "user", "content": _ctx_usuario(mensagem, produtor_id)}]
    try:
        for _ in range(rounds):
            try:
                data = _post_tools(key, messages, url, model)
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
