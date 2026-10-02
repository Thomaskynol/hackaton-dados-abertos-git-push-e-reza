from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class SessaoCreate(BaseModel):
    produtor_id: str
    titulo: Optional[str] = None
    uf: Optional[str] = None
    cod_ibge: Optional[str] = None


class SessaoOut(BaseModel):
    id: str
    produtor_id: str
    titulo: str
    uf: Optional[str] = None
    cod_ibge: Optional[str] = None
    criado_em: str
    atualizado_em: str


class MensagemOut(BaseModel):
    id: str
    sessao_id: str
    produtor_id: str
    autor: str
    texto: str
    intencao: Optional[str] = None
    fonte: Optional[str] = None
    dados: Optional[Dict[str, Any]] = None
    criado_em: str


class MemoriaOut(BaseModel):
    id: str
    produtor_id: str
    texto: str
    origem: str
    sessao_id: Optional[str] = None
    criado_em: str
