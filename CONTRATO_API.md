# Contrato de API — MVP Agricultura Familiar

Este contrato define a interface de comunicação entre o Frontend (NextJS) e o Backend (FastAPI) para o MVP da Hackathon.

---

## 1. Endpoints do MVP

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/chat` | Envia mensagem do produtor e recebe resposta contextualizada |
| `POST` | `/api/onboarding` | Conversa guiada para cadastro do produtor |
| `GET` | `/api/produtor/{id}` | Retorna o perfil completo do produtor |
| `POST` | `/api/produtor` | Cria ou atualiza o perfil do produtor |
| `GET` | `/api/alertas/{id}` | Lista alertas ativos para o produtor |
| `POST` | `/api/alertas/simular` | Dispara/simula um alerta (útil para pitch/demo) |
| `GET` | `/api/health` | Healthcheck da API |

---

## 2. Detalhamento dos Endpoints

### 2.1 POST /api/chat

Envia uma mensagem de texto e retorna a resposta com intenção identificada, dados estruturados e fontes abertas consultadas.

**Request Body:**
```json
{
  "produtor_id": "abc123",
  "mensagem": "minha uva tá com míldio"
}
```

**Response 200 (Sucesso):**
```json
{
  "resposta": "Antônio, para míldio em uva, os produtos registrados são:\n• Produto X (classe II)\n• Produto Z (ORGÂNICO)",
  "intencao": "PRAGA",
  "fonte": "Agrofit/MAPA",
  "data_extracao": "2026-10-02",
  "dados": {
    "cultura": "uva",
    "praga": "mildio",
    "produtos": [
      { "nome": "Produto X", "classe": "II", "organico": false },
      { "nome": "Produto Z", "classe": "IV", "organico": true }
    ]
  }
}
```

**Response 200 (Fallback / Dúvida):**
```json
{
  "erro": "NAO_ENTENDI",
  "mensagem": "Não consegui entender. Pode reformular?",
  "sugestoes": [
    "Quando planto feijão?",
    "Minha uva está com míldio",
    "Vai gear?"
  ]
}
```

---

### 2.2 POST /api/onboarding

Conversa passo a passo para cadastrar as informações do produtor rural.

**Request Body:**
```json
{
  "telefone": "+5519999999999",
  "etapa": 1,
  "resposta": "Antônio"
}
```

**Response 200:**
```json
{
  "proximo_passo": 2,
  "pergunta": "Prazer, Antônio! Me manda sua cidade.",
  "perfil_parcial": {
    "nome": "Antônio"
  }
}
```

---

### 2.3 GET /api/produtor/{id}

Retorna as características da propriedade, lavouras e preferências do produtor.

**Response 200:**
```json
{
  "id": "abc123",
  "nome": "Antônio",
  "telefone": "+5519999999999",
  "codigo_ibge": "3503307",
  "municipio": "Araraquara",
  "uf": "SP",
  "lavouras": [
    { "cultura": "uva", "area_ha": 5, "solo": 1, "irrigacao": false },
    { "cultura": "tomate", "area_ha": 3, "solo": 1, "irrigacao": false }
  ],
  "preferencias": {
    "notificacoes": true,
    "horario": "06:00"
  },
  "criado_em": "2026-10-02T10:00:00Z"
}
```

---

### 2.4 POST /api/produtor

Cria ou atualiza o perfil do produtor.

**Request Body:**
```json
{
  "nome": "Antônio",
  "telefone": "+5519999999999",
  "codigo_ibge": "3503307",
  "municipio": "Araraquara",
  "uf": "SP",
  "lavouras": [
    { "cultura": "uva", "area_ha": 5, "solo": 1, "irrigacao": false }
  ],
  "preferencias": {
    "notificacoes": true,
    "horario": "06:00"
  }
}
```

**Response 200:**
```json
{
  "id": "abc123",
  "mensagem": "Perfil cadastrado com sucesso",
  "ok": true
}
```

---

### 2.5 GET /api/alertas/{id}

Retorna a lista de alertas agroclimáticos ativos para a propriedade do produtor.

**Response 200:**
```json
{
  "alertas": [
    {
      "id": "alerta1",
      "tipo": "geada",
      "severidade": "alta",
      "mensagem": "Geada prevista para quinta (3 dias). Sua uva está em risco.",
      "fonte": "ZARC + INMET",
      "data_extracao": "2026-10-02",
      "enviado_em": "2026-10-02T06:00:00Z",
      "lido": false
    }
  ]
}
```

---

### 2.6 POST /api/alertas/simular

Dispara manualmente um alerta climático simulado para demonstração e pitch.

**Request Body:**
```json
{
  "produtor_id": "abc123",
  "tipo": "geada"
}
```

**Response 200:**
```json
{
  "ok": true,
  "alerta": {
    "id": "alerta2",
    "tipo": "geada",
    "mensagem": "Geada prevista para quinta (3 dias). Sua uva está em risco.",
    "fonte": "ZARC + INMET",
    "enviado_em": "2026-10-02T14:32:00Z"
  }
}
```

---

### 2.7 GET /api/health

Healthcheck da aplicação.

**Response 200:**
```json
{
  "status": "ok"
}
```

---

## 3. Enum de Intenções

```typescript
type Intencao =
  | "PLANEJAMENTO"   // ex: "quando planto feijão?"
  | "PRAGA"          // ex: "minha planta está com míldio"
  | "CLIMA"          // ex: "vai gear essa semana?"
  | "VENDA"          // ex: "como vendo minha colheita?"
  | "PERFIL"         // ex: "meu perfil / minhas lavouras"
  | "SAUDACAO"       // ex: "oi / bom dia"
  | "NAO_ENTENDI";   // fallback
```
