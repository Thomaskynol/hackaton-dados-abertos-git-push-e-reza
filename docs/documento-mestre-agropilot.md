---
title: Documento Mestre — AgroPilot
type: concept
tags: [prototipo, hackaton, join, metodologia]
sources: [raw/transcripts/agropilot-documento-mestre-v3.md, raw/transcripts/agropilot-v4-arquitetura.md, raw/articles/relatorio-agricultura-familiar-dados-abertos.md]
created: 2026-10-02
updated: 2026-10-02
confidence: high
measured: 2026-10-02
---

# Documento Mestre — AgroPilot

**Safra sob Controle.** Stack: Next.js 14 + FastAPI + MongoDB + Open-Meteo.

Documento único de referência da equipe. Consolida o melhor de **quatro versões**
(v2 · v3 · v4 · Documento Mestre v3) com **todos os bugs de dados corrigidos** e
**todos os números medidos** em Araraquara.

**Origem de cada parte:** [[review-arquitetura-agropilot]] (v3) ·
[[review-arquitetura-v4]] (v4) · [[review-documento-mestre-v3]] (Mestre) ·
[[arquitetura-motor-correlacao]] (motor v4 + medições).

---

## 0. Sumário executivo

### O produto

Copiloto da safra. Conecta dados públicos agrícolas (MAPA, ANA/Embrapa), contexto
da propriedade, diário do produtor e IA para transformar informação em **próximo
passo no campo**.

**Diferencial inegociável: a safra tem memória.** Cada registro do produtor altera o
estado do sistema, e o sistema reage — atualizando plano, criando missão,
explicando a mudança.

### O que o MVP prova

1. Existe problema real: **dado público existe, decisão cotidiana não**
2. Dados abertos viram **evidência operacional**
3. IA tem função concreta: **linguagem, não decisão agronômica**
4. A solução é responsável: **fonte, data, limitação, LGPD**
5. O sistema **acompanha a safra** (estado persistente)
6. Existe caminho real para automação a partir da missão

### O que o MVP **não** é

❌ Chatbot agrícola genérico · ❌ Dashboard passivo · ❌ Score "90% pode plantar" ·
❌ Emissor de receita agronômica · ❌ Modelo de ML treinado em 24 h · ❌ Detector de
pragas com YOLO

⚠️ **A lista de exclusão é a parte mais defensável do documento.** O "score 90%
pode plantar" foi exatamente o bug que medi duas vezes: `risco=None` virava
`100 - 0 = 100` → status "aberta". Declarar a exclusão é ter aprendido com o erro.

### Escopo congelado

Pequenos e médios produtores de **grãos, sequeiro**. Culturas: **milho, soja,
feijão, arroz, trigo**.

---

## 1. Enquadramento na hackathon

| Critério | Peso | Como o MVP responde |
|---|---|---|
| Relevância e impacto social | **20** | produtor familiar + decisão + dado público |
| Uso e análise dos dados | 15 | 5 bases cruzadas com proveniência visível |
| Qualidade da solução | 15 | arquitetura modular, fallback, degradação graciosa |
| Inovação e criatividade | 15 | **safra com memória** + missão como ponte para robótica |
| Protótipo / demonstração | 15 | jornada vertical funcional ponta a ponta |
| Viabilidade e continuidade | 10 | sem hardware obrigatório, roadmap claro |
| Apresentação e comunicação | 10 | narrativa simples + demo ensaiada |

**Critério eliminatório:** ética, privacidade, uso responsável. O MVP é desenhado
para cumprir isso desde a ingestão (§9).

⚠️ **Impacto social é o maior peso isolado — o dobro de qualquer outro.** O número
mais forte para o pitch é [[dor-risco-e-perdas]].

---

## 2. Tese central

### O problema

O produtor não pergunta pelo dataset. Ele pergunta:

> "Posso plantar agora?" · "O que falta fazer?" · "O que aconteceu esta semana?" ·
> "Quanto eu já gastei?" · "Tenho risco importante para acompanhar?"

As bases públicas respondem partes disso. **O AgroPilot faz a ligação.**

### O ciclo do produto

```
DADOS PÚBLICOS
      ↓
CONTEXTO DA SAFRA
      ↓
EVIDÊNCIAS
      ↓
DECISÃO EXPLICADA
      ↓
AÇÃO
      ↓
DIÁRIO / LOG ──────→ MISSÃO DE CAMPO
      ↓                      ↓
NOVO CONTEXTO ←─────── AUTOMAÇÃO FUTURA
      ↓
NOVA DECISÃO / PLANO
```

