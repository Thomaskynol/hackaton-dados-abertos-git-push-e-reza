from fastapi import APIRouter
from ..schemas.produtor import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api", tags=["Onboarding"])


@router.post("/onboarding")
def responder_onboarding(req: OnboardingRequest):
    if req.etapa == 1:
        return {
            "proximo_passo": 2,
            "pergunta": f"Prazer, {req.resposta}! Me manda sua cidade e estado (ex: Araraquara - SP).",
            "perfil_parcial": {"nome": req.resposta},
        }
    elif req.etapa == 2:
        return {
            "proximo_passo": 3,
            "pergunta": "Show! Quais culturas você planta na sua propriedade? (ex: uva, tomate, feijão)",
            "perfil_parcial": {"municipio": req.resposta},
        }
    elif req.etapa == 3:
        return {
            "proximo_passo": 4,
            "pergunta": "Qual o tamanho aproximado da sua área plantada em hectares?",
            "perfil_parcial": {"culturas": req.resposta},
        }
    else:
        return {
            "proximo_passo": 5,
            "pergunta": "Cadastro concluído! Agora você receberá alertas climáticos e recomendações do ZARC e Agrofit direto por aqui.",
            "perfil_parcial": {"status": "concluido"},
        }
