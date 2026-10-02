# Arquitetura Front + Back (sem banco ainda)

Boa estratégia. Se o front e o back não travarem um no outro, vocês ganham tempo para a correlação depois. O segredo é: **definir o contrato de API antes de qualquer código** e o front trabalhar com **mock** desde o primeiro minuto.

Abaixo, a arquitetura para os 2 devs (1 front + 1 back), com contrato, estrutura de pastas, mock e fluxo.

---

## 1. Princípio: contrato primeiro, código depois

```
┌──────────────────────────────────────────────────────────────┐
│  CONTRATO DE API (definido na H0, não muda)                  │
│  → JSON de request/response de cada endpoint                 │
│  → É o que permite front e back trabalharem em paralelo     │
└──────────────────────────┬───────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌───────────────────┐                 ┌───────────────────┐
│  FRONT (NextJS)   │                 │  BACK (FastAPI)   │
│                   │                 │                   │
│  Consome o        │                 │  Implementa o     │
│  contrato com     │                 │  contrato com     │
│  dados mockados   │                 │  dados mockados   │
│                   │                 │  (depois troca    │
│  Não espera o     │                 │  por MongoDB)     │
│  back ficar pronto│                 │                   │
└───────────────────┘                 └───────────────────┘
```

**Regra de ouro:** o front nunca espera o back. Ele consome o contrato com mock. O back nunca espera o banco. Ele responde com mock. Quando os dois estiverem prontos, é só trocar o mock pelo real.

---

## 2. Contrato de API (o documento mais importante)

Este é o documento que os 2 devs precisam concordar **antes de escrever qualquer linha**. Salve como `CONTRATO_API.md` no repositório.

### 2.1 Endpoints do MVP

```
POST   /api/chat                 → envia mensagem, recebe resposta
POST   /api/onboarding           → conversa guiada de cadastro
GET    /api/produtor/{id}        → perfil do produtor
POST   /api/produtor             → cria/atualiza perfil
GET    /api/alertas/{id}         → alertas do produtor
POST   /api/alertas/simular      → força alerta (para o pitch)
GET    /api/health               → healthcheck
```

### 2.2 Contrato detalhado

#### POST /api/chat

**Request:**
```json
{
  "produtor_id": "abc123",
  "mensagem": "minha uva tá com míldio"
}
```

**Response (200):**
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

**Response (erro):**
```json
{
  "erro": "NAO_ENTENDI",
  "mensagem": "Não consegui entender. Pode reformular?",
  "sugestoes": ["Quando planto feijão?", "Minha uva está com míldio", "Vai gear?"]
}
```

#### POST /api/onboarding

**Request:**
```json
{
  "telefone": "+5519999999999",
  "etapa": 1,
  "resposta": "Antônio"
}
```

**Response (200):**
```json
{
  "proximo_passo": 2,
  "pergunta": "Prazer, Antônio! Me manda sua cidade.",
  "perfil_parcial": {
    "nome": "Antônio"
  }
}
```

#### GET /api/produtor/{id}

**Response (200):**
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

#### GET /api/alertas/{id}

**Response (200):**
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

#### POST /api/alertas/simular

**Request:**
```json
{
  "produtor_id": "abc123",
  "tipo": "geada"
}
```

**Response (200):**
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

### 2.3 Enum de intenções (compartilhado)

```typescript
// front: src/types/intencoes.ts
// back:  app/schemas/intencoes.py

type Intencao =
  | "PLANEJAMENTO"   // "quando planto X?"
  | "PRAGA"          // "minha planta está com X"
  | "CLIMA"          // "vai gear?"
  | "VENDA"          // "como vendo?"
  | "PERFIL"         // "meu perfil"
  | "SAUDACAO"       // "oi"
  | "NAO_ENTENDI";   // fallback
```

**Definir isso na H0 evita retrabalho.**

---

## 3. Mock de dados (para o front não travar)

O back cria um arquivo `mock.py` com respostas fixas. O front consome esse mock via **MSW (Mock Service Worker)** ou um **JSON estático**.

### 3.1 Mock do back (Python)