⚠️ **A memória da safra é o diferencial real.** A v4 implementou proatividade como
"alerta de geada entra sempre, independente da intenção"; esta implementa como
"estado vivo da safra". **Esta é melhor**: não depende de previsão meteorológica
para ter próatividade, e a **missão de campo** é ponte concreta para robótica — que
é o tema do CEPIN.

---

## 3. Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind | controle visual, componente reutilizável, mobile-first |
| Backend | FastAPI (Python 3.11) | dados + tipagem Pydantic + OpenAPI automático |
| Banco | MongoDB 7 | documento com estado, evolução sem migration |
| Ingestão | Python + Pandas | roda offline, antes da demo |
| IA | LLM via API + `MockProvider` | linguagem natural, **fallback obrigatório** |
| Clima | Open-Meteo (REST, sem chave) | cache 6 h |
| Deploy dev | Docker Compose | mongo + backend + frontend em um comando |

**Fora:** PostgreSQL · microsserviços · filas · Kubernetes · autenticação complexa
(safra anônima via `safra_id` na URL) · Prisma/Mongoose · YOLO · robô real.

⚠️ **Open-Meteo é non-commercial** (< 10.000 calls/dia) e a organização **proibiu
contratar APIs sem autorização de todos os integrantes**. Plano gratuito OK.

---

## 4. Grafo e chaves

```
                    ┌──────────────────┐
                    │    municipios    │ ← HUB
                    │ cod_ibge unique  │
                    │ nome, uf, bioma  │
                    └────────┬─────────┘
        ┌──────────┬────────┼────────┬──────────┐
        ▼          ▼        ▼        ▼          ▼
    ┌───────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌──────┐
    │ zarc  │ │psr_agr │ │sigef │ │ana_atl │ │clima │
    │(fato) │ │ (fato) │ │(fato)│ │ (dim)  │ │(cache)│
    └───────┘ └────────┘ └──────┘ └────────┘ └──────┘
        └──────────────┴───────┴─────────┴────────┘
                              │
                     cod_ibge + cultura_canonica
                              │
                              ▼
                     ┌────────────────┐
                     │    agrofit     │ sem geo
                     │ cultura+praga  │
                     └────────────────┘
```

| Base | Chave | Como liga |
|---|---|---|
| [[zarc]] | `cod_ibge` + `cultura_canonica` + solo + ciclo + manejo | direto |
| [[sisser]] | `cod_ibge` + `cultura_canonica` | direto (`CD_GEOCMU`) |
| [[sigef]] | `nome_normalizado + uf → cod_ibge` | lookup na ingestão |
| [[ana-atlas-irrigacao]] | `cod_ibge` | direto (`Código` 9→7 díg.) |
| [[agrofit]] | `cultura_canonica` + `praga_cientifica` | **sem geo** |

**Medido:** ZARC × ANA = **100%** (5.570/5.570) · SISSER × ANA = **99,8%** ·
SIGEF cobre só **2.414 pares município+UF** de 5.570 — o join tem lacuna por
construção. Ver [[chave-de-join-ibge]].

---

## 5. Coleções

| Coleção | Papel | Grain |
|---|---|---|
| `municipios` | **hub** | `cod_ibge` |
| `zarc` | fato principal | geo × cultura × solo × ciclo × manejo |
| `psr_agregado` | histórico de sinistro | geo × cultura × **ano** |
| `sigef_mapa_agregado` | evidência de plantio | geo × cultura |
| `ana_atlas` | contexto hídrico | `cod_ibge` |
| `agrofit` | catálogo de defensivos | 1 registro |
| `cache_clima` | runtime | `cod_ibge` |
| `seasons` | **estado vivo da safra** | `safra_id` |
| `diary_entries` | diário do produtor | `season_id` + `occurred_at` |
| `tasks` | tarefas | `season_id` + status |
| `missions` | missões de campo | `season_id` + status |
| `evidence_snapshots` | histórico + TTL 30 d | `season_id` + `consulted_at` |
| `data_sources` | **metadados de proveniência** | fonte |
| `alertas` | proativos do worker | `chave_dedupe` |

### 5.1 `zarc`

