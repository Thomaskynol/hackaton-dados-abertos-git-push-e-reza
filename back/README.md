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