```python
# back/app/mock.py
MOCK_CHAT_PRAGA = {
    "resposta": "Antônio, para míldio em uva, os produtos registrados são:\n• Produto X (classe II)\n• Produto Z (ORGÂNICO)",
    "intencao": "PRAGA",
    "fonte": "Agrofit/MAPA",
    "data_extracao": "2026-10-02",
    "dados": {
        "cultura": "uva",
        "praga": "mildio",
        "produtos": [
            {"nome": "Produto X", "classe": "II", "organico": False},
            {"nome": "Produto Z", "classe": "IV", "organico": True},
        ],
    },
}

MOCK_CHAT_PLANEJAMENTO = {
    "resposta": "Antônio, para feijão em Araraquara (solo 1, sequeiro):\n• Melhor janela: dec 29-32 (risco 20%)\n• Cultivares: BRS Estilo, BRS Pérola\n• Semente local: BRS Estilo (30 km)",
    "intencao": "PLANEJAMENTO",
    "fonte": "ZARC 2025/26 + SIGEF",
    "data_extracao": "2026-10-02",
    "dados": {
        "cultura": "feijao",
        "janelas": [{"dec": 29, "risco": 20}, {"dec": 30, "risco": 20}],
        "cultivares": ["BRS Estilo", "BRS Pérola"],
    },
}

MOCK_ALERTA_GEADA = {
    "id": "alerta1",
    "tipo": "geada",
    "severidade": "alta",
    "mensagem": "Geada prevista para quinta (3 dias). Sua uva está em risco.",
    "fonte": "ZARC + INMET",
    "data_extracao": "2026-10-02",
    "enviado_em": "2026-10-02T06:00:00Z",
    "lido": False,
}
```

### 3.2 Mock do front (MSW)

```typescript
// front/src/mocks/handlers.ts
import { http, HttpResponse } from 'msw'
import { MOCK_CHAT_PRAGA, MOCK_CHAT_PLANEJAMENTO } from './fixtures'

export const handlers = [
  http.post('/api/chat', async ({ request }) => {
    const body = await request.json()
    const msg = body.mensagem.toLowerCase()

    if (msg.includes('míldio') || msg.includes('praga')) {
      return HttpResponse.json(MOCK_CHAT_PRAGA)
    }
    if (msg.includes('plantar') || msg.includes('plantio')) {
      return HttpResponse.json(MOCK_CHAT_PLANEJAMENTO)
    }
    return HttpResponse.json({
      erro: 'NAO_ENTENDI',
      mensagem: 'Não consegui entender. Pode reformular?',
    })
  }),

  http.get('/api/produtor/:id', () => {
    return HttpResponse.json(MOCK_PRODUTOR)
  }),

  http.get('/api/alertas/:id', () => {
    return HttpResponse.json({ alertas: [MOCK_ALERTA_GEADA] })
  }),
]
```

**Vantagem:** o front roda 100% sem back. Quando o back ficar pronto, é só desligar o MSW.

---

## 4. Estrutura de pastas

### 4.1 Front (NextJS)

```
front/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # chat
│   │   ├── onboarding/
│   │   │   └── page.tsx            # cadastro guiado
│   │   └── perfil/
│   │       └── page.tsx            # perfil do produtor
│   ├── components/
│   │   ├── ChatWindow.tsx          # janela de mensagens
│   │   ├── ChatMessage.tsx         # bolha de mensagem
│   │   ├── ChatInput.tsx           # campo de texto
│   │   ├── AlertaCard.tsx          # card de alerta
│   │   ├── PerfilCard.tsx          # card de perfil
│   │   └── FonteBadge.tsx          # badge "Fonte: X"
│   ├── hooks/
│   │   ├── useChat.ts              # hook de chat
│   │   ├── useProdutor.ts          # hook de perfil
│   │   └── useAlertas.ts           # hook de alertas
│   ├── services/
│   │   └── api.ts                  # cliente HTTP (axios/fetch)
│   ├── types/
│   │   ├── api.ts                  # tipos do contrato
│   │   └── intencoes.ts            # enum de intenções
│   ├── mocks/
│   │   ├── handlers.ts             # MSW handlers
│   │   ├── fixtures.ts             # dados mockados
│   │   └── browser.ts              # setup do MSW
│   └── styles/
│       └── globals.css
├── public/
├── next.config.js
├── package.json
└── tsconfig.json
```