```js
{
  // originais (auditoria)
  Nome_cultura: "Milho 1ª Safra", SafraIni: "2026", SafraFin: "2027",
  geocodigo: "3503208", UF: "SP", municipio: "Araraquara",
  Portaria: "Portaria SPA/MAPA nº .../2026",
  Cod_Solo: "3", Cod_Ciclo: "20", Cod_Outros_Manejos: "1", Cod_NM: "",

  // derivados
  cod_ibge: "3503208", cultura_canonica: "milho", ciclo_grupo: "grupo_i",
  solo_canonico: "argiloso", manejo_canonico: "sequeiro",
  nm: null,                    // ⭐ null quando Cod_NM == ""
  dec: { "28": 30, "29": 20, "30": 20, "31": 20, /* … */ "36": 20 },
  abertos: [28, 29, 30, 31, 32, 33, 34, 35, 36],   // multikey
  risco_min: 20, risco_max: 40,
  fora_janela_agora: true
}
db.zarc.createIndex({ cod_ibge: 1, manejo_canonico: 1, solo_canonico: 1,
                      cultura_canonica: 1, abertos: 1 })
```

⚠️ **`nm` fora do índice e do filtro.** Medido: vazio em **999.410 de 1.026.973**
linhas (97,3%), e presente **só para soja**. No índice, elimina 4 das 5 culturas.
NM é **contexto do produtor**, não chave de filtro.

⚠️ **`dec` nunca é 0 dentro da janela** — `0` significa *não indicado*. Filtrar
`min()` sem excluir zero devolve 0 para tudo. Ver [[semantica-zarc-zero]].

### 5.2 `psr_agregado` — e por que 2025 não entra

```js
{ cod_ibge: "3503208", uf: "SP", municipio: "Araraquara",
  cultura_canonica: "soja", ano: 2019,
  total_apolices: 15, total_sinistros: 2, taxa_sinistro_pct: 13.33,
  total_pago_reais: 22900.52,
  por_evento: [{ evento: "SECA", apolices: 2, valor: 22900.52 }],
  fonte_arquivo: "SISSER_PSR_2016_2024" }
db.psr_agregado.createIndex({ cod_ibge: 1, cultura_canonica: 1, ano: -1 })
```

⚠️ **Regra medida:** `sinistro = EVENTO_PREPONDERANTE ∉ {'', '-'} E
VALOR_INDENIZAÇÃO > 0`.

**O arquivo de 2025 não satisfaz nenhuma das duas.** `EVENTO_PREPONDERANTE` é `-` em
**46.137 de 46.137** linhas e a soma de `VALOR_INDENIZAÇÃO` é **R$ 0,00**. Ingerir
2025 produziria `taxa_sinistro_pct: 0.0` em todo o país — **falso**, não "baixo".

### 5.3 `agrofit` — 280.159 docs, sem explosão

**0 de 280.159** registros têm `;`, `,` ou `/` em `CULTURA`. **Não explode por `;`.**

```js
{ nr_registro: "35523", marca_comercial: "KBR-829M1-02",
  ingrediente_ativo: "Heterorhabditis bacteriophora (840 g/kg)",
  cultura_canonica: "uva", praga_nome_cientifico: "Scaptocoris castanea",
  classe_toxicologica: null,       // rótulo não-numérico → null
  organicos: "S", situacao: "Registrado" }
db.agrofit.createIndex({ cultura_canonica: 1, praga_nome_cientifico: 1 })
db.agrofit.createIndex({ cultura_canonica: 1, organicos: "S" })  // parcial
```

**Normalização de toxicidade na ingestão** — sem isso, 5,6% dos registros ficam de
fora de qualquer filtro numérico:

```python
TOX = {"Categoria 1": 1, "Categoria 2": 2, "Categoria 3": 3,
       "Categoria 4": 4, "Categoria 5": 5,
       "Extremamente Tóxico": 1,    # rótulo antigo = Cat 1
       "Altamente Tóxico": 2,       # rótulo antigo = Cat 2
       "Medianamente Tóxico": 3, "Pouco Tóxico": 4}
# 'Não Classificado' / 'NÃO DETERMINADO' → null. null NÃO passa em $gte.
```

Distribuição real: Cat 5 = 202.733 (76,7%) · Cat 4 = 49.372 (18,7%) · Cat 3 = 6.030 ·
Cat 2 = 5.379 · Cat 1 = 920 · não-numéricos = **15.725**.

### 5.4 `cache_clima` — sem TTL

```js
{ cod_ibge: "3503208", coletado_em: ISODate("2026-10-02T15:05:00Z"),
  dias: ["2026-10-02", /* … */ "2026-10-08"],
  chuva_diaria: [0, 2, 10, 18, 8, 3.5, 0.5], chuva_7d_mm: 42.0,
  tmin_diaria: [12.0, 10.5, 8.0, 5.5, 3.0, 5.2, 8.4],
  tmin_min_7d: 3.0, dia_tmin: "2026-10-06" }
```

⚠️ **Não usar `expireAfterSeconds`.** O TTL do Mongo **apaga o documento** — o motor
perde o dado velho e não pode devolvê-lo com `degradado: true`, que é o princípio
da degradação graciosa. **Idade calculada na aplicação.**

