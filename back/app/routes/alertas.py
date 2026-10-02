from datetime import datetime, timezone
from fastapi import APIRouter
from ..schemas.alertas import (
    SimularAlertaRequest,
    SimularAlertaResponse,
    AlertasListResponse,
)
from ..mock import MOCK_ALERTA_GEADA

router = APIRouter(prefix="/api", tags=["Alertas"])


@router.get(
    "/alertas/{id}",
    response_model=AlertasListResponse,
    summary="Listar alertas do produtor",
    description="Retorna a lista de alertas agroclimáticos ativos para o produtor.",
)
def listar_alertas(id: str):
    return {"alertas": [MOCK_ALERTA_GEADA]}


@router.post(
    "/alertas/simular",
    response_model=SimularAlertaResponse,
    summary="Simular alerta climático",
    description="Dispara manualmente a simulação de um alerta agroclimático (geada, seca, etc.).",
)
def simular_alerta(req: SimularAlertaRequest):
    return {
        "ok": True,
        "alerta": {
            "id": f"alerta-{req.tipo}-simulado",
            "tipo": req.tipo,
            "severidade": "alta",
            "mensagem": f"Alerta simulado de {req.tipo} para sua propriedade. Risco detectado para suas culturas.",
            "fonte": "ZARC + INMET",
            "enviado_em": datetime.now(timezone.utc).isoformat(),
            "lido": False,
        },
    }

