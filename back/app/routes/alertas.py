from datetime import datetime, timezone
from fastapi import APIRouter
from ..schemas.alertas import SimularAlertaRequest
from ..mock import MOCK_ALERTA_GEADA

router = APIRouter(prefix="/api", tags=["Alertas"])


@router.get("/alertas/{id}")
def listar_alertas(id: str):
    return {"alertas": [MOCK_ALERTA_GEADA]}


@router.post("/alertas/simular")
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
