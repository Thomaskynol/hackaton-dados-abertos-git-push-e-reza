from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Lavoura(BaseModel):
    cultura: str
    area_ha: float
    solo: int = 1
    irrigacao: bool = False


class Preferencias(BaseModel):
    notificacoes: bool = True
    horario: str = "06:00"


class ProdutorCreate(BaseModel):
    nome: str
    telefone: str
    codigo_ibge: str
    municipio: str
    uf: str
    lavouras: List[Lavoura] = []
    preferencias: Optional[Preferencias] = None


class ProdutorResponse(BaseModel):
    id: str
    nome: str
    telefone: str
    codigo_ibge: str
    municipio: str
    uf: str
    lavouras: List[Lavoura]
    preferencias: Preferencias
    criado_em: str


class OnboardingRequest(BaseModel):
    telefone: str
    etapa: int
    resposta: str


class OnboardingResponse(BaseModel):
    proximo_passo: int
    pergunta: str
    perfil_parcial: Optional[Dict[str, Any]] = None
