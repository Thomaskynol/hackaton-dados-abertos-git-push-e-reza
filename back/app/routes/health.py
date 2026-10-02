from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    summary="Health check da API",
    description="Retorna o status de integridade da API.",
)
def health_check():
    return {"status": "ok"}

