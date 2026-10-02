"""Rota /api/alertas — leitura e simulação com MongoDB + fallback mock."""
from datetime import datetime, timezone
from fastapi import APIRouter
from ..schemas.alertas import SimularAlertaRequest
from ..mock import MOCK_ALERTA_GEADA
from ..db import get_db

router = APIRouter(prefix="/api", tags=["Alertas"])

_MENSAGENS = {
    "geada": "Geada prevista para os próximos 3 dias. Sua lavoura está em risco — cubra as mudas sensíveis.",
    "granizo": "Risco de granizo nas próximas 24h. Verifique cobertura de proteção das culturas.",
    "seca": "Período de seca prolongada. Monitore a umidade do solo e avalie irrigação suplementar.",
    "chuva_forte": "Chuva forte prevista (>75 mm). Risco de erosão e encharcamento — verifique drenagem.",
    "vento_forte": "Ventos acima de 60 km/h esperados. Avalie suporte em estacas e telas de proteção.",
}


def _col(db):
    try:
        return db["alertas"] if db is not None else None
    except Exception:
        return None


@router.get("/alertas/{id}")
def listar_alertas(id: str):
    """Lista alertas ativos do produtor. Tenta Mongo; fallback para mock."""
    col = _col(get_db())
    if col is not None:
        try:
            docs = list(col.find({"produtor_id": id}, {"_id": 0}).sort("enviado_em", -1).limit(10))
            if docs:
                return {"alertas": docs}
        except Exception:
            pass
    return {"alertas": [MOCK_ALERTA_GEADA]}


@router.post("/alertas/simular")
def simular_alerta(req: SimularAlertaRequest):
    """Cria alerta simulado — persiste no Mongo se disponível."""
    import uuid

    agora = datetime.now(timezone.utc).isoformat()
    alerta = {
        "id": f"alerta-{req.tipo}-{uuid.uuid4().hex[:6]}",
        "produtor_id": req.produtor_id,
        "tipo": req.tipo,
        "severidade": "alta",
        "mensagem": _MENSAGENS.get(
            req.tipo,
            f"Alerta simulado de {req.tipo} para sua propriedade. Risco detectado para suas culturas.",
        ),
        "fonte": "ZARC + INMET",
        "enviado_em": agora,
        "lido": False,
    }

    col = _col(get_db())
    if col is not None:
        try:
            col.insert_one(dict(alerta))
        except Exception:
            pass

    return {"ok": True, "alerta": {k: v for k, v in alerta.items() if k != "produtor_id"}}