### 5.5 `data_sources` — a melhor proveniência de todas as versões

```js
{ _id: "zarc", name: "MAPA — ZARC Tábua de Risco 2026/2027",
  url: "https://dados.agricultura.gov.br/…", license: "CC-BY",
  extracted_at: ISODate("2026-10-02"), reference_period: "2026/2027",
  transformations: ["filtro cultura=graos", "join cod_ibge"],
  fields_used: ["Cod_Solo", "dec1..dec36"],
  limitations: ["ZARC e zoneamento municipal; nao considera microclima."] }
```

Alimenta o botão "Ver fonte" do `EvidenceCard`.

---

## 6. Motor de evidências

### 6.1 Fluxo

```
Contexto da safra
      ↓
Resolver município + cultura
      ↓
Resolver parâmetros disponíveis (solo? nm?)
      ↓
Consultar fontes (ZARC, clima, PSR, SIGEF, ANA)
      ↓
Normalizar respostas
      ↓
Validar compatibilidade
      ↓
Classificar cada evidência
      ↓
Montar EvidenceBundle
```

### 6.2 Os 4 estados honestos

```
✓ favoravel        a fonte sustenta uma afirmação
⚠ atencao          a fonte tem ressalva
? parametros_pendentes  falta dado para concluir
— sem_dado         a fonte não cobre este caso
```

**Nunca usar "score 90%". A banca vê quatro estados honestos.**

⚠️ **Melhor que o `confianca: alta/média/baixa` da v4:** os estados descrevem **o que
o dado permite dizer**, não o quanto o sistema tem certeza de si.

### 6.3 Por que o bundle existe

**O LLM nunca recebe JSON solto.** Recebe: contexto da safra · evidências com fonte
+ data · limitações · tarefas pendentes · últimos registros do diário.

Assim a IA **só explica, não inventa**.

---

## 7. Pipeline do motor

```python
async def processar(self, req):
    ctx   = await self.resolver(req)                       # validação + geo
    nomes = set(self.ROTAS[ctx.intencao]) | {"alertas"}    # ⭐ alertas sempre
    blocos = await asyncio.gather(*(
        self._com_timeout(self.analyzers[n], ctx, 0.8) for n in nomes))
    risco  = self.risk_engine.avaliar(ctx, blocos)
    regras = self.rule_engine.aplicar(ctx, blocos, risco)
    return self.payload_builder.montar(ctx, blocos, risco, regras)
```

**Princípios:** (1) o request path **nunca** chama API externa — lê cache;
(2) o motor é **determinístico** — a LLM só extrai a intenção na entrada e redige na
saída; (3) falha de analisador vira **bloco degradado**, não 500.

### 7.1 Roteador

| Intenção | Analisadores |
|---|---|
| `escolha_cultivo` | zarc, psr, sigef, hidrico, clima |
| `risco_climatico` | zarc, clima, psr, **alertas** |
| `praga` | agrofit, clima, **alertas** |
| `manejo_irrigacao` | hidrico, clima, zarc, **alertas** |
| `geral` | zarc, clima, **alertas** |

### 7.2 ZarcAnalyzer — a distinção que importa

```python
# NÃO filtra por `abertos` — precisa distinguir "fora da janela" de "não zoneado"
alvo = db.zarc.find(
    {"cod_ibge": g, "cultura_canonica": c, "solo_canonico": s,
     "manejo_canonico": m, "safra": safra},      # ⭐ sem nm
    {"_id": 0, "ciclo_grupo": 1, "dec": 1, "abertos": 1, "portaria": 1})

# alternativas: aqui sim usa o índice por `abertos`
alt = db.zarc.find(
    {"cod_ibge": g, "manejo_canonico": m, "solo_canonico": s,
     "abertos": dec_atual, "cultura_canonica": {"$in": outras}},
    {"_id": 0, "cultura_canonica": 1, "dec": 1})
```

⚠️ **Filtrar por `abertos` na busca principal perde a informação essencial:**
"não zoneado" e "fora da janela" são respostas diferentes, e a segunda é reversível.

⚠️ **Devolva a janela por ciclo, não uma única.** Medido em Araraquara: milho 1ª
safra × solo 3 tem **três ciclos** (20, 21, 22) com janelas distintas.

### 7.3 RiskEngine — veto, depois score

