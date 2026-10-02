import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .routes import health, chat, onboarding, produtor, alertas, precos, regiao

load_dotenv()

app = FastAPI(
    title="API Agro Familiar MVP",
    description="Backend para suporte inteligente a produtores da agricultura familiar usando dados abertos.",
    version="1.0.0",
)

# Configuração de CORS para permitir que o Frontend (NextJS) consuma a API sem bloqueios
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Rotas
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(onboarding.router)
app.include_router(produtor.router)
app.include_router(alertas.router)
app.include_router(precos.router)
app.include_router(regiao.router)


@app.get("/")
def root():
    return {
        "mensagem": "API Agro Familiar em execução",
        "docs": "/docs",
        "health": "/api/health",
    }
