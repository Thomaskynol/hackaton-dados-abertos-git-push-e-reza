from typing import List, Optional
from pydantic import BaseModel


class AlertaItem(BaseModel):
    id: str
    tipo: str
    severidade: Optional[str] = "media"
    mensagem: str
    fonte: str
    data_extracao: Optional[str] = None
    enviado_em: str
    lido: bool = False


class AlertasListResponse(BaseModel):
    alertas: List[AlertaItem]


class SimularAlertaRequest(BaseModel):
    produtor_id: str
    tipo: str


class SimularAlertaResponse(BaseModel):
    ok: bool = True
    alerta: AlertaItem
