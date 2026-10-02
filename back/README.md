# Backend MVP — Agro Familiar (FastAPI)

Backend desenvolvido para a Hackathon de Dados Abertos para suporte a produtores da agricultura familiar.

## 🚀 Como executar o projeto

### 1. Criar e ativar o ambiente virtual (opcional, mas recomendado)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Rodar a aplicação
```bash
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em:
- **API Base:** [http://localhost:8000](http://localhost:8000)
- **Documentação Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Healthcheck:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 4. Rodar testes automatizados do contrato
```bash
pytest tests/test_contrato.py -v
```

## 🪟 Executar sem Docker (Windows)

Um script só instala o que falta (MongoDB, `mongosh`, `mongorestore`, venv, `npm install`), popula o banco e sobe API + front:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1
```

- Idempotente: pode rodar de novo sem quebrar nada. Requer `winget` disponível e, para a primeira instalação, PowerShell como Administrador.
- O dump `seed\agropilot.gz` (release privada) é baixado via `gh release download`; se o `gh` faltar, o script imprime o link para download manual. O `mongorestore --drop` só roda se o banco `agropilot` estiver vazio.
- URLs: **front** http://localhost:3000 · **Swagger** http://localhost:8000/docs · **Health** http://localhost:8000/api/health
- Logs em `%TEMP%\agropilot-*.log` e PIDs em `%TEMP%\agropilot-*.pid`.
- Parâmetros: `-Setup` (só instala e popula), `-Seed` (força o seed), `-Status` (o que está de pé), `-Stop` (derruba API e front).
- Sem executar o script: `uvicorn app.main:app --reload --port 8000` a partir de `back\`, com o serviço Windows `MongoDB` rodando.

O caminho com Docker continua disponível como alternativa (`docker compose up`), conforme o `docker-compose.yml`.