### 4.2 Back (FastAPI)

```
back/
├── app/
│   ├── main.py                     # FastAPI app
│   ├── routes/
│   │   ├── chat.py                 # POST /api/chat
│   │   ├── onboarding.py           # POST /api/onboarding
│   │   ├── produtor.py             # GET/POST /api/produtor
│   │   ├── alertas.py              # GET /api/alertas
│   │   └── health.py               # GET /api/health
│   ├── schemas/
│   │   ├── chat.py                 # Pydantic models
│   │   ├── produtor.py
│   │   ├── alertas.py
│   │   └── intencoes.py            # enum de intenções
│   ├── core/
│   │   ├── router_intencao.py      # classifica intenção
│   │   ├── templates.py            # respostas template
│   │   ├── llm.py                  # tradução (opcional)
│   │   └── scheduler.py            # notificações proativas
│   ├── data/
│   │   ├── zarc.py                 # (mock por enquanto)
│   │   ├── agrofit.py              # (mock por enquanto)
│   │   ├── sisser.py               # (mock por enquanto)
│   │   └── atlas.py                # (mock por enquanto)
│   ├── db/
│   │   ├── database.py             # conexão (mock por enquanto)
│   │   └── repositories.py         # queries (mock por enquanto)
│   └── mock.py                     # dados mockados
├── tests/
│   └── test_contrato.py            # testa o contrato
├── requirements.txt
└── README.md
```

---

## 5. Fluxo de comunicação

```
┌──────────────────────────────────────────────────────────────┐
│  USUÁRIO                                                     │
│  digita "minha uva tá com míldio"                            │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  FRONT (NextJS)                                              │
│  • ChatInput captura texto                                   │
│  • useChat envia POST /api/chat                              │
│  • Aguarda resposta                                          │
│  • ChatMessage renderiza                                     │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  BACK (FastAPI)                                              │
│  • routes/chat.py recebe                                     │
│  • router_intencao.py classifica → PRAGA                     │
│  • data/agrofit.py busca produtos (mock)                     │
│  • templates.py monta resposta                               │
│  • llm.py traduz (opcional)                                  │
│  • Acrescenta fonte + data                                   │
│  • Devolve JSON                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ JSON
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  FRONT (NextJS)                                              │
│  • Renderiza resposta                                        │
│  • Mostra badge "Fonte: Agrofit/MAPA"                        │
│  • Mostra data de extração                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Stack e decisões fechadas

### 6.1 Front

| Item | Tecnologia | Justificativa |
|---|---|---|
| Framework | NextJS 14 (App Router) | Padrão, SSR, fácil deploy |
| Linguagem | TypeScript | Contrato tipado |
| Estilo | Tailwind CSS | Rápido de montar |
| Estado | React Query (TanStack) | Cache e chamadas de API |
| HTTP | fetch nativo ou axios | Simples |
| Mock | MSW | Front não depende do back |
| Ícones | lucide-react | Leve |
| Deploy | Vercel | Zero config |

### 6.2 Back

| Item | Tecnologia | Justificativa |
|---|---|---|
| Framework | FastAPI | Rápido, async, tipado |
| Linguagem | Python 3.11+ | Ecossistema de dados |
| Validação | Pydantic | Contrato tipado |
| CORS | fastapi.middleware.cors | Permitir front |
| Scheduler | APScheduler | Notificações proativas |
| LLM | Gemini free / Groq / Ollama | Sem custo |
| Deploy | Render / Railway / Fly.io | Free tier |

### 6.3 Decisões críticas

| Decisão | Escolha | Por quê |
|---|---|---|
| Contrato antes do código | Sim | Permite paralelismo |
| Mock no front | MSW | Front não espera back |
| Mock no back | `mock.py` | Back não espera banco |
| LLM no back | Só tradução | Não decide, só traduz |
| Tipagem | TypeScript + Pydantic | Contrato consistente |
| CORS | Liberado em dev | Facilita integração |
| Variáveis de ambiente | `.env` | API keys não vão pro Git |

---

## 7. O que cada dev entrega

### Dev Front (Pessoa 1)

**H0-2:**
- Setup NextJS + Tailwind + MSW
- Tipos do contrato (`types/api.ts`)
- Componentes: `ChatWindow`, `ChatMessage`, `ChatInput`
- Mock do MSW funcionando

**H2-6:**
- Tela de chat funcional com mock
- Tela de onboarding
- Tela de perfil
- Badge de fonte

**H6-10:**
- Integração com back real (trocar MSW por API)
- Polir UI
- Testar fluxos

**Entregável:** front rodando, consumindo o back, com demo navegável.

### Dev Back (Pessoa 2)

**H0-2:**
- Setup FastAPI + Pydantic
- Schemas do contrato (`schemas/`)
- Endpoints stub retornando mock
- CORS liberado

**H2-6:**
- `router_intencao.py` (regras)
- `templates.py` (respostas)
- `mock.py` (dados mockados)
- Endpoints funcionando com mock

**H6-10:**
- Integração com LLM (opcional)
- Scheduler de alertas
- Testes de contrato

**Entregável:** back rodando, respondendo o contrato, com mock. Pronto para trocar por MongoDB depois.

---

## 8. Como trabalhar em paralelo sem bloqueio

### 8.1 Na H0

1. **Definir o contrato** juntos (30 min).
2. **Criar o repositório** com `front/` e `back/`.
3. **Criar o `CONTRATO_API.md`** na raiz.
4. **Cada um faz seu setup** e começa a codar.

### 8.2 Durante o desenvolvimento

- **Front:** usa MSW, não precisa do back.
- **Back:** usa mock, não precisa do banco.
- **Comunicação:** se o contrato mudar, avisar imediatamente.

### 8.3 Integração (H6)

1. Back sobe em `localhost:8000`.
2. Front aponta para `http://localhost:8000`.
3. Desligar MSW.
4. Testar os fluxos.