```python
def avaliar_risco(ctx, zarc, clima, psr):
    if zarc is None:
        return Risco(status="nao_zoneado", veto="cultura_nao_zoneada",
                     confianca="alta")
    pct = zarc["melhor"]["risco_pct"]
    if pct is None:                    # ⭐ VETO DURA
        return Risco(status="fechada", risco_pct=None,
                     veto="fora_janela_zarc", confianca="alta")

    d_clima = 0
    chuva = clima["chuva_7d_mm"]
    if   chuva < 10 and not ctx.irrigacao: d_clima += 8
    elif chuva > 100:                       d_clima += 8
    elif 20 <= chuva <= 60:                 d_clima -= 3
    # 10-20 e 60-100 → d_clima = 0 EXPLÍCITO (a v3 tinha lacuna silenciosa)
    if ctx.cultura_sensivel_geada and clima["tmin_min_7d"] <= 3:
        dias = (clima["dia_tmin"] - ctx.hoje).days
        if dias <= EMERGENCIA[ctx.cultura][0]: d_clima += 15

    d_hist = 0
    if psr and psr["total_apolices"] >= 30:
        w = psr["total_apolices"] / (psr["total_apolices"] + 200)
        d_hist = max(-5, min(5, w * (psr["taxa_sinistro_pct"]
                                     - psr["taxa_base_cultura_pct"])))
    else:
        ctx.confianca_rebaixar("poucas apolices no historico")

    ajuste = max(-10, min(15, d_clima + d_hist))    # ajustes nunca dominam
    risco = max(0, min(100, pct + ajuste))
    status = "aberta" if risco <= 25 else "atencao" if risco <= 40 else "fechada"
```

**Quatro decisões:** (1) veto antes do score; (2) bandas declaradas; (3) clima como
**ajuste**, não base — ZARC é climatologia de longo prazo, chuva de 7 dias é curto
prazo; (4) encolhimento do histórico, com piso de 30 apólices.

⚠️ **Os pesos (200, 8, 15, tetos) não têm fonte declarada.** Precisam de calibração
com agrônomo e teste contra casos conhecidos.

### 7.4 Nível de risco de sinistro — com a tabela real

Regra: ≥ 40% = alto · 15–39% = médio · < 15% = baixo.

| Evento | Brasil (301.498) | Milho (82.962) |
|---|---|---|
| **SECA** | 157.350 — **52,2%** → **alto** | 55.595 — **67,0%** → **alto** |
| Granizo | 44.467 — 14,7% → baixo | 2.296 — 2,8% → baixo |
| **GEADA** | 30.972 — **10,3%** → **baixo** | 12.468 — 15,0% → médio |

⚠️ **Geada dá "baixo" no Brasil** — contra-intuitivo, mas é o que o dado diz.
**Seca é 52% dos sinistros: o alerta de seca é o que o número sustenta.**

---

## 8. Workers e alertas

```python
app.conf.beat_schedule = {
  "clima":   {"task": "tasks.clima_lote",     "schedule": crontab(minute=5,  hour="*/6")},
  "alertas": {"task": "tasks.avaliar_alertas","schedule": crontab(minute=20, hour="*/6")},
  "risco":   {"task": "tasks.refresh_risco",  "schedule": crontab(minute=0,  hour=3)},
  "janela":  {"task": "tasks.janela_zarc",    "schedule": crontab(minute=0,  hour=7)},
}
```

| Alerta | Condição | Horizonte |
|---|---|---|
| Geada | tmin ≤ 3 °C **e** cultivo em estágio sensível | 1–7 d |
| Veranico | chuva < X mm em Y dias na germinação/floração | 7–10 d |
| Excesso | > 100 mm/7d perto de plantio ou colheita | 7 d |
| **Janela fechando** | falta ≤ 1 decêndio para a janela fechar | decêndio |
| Seca sazonal | previsão desfavorável + histórico PSR de seca | estação |

**Quatro decisões:** clima por município (não por produtor) · **nunca notificar sem
dado** (degrada em vez de inventar) · idempotência por `chave_dedupe` com cooldown
de 24 h · filas separadas para ingestão não atrasar alerta.

⚠️ **Não prometa alerta de surto de pragas.** Nenhuma das 6 bases traz vigilância de
pragas — o [[agrofit]] é catálogo, não monitoramento.

---

## 9. Privacidade e LGPD

### Regra principal

> **Um dado ser público não significa que ele deva ser reproduzido integralmente.**

### Pipeline de privacidade

```
RAW (CSV do MAPA)
   ↓
PII FILTER (remove NM_SEGURADO, NR_DOCUMENTO_SEGURADO, lat/lon individual)
   ↓
AGGREGATION (agrupa por cod_ibge + cultura + ano)
   ↓
PRODUCTION (Mongo)
```