### 8.4 Regras de ouro

| Regra | Por quê |
|---|---|
| Contrato não muda sem avisar | Evita retrabalho |
| Front nunca espera back | MSW resolve |
| Back nunca espera banco | Mock resolve |
| Commits pequenos e frequentes | Facilita merge |
| Branch por feature | Evita conflito |
| Testar o contrato | Garante integração |

---

## 9. Variáveis de ambiente

### Front `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=true
```

### Back `.env`
```
LLM_PROVIDER=groq
GROQ_API_KEY=...
CORS_ORIGINS=http://localhost:3000
```

**Regra:** `.env` nunca vai pro Git. Só `.env.example`.

---

## 10. Roteiro de integração (H6)

```
1. Back sobe:
   $ cd back && uvicorn app.main:app --reload --port 8000

2. Testar health:
   $ curl http://localhost:8000/api/health
   → {"status": "ok"}

3. Front aponta para o back:
   .env.local → NEXT_PUBLIC_USE_MOCK=false

4. Testar chat:
   - Abrir http://localhost:3000
   - Digitar "minha uva tá com míldio"
   - Ver resposta do back

5. Se falhar:
   - Verificar CORS
   - Verificar contrato
   - Verificar logs do back
```

---

## 11. Resumo executivo

| Item | Decisão |
|---|---|
| **Contrato** | Definido na H0, não muda |
| **Front** | NextJS + TypeScript + Tailwind + MSW |
| **Back** | FastAPI + Pydantic + mock |
| **Comunicação** | HTTP JSON |
| **Paralelismo** | MSW (front) + mock.py (back) |
| **Integração** | H6, trocar mock por real |
| **Banco** | Depois, quando a correlação estiver pronta |
| **Entrega** | Front + back funcionando com mock |

**Frase-guia:** *"Contrato na H0, mock nos dois lados, integração na H6."*

---

Se quiser, eu detalho agora:
- **o `CONTRATO_API.md`** completo (com todos os endpoints e schemas);
- **o `router_intencao.py`** (classificador de intenções por regras);
- **o `api.ts`** (cliente HTTP do front);
- **o `handlers.ts`** (MSW completo);
- **o `main.py`** (FastAPI com CORS e rotas).