⚠️ **Mais estrito que a organização exige.** [[hackaton-regras]] diz apenas "nunca
cruzem bases pra reidentificar uma pessoa". Filtrar **na entrada** é mais barato e
mais defensável que filtrar na saída.

### O que nunca entra no Mongo de produção

`NM_SEGURADO` · `NR_DOCUMENTO_SEGURADO` · endereço individual · telefone · e-mail ·
coordenadas individuais sem necessidade

### Como falar de sinistro

❌ "14% dos agricultores perderam a safra"
✅ "Nos registros disponíveis, X apólices apresentam Y ocorrências conforme o critério
utilizado."

### Proveniência visível

Todo `EvidenceCard` tem **"Ver fonte"** → dataset, órgão, URL, licença, data de
extração, período de referência, limitações conhecidas.

---

## 10. Regra de ouro: regras vs IA

### Determinístico (backend)

Normalização de cultura · lookup por `cod_ibge` · cálculo de decêndio · filtro de
disponibilidade · agregação PSR/SIGEF · criação de tarefas e missões · status ·
proveniência · soma de custos · avanço de etapa.

### IA (LLM)

Interpretar texto livre do diário · explicar o `EvidenceBundle` · resumir o estado ·
transformar registro em próxima ação · classificar intenção.

> **Se dá pra calcular em SQL/Python, não chama LLM. Se é linguagem natural, chama
> LLM.**

### System prompt (10 regras)

1. Não invente números · 2. Não invente fontes · 3. Não afirme que algo é oficial
se for derivado · 4. Não transforme ausência de dados em certeza · 5. Não dê
diagnóstico agronômico definitivo · 6. Não determine elegibilidade de programas ·
7. Declare limitações · 8. Use apenas o `EvidenceBundle` · 9. Diferencie dado,
inferência e sugestão · 10. Indique fonte.

### Fallback determinístico

```python
def fallback(bundle):
    n = len(bundle["pending_tasks"])
    prox = bundle["pending_tasks"][0]["title"] if n else "Nenhuma tarefa pendente"
    return {"resumo": f"Voce tem {n} tarefa(s) pendente(s). Proxima: {prox}.",
            "evidencias_utilizadas": [e["type"] for e in bundle["evidences"]],
            "alertas": [], "proximas_acoes": [],
            "limites": ["Explicacao deterministica: provedor de IA indisponivel."]}
```

**O sistema nunca depende do LLM pra funcionar.**

---

## 11. Ingestão

### Ordem obrigatória

```
1. ZARC      → cria municipios (hub) + popula zarc
2. ANA       → enriquece municipios
3. PSR       → popula psr_agregado (2016-2024, usa CD_GEOCMU)
4. SIGEF     → popula sigef_agregado (lookup nome+uf → cod_ibge)
5. Agrofit   → popula agrofit (NÃO explode — 1 cultura por linha)
6. data_sources → metadados
```

⚠️ **ZARC primeiro** porque é o único com `geocodigo` limpo — é ele que cria o hub.

### Mapas canônicos (do dicionário oficial — conferidos)

```python
SOLO_MAP = {1:"arenoso", 2:"media", 3:"argiloso",
            11:"ad1", 12:"ad2", 13:"ad3", 14:"ad4", 15:"ad5", 16:"ad6"}
MANEJO_MAP = {1:"sequeiro", 2:"irrigado", 3:"irrigado_geada"}
CICLO_MAP  = {13:"perene", 19:"semiprene", 20:"grupo_i", 21:"grupo_ii",
              22:"grupo_iii", 24:"grupo_iv", 25:"grupo_v", 26:"grupo_vi"}
CLIMA_MAP  = {0:"nao_se_aplica", 1:"alta_frio", 2:"media_frio", 3:"baixa_frio",
              4:"semiarido", 5:"ameno", 6:"quente", 7:"tropical",
              8:"subtropical_ameno", 9:"subtropical_frio", 11:"subtropical"}
```

Verificados contra o **Dicionário de Dados da Tábua de Risco 2026**
(CGRA/DEGER/SPA, MAPA) — todos corretos.

### NM — contexto, não filtro

3 perguntas com tutorial: análise de solo · semente certificada · adubação.
`NM = min(1 + pontos, 4)`.

⚠️ **Frase obrigatória na interface:** *"Categoria técnica estimada a partir das suas
respostas. Não é classificação oficial do ZARC."*

⚠️ **Não use NM como filtro do ZARC** — `Cod_NM` está vazio em 97,3% e só existe
para soja.

---

## 12. Schemas

### Entrada

```json
{
  "safra_id": "saf_demo_001",
  "cod_ibge": "3503208",
  "crop_input": "milho",
  "area_ha": 5, "soil": "argiloso", "management": "sequeiro",
  "respostas_nm": { "analise_solo": "nunca", "semente": "salva",
                    "adubacao": "chute" },
  "cultivos_ativos": [ { "cultura": "soja", "area_ha": 3, "estagio": "colheita" } ],
  "pergunta": { "texto": "Posso plantar milho agora?",
                "intencao": "risco_climatico" }
}
```

### Saída — **todos os números medidos em Araraquara**

```json
{
  "meta": { "degradado": false, "blocos_indisponiveis": [], "confianca": "media",
            "motivos_confianca": ["solo declarado sem analise",
                                  "PSR com 114 apolices em 9 anos"] },
  "consulta": { "municipio": "Araraquara", "uf": "SP", "cultura": "milho",
                "solo": "argiloso", "ciclo": "grupo_i",
                "decendio_atual": 28, "safra": "2025/2026" },

  "decisao": {
    "status": "atencao", "risco_pct": 33,
    "resumo": "Janela aberta para milho 1a safra (solo argiloso), mas o decendio 28 e o de maior risco da janela. Os decendios 29 a 36 tem risco 20%.",
    "janela_recomendada": { "decendios": [29,30,31,32,33,34,35,36],
                            "risco_pct": 20,
                            "inicio": "2026-10-11", "fim": "2026-12-31" }
  },

  "evidencias": [
    { "type": "zarc", "status": "favoravel", "source": "MAPA — ZARC",
      "extracted_at": "2026-10-02", "reference_period": "2025/2026",
      "data": { "decendio_atual": 28, "risk_pct": 30, "melhor_janela": 20 },
      "limitations": ["ZARC e zoneamento municipal; nao considera microclima."] },
    { "type": "psr", "status": "atencao", "source": "MAPA — SISSER",
      "extracted_at": "2026-10-02", "reference_period": "2016-2024",
      "data": { "apolices_municipio": 114, "com_sinistro": 10,
                "taxa_pct": 8.77, "pago_reais": 200416.53,
                "culturas": { "Cana-de-acucar": 60, "Soja": 44, "Milho 1a": 1 } },
      "limitations": ["Dados de apolice, nao de producao individual."] },
    { "type": "ana", "status": "sem_dado", "source": "ANA — Atlas Irrigacao",
      "data": { "area_irrigada_ha": 472.0, "pivois_mapeados": 0 },
      "limitations": ["Nenhum pivo central registrado no municipio."] }
  ],

  "riscos": [
    { "tipo": "seca", "nivel": "alto", "horizonte": "estacao",
      "evidencia": "Seca = 55.595 de 82.962 sinistros de milho no Brasil (67,0%).",
      "fonte": "MAPA/SISSER 2016-2024" },
    { "tipo": "geada", "nivel": "baixo", "horizonte": "estacao",
      "evidencia": "Geada = 12.468 sinistros em milho (15,0%); 10,3% no Brasil.",
      "fonte": "MAPA/SISSER 2016-2024" }
  ],

  "historico_local": {
    "mensagem": "Em 9 anos Araraquara teve 114 apolices; 10 tiveram sinistro (8,8%). Cana e soja respondem por 91% delas. Milho aparece em 1."
  },

  "alternativas": [
    { "cultura": "soja",   "risco_pct": 20, "status": "aberta",
      "observacao": "Risco 20% no decendio 28. 44 das 114 apolices do municipio sao soja." },
    { "cultura": "feijao", "risco_pct": 20, "status": "aberta",
      "observacao": "Risco 20% no decendio 28 (solo AD4, irrigado)." },
    { "cultura": "sorgo",  "risco_pct": 20, "status": "aberta",
      "observacao": "Risco 20% no decendio 28 (solo argiloso, sequeiro)." }
  ],

  "instrucoes_para_llm": {
    "tom": "simples, direto, sem jargao",
    "nao_afirmar": ["garantia de safra", "dose de defensivo",
                    "diagnostico de praga sem imagem",
                    "previsao de geada alem de 7 dias"],
    "sempre_incluir": ["aviso_legal"]
  },
  "limitacoes": ["ZARC e zoneamento municipal."],
  "aviso_legal": "Ferramenta de apoio a decisao. Nao substitui responsavel tecnico habilitado (Lei 14.785/2023). Registros de defensivo exigem receituario agronomico (art. 39)."
}
```

### O que mudou contra os exemplos das 4 versões

| | v2 · v3 · v4 · Mestre | Aqui (medido) |
|---|---|---|
| `decendio_atual` | 29 | **28** |
| PSR ano | 2025 | **2016–2024** |
| apólices | 3.412 · 1.200 · 120 | **114** |
| taxa sinistro | 14,2% · 11,0% · 15% | **8,77%** |
| irrigação | "12,3%, pivô central" | **472 ha, 0 pivôs** |
| janela | 28–30 | **29–36 a 20%** |
| lei | 7.802/1989 | **14.785/2023** |
| `agrofit` explode | sim | **não** — 1 cultura/linha |
| `cache_clima` TTL | `expireAfterSeconds` | **sem TTL** |
| `nm` no índice | sim | **não** — fora do filtro |

⚠️ **Araraquara tem soja e feijão a 20% no decêndio 28, e 44 das 114 apólices são
soja.** A recomendação real para o produtor local não é milho — é **manter e
expandir soja**.

---

## 13. Frontend — 3 telas

⚠️ **Corte de 6 para 3.** `radar` + `diario` + `missoes` provam o ciclo completo.
`plano` é lista, e `/` absorve. Para 24 h, três telas.

**`/` Minha Safra** — etapa atual · próxima ação · contadores · último registro
**`/radar` Radar** — `EvidenceCard` com 4 estados, fonte e limitações
**`/diario` Diário** — registro → eventos estruturados → tarefas → missão → explicação

`ConsultorPanel` flutuante: pergunta em linguagem natural, resposta sempre
estruturada (`resposta` / `baseado_em` / `acoes` / `limitacoes`).

**Descartado:** `farm` como coleção separada (`safra_id` anônima resolve) ·
`PATCH /proxima-etapa` manual (consome tempo, prova pouco no pitch).

---

## 14. Modos e degradação

| Modo | Comportamento |
|---|---|
| `LIVE` | tudo funcionando |
| `DEMO_MODE=true` | dados locais pré-carregados, sem chamadas externas |
| `LLM_OFF` | fallback determinístico em texto |
| `CLIMA_OFF` | evidência climática marcada indisponível |

Quando uma fonte cai: `ZARC ✓ · PSR ✓ · SIGEF ✓ · Clima ? · ANA ✓` →
*"A decisão foi montada com 4 fontes. O contexto climático não está disponível."*

**Nunca inventar dado faltante.**

---

## 15. Ordem de implementação

1. **Normalizar toxicidade** + `nm = null` · PSR só 2016–2024
2. Ingestão versionada + `abertos` + PII filter
3. `RiskEngine` com veto + testes golden
4. `POST /safras` + `GET /radar` — libera o frontend em paralelo
5. Diário → tarefa → missão (o momento "wow")
6. Workers de janela fechando e seca
7. Thesagro para `praga_sinonimos` — única base que oficializa sinônimos

**Não fazer:** SIGEF INCRA (fundiário, fora do escopo) · `sisser_hidrico` (SISSER é
seguro rural) · surto de pragas (não há vigilância) · defensivo sem receituário
(Lei 14.785/2023, art. 39).

---

## 16. Testes golden

```python
def test_araquara_milho_2026_10_02():
    r = motor.processar(req_fixture("araquara", "milho", "argiloso"),
                         agora="2026-10-02T14:32-03:00")
    assert r.consulta.decendio_atual == 28
    assert r.decisao.janela_recomendada.decendios == list(range(29, 37))
    assert r.evidencias["psr"]["data"]["apolices_municipio"] == 114
    assert r.evidencias["psr"]["reference_period"] == "2016-2024"

def test_fora_da_janela_e_veto():
    r = motor.processar(req_fixture("araquara", "milho", "arenoso"),
                         agora="2026-12-15")
    assert r.decisao.veto == "fora_janela_zarc"
    assert r.decisao.risco_pct is None      # ⭐ nunca 0 nem 100

def test_sem_pii_no_mongo():
    assert db.psr_agregado.count_documents({"nome_segurado": {"$exists": True}}) == 0
```

---

## 17. Aviso legal

> Ferramenta de apoio à decisão. **Não substitui responsável técnico habilitado
> (Lei 14.785/2023).** Registros de defensivo exigem **receituário agronômico**
> (art. 39).

⚠️ A Lei 14.785/2023 **revoga** as Leis 7.802/1989 e 9.974/2000.

---

Ver [[review-arquitetura-agropilot]], [[review-arquitetura-v4]],
[[review-documento-mestre-v3]], [[arquitetura-motor-correlacao]],
[[relatorio-consolidado]], [[chave-de-join-ibge]], [[semantica-zarc-zero]],
[[hackaton-regras]], [[zarc-nao-cobre-perenes]].