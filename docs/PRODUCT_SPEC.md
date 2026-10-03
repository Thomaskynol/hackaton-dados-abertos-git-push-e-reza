# 🌾 AgroPilot — Consultor Comercial e Copiloto da Safra

## Documento de Definição do Produto (PRD) & Arquitetura — Hackathon 2026

> **Status:** documento vivo. Consolida o escopo atual após a virada de foco para
> o **consultor comercial regional (Mapa)** como carro-chefe, com o copiloto
> conversacional reposicionado como apoio. Complementa — não substitui — o
> `docs/documento-mestre-agropilot.md` (referência técnica da correlação de dados)
> e o `CONTRATO_API.md` (contrato front↔back).

---

## 0. Mudança de foco (leia primeiro)

O AgroPilot nasceu centrado num **chatbot agrícola**. A partir desta versão, o
**carro-chefe é o Mapa / consultor comercial regional**: o produtor abre o app,
vê o mapa do Brasil, toca na sua região e recebe um **card de insights** com
preço de mercado, piso de proteção, o que a região mais produz, tipo de solo,
irrigação e canais de venda — tudo com fonte e data.

> **Tese nova:** *"O produtor não perde dinheiro só no campo. Perde na hora de
> vender, por falta de informação de mercado. O AgroPilot é a camada de
> inteligência comercial — e de tradução técnica — que faltava, no bolso."*

O chatbot **continua existindo** como **Assistente de apoio**: ele ajuda a
interpretar o mapa, os preços e as evidências. Deixa de ser a tela principal.

> **Tese dupla (não é troca, é combinação).** O "consultor comercial" é a tese
> **vendável em 30s** (dor real: o produtor perde dinheiro na hora de vender). A
> "safra com memória" (versões anteriores) é a tese **profunda e original**, e
> ela volta no momento em que o produtor toca na UF e o card diz: *"Você planta
> milho em Araraquara; aqui vende a R$ X (CONAB), o piso é R$ Y (PGPM), e a maior
> parte das apólices é de pequenos como você. Registre sua safra que eu te aviso
> quando o preço passar o piso."* **O mapa abre; a memória fecha.** As duas numa
> frase, e honesta — o sistema só "avisa" o que tem dado para avisar.

### Por que a virada
- Serve **igual** o pequeno/familiar e o grande produtor — todos vendem, todos
  querem faturar mais. Comercial é universal.
- Diferencia de "mais um ChatGPT agrícola": o valor é **dado público comercial
  georreferenciado**, não conversa genérica.
- É **honesto e defensável**: preço vem da CONAB (fonte pública), não de palpite.

---

## 1. Filosofia e Princípios

### O princípio que guia tudo
> *"O produtor não tem margem para errar — nem no campo, nem na venda."*

Um pequeno produtor que vende abaixo do piso, ou no canal errado, come o próprio
lucro. Um grande produtor que não compara praças perde escala de margem. Os dois
precisam de informação comercial clara.

### Os 7 princípios

| Princípio | Significado | Implementação |
|---|---|---|
| **1. Universal** | Serve familiar e latifundiário; grãos e hortaliças | Camada de dados por UF/município + níveis de observabilidade (§7) |
| **2. Comercial** | Ajuda a faturar mais, não só a plantar | Mapa + card de preço (CONAB), piso (PGPM), canais de venda |
| **3. Proativo** | Avisa antes do problema (janela, clima, oportunidade) | Early Warning + alertas por combinação de fatores (§8) |
| **4. Honesto** | Todo número tem fonte e data; sem dado → estado honesto | 4 estados; "Ver fonte" em todo card; regra de ouro (§3) |
| **5. Explicável** | Mostra o porquê e a origem; nunca "score 90%" | EvidenceCard + "Leitura do AgroPilot" (síntese) |
| **6. Seguro** | Não substitui ZARC, agrônomo nem decide a venda | Mostra cenário; o produtor decide (§3, §9) |
| **7. Acessível** | Telefone + nome; áudio; linguagem simples; mobile-first | Next + Tailwind, TTS, Modo Campo, alvos ≥ 44px |

### O que o AgroPilot NÃO é
| Não é | Por quê |
|---|---|
| ❌ Site informativo | Google já faz, sem contexto da região do produtor |
| ❌ Dashboard passivo | O produtor quer saber **onde e por quanto vender**, não só gráfico |
| ❌ ChatGPT agrícola genérico | Modelo genérico não conhece preço CONAB por UF nem ZARC decendial |
| ❌ Corretora / casa de análise | Não dá ordem de venda; **mostra** preço, piso e canais |
| ❌ Previsor de preço futuro | Sem modelo validado → alucinação. Mostra série/tendência honesta, não "profecia" |
| ❌ Sistema só para o grande | Foco inicial no familiar; mesma engine escala para o grande (§7) |

### O que o AgroPilot É
> **Um consultor comercial regional + copiloto da safra que conhece o produtor,
> a propriedade e a REGIÃO, mostra preço e canais de venda com fonte, antecipa
> riscos, e traduz dado técnico oficial em o próximo passo — da semente à venda.**

---

## 2. Jornada e ciclo do produto

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      JORNADA DO PRODUTOR                                  │
│                                                                           │
│  🌱 PLANEJAR   🌾 PLANTAR    💧 ACOMPANHAR   🚜 COLHER    💰 VENDER        │
│  o que/onde    janela ZARC    risco/clima     momento     PREÇO + CANAL   │
│      │            │              │              │            │ ◄──────────┤
│      ▼            ▼              ▼              ▼            ▼  carro-chefe │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                           AGROPILOT                                  │ │
│  │  MAPA (consultor comercial)  ·  SAFRA (estado+risco)  ·  ASSISTENTE  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

### O loop que diferencia (inovação)
Enquanto a concorrência faz `dados → recomendação`, o AgroPilot fecha o loop:

```
DADOS → PREDIÇÃO (risco) → SIMULAÇÃO ("e se?") → DECISÃO → AÇÃO → NOVA EVIDÊNCIA
  ▲                                                                      │
  └──────────────────────────────────────────────────────────────────────┘
```
Detalhe do loop preditivo (gêmeo digital simplificado, risco explicável,
simulador "E se?", Early Warning, próxima decisão) em **§8**.

---

## 3. Regra de ouro: honestidade de dados (inviolável)

> **Todo número exibido como fato PRECISA de fonte e data visíveis. É PROIBIDO
> inventar preço, produção, comprador, cotação ou qualquer dado. Quando faltar
> dado, exibir estado honesto. O sistema MOSTRA o cenário; não decide pela
> pessoa. Nunca "score 90%". Nunca "venda agora".**

Isto vale para front, back, correlação e IA. É o que separa o AgroPilot de um
protótipo que fabrica "R$ 128,50/saca" sem origem — exatamente o erro que derruba
credibilidade na banca.

### Os 4 estados honestos (herdados do documento-mestre §6.2)
```
✓ favorável          a fonte sustenta a afirmação
⚠ atenção            a fonte tem ressalva
? pendente           falta um dado para concluir (ex.: cultura/solo não informado)
— sem dado           a fonte não cobre este caso (ex.: sem cotação para a UF)
```

---

## 4. Arquitetura da aplicação (estado atual)

### 4.1 Frontend — `front/` (JÁ CONSTRUÍDO, navegável, sem backend)
- **Stack:** Next.js 14 (App Router) + TypeScript + Tailwind CSS. Mobile-first.
- **Fontes:** stack do sistema via `--font-sans`/`--font-display`
  (NÃO usar `next/font/google` — falha offline e quebra o build).
- **Paleta terrosa** (fuga do verde-agro genérico), tokens em
  `src/app/globals.css`: `canvas` (off-white quente), `surface`, `line`, `ink`,
  `muted`, `terra` (terracota = AÇÃO), `terra-soft`, `terra-ink`; estados
  `favoravel` (oliva), `atencao` (âmbar), `risco` (tijolo), `pendente`.
  Inclui `.modo-campo` (alto contraste para sol forte).
- **Acessibilidade:** alvos ≥ 44px, foco visível, `aria-*`, `prefers-reduced-motion`,
  pt-BR, linguagem simples. Ícones `lucide-react`.
- **Áudio:** `useGravacao` (mic/MediaRecorder) em `src/lib/audio.ts`. Não há
  leitura em voz alta (TTS) na UI. Transcrição real fica para o backend.
- **Integração com backend:** na Fase 1 o front roda com dados locais honestos em
  `src/lib/*` e perfil em `localStorage` (`usePerfil`). Na Fase 2 (§10.2) passa a
  consumir `/api/regiao/{uf}` com fallback ao local. Tipos em `src/lib/types.ts`
  espelham o `CONTRATO_API.md` para a troca ocorrer **sem mexer na UI**.

Estrutura:
```
front/src/
├── app/
│   ├── globals.css, layout.tsx, page.tsx (redireciona)
│   ├── login/            # entrada só com telefone
│   ├── onboarding/       # 5 passos, UMA pergunta por tela
│   └── (app)/            # casca TopBar + BottomNav
│       ├── mapa/         # ◄ CARRO-CHEFE (a construir — §5)
│       ├── safra/        # estado da propriedade + decisão do dia
│       ├── radar/        # evidências (4 estados + Ver fonte)
│       └── perguntar/    # Assistente (chat voz/texto/chips) — apoio
├── components/           # Button, Chip, EvidenceCard,
│                         # ChatBubble, ChatInput, TopBar, BottomNav
└── lib/                  # types, dados-locais, perfil-context, audio,
                          # mapa-local (a criar), precos (a criar)
```

### 4.2 Backend — `back/` (FastAPI, hoje em mock + consulta parcial)
- FastAPI + Pydantic; rotas `health/chat/onboarding/produtor/alertas`.
- `db.py` conecta Mongo (lazy, degrada para mock sem Mongo).
- `dados_reais.py` já consulta `zarc` e `agrofit`; demais bases ociosas.
- RiskEngine, EvidenceBundle e camada LLM ainda **não** implementados
  (especificados no documento-mestre §6, §7).

### 4.3 Correlação — `correlacao/` (ingestão pronta e testada)
- 6 bases → Mongo `agropilot`: ZARC (hub `municipios`), ANA, PSR, SIGEF, Agrofit.
- Stdlib only; 48 testes; PII filtrada na entrada; proveniência por fonte.
- Detalhes e invariantes no `docs/documento-mestre-agropilot.md`.

---

## 5. Carro-chefe: aba **Mapa** (consultor comercial regional)

### 5.1 Objetivo e hierarquia (o mapa é navegação, a síntese é o produto)
O produtor abre o Mapa, toca na sua UF e recebe um **card de insights regionais**
que o ajuda a decidir **onde e por quanto vender**. Primeira aba, tela inicial
pós-login.

> ⚠️ **Correção de prioridade (importante).** O mapa em si **não é o
> diferencial** — qualquer dashboard tem um mapa do Brasil, e a banca já viu
> dezenas hoje. O diferencial é a **Leitura do AgroPilot** (§5.7): a síntese que
> conecta preço × piso × canal numa decisão. Portanto: **o mapa é navegação; o
> card + a síntese são o produto.** Não gastar horas em pan/zoom; gastar o
> esforço fazendo a síntese brilhar com dado real.

### 5.2 Mapa do Brasil por UF (SVG estático clicável — leve e suficiente)
- SVG dos 27 estados (paths inline ou GeoJSON simplificado de baixa resolução).
  **Estático e clicável** — sem pan/zoom caro. Clique/toque na UF abre o card.
  Isso economiza horas de engenharia que vão para a síntese (§5.7).
- UF com realce ao toque/hover; UF selecionada destacada. Transições simples,
  respeitando `reduced-motion`. Visual clean: cantos arredondados, sombra suave,
  paleta terrosa, sensação premium — mas sem gesto complexo.
- **Coroplético:** colore UFs por intensidade de uma métrica (ex.: preço da
  cultura). Sem dado real ligado, usar escala neutra ou valores **claramente
  rotulados como exemplo** — nunca exemplo como fato.
- A UF do perfil (default **SP/Araraquara**) começa pré-selecionada.
- **Drill-down município** e pan/zoom ficam para depois (não são MVP).

### 5.3 Card de insights — 4 blocos visíveis + "Ver mais" colapsado
No celular, 10 blocos viram 3 scrolls e a banca desiste no 4º. Então o card
mostra **4 blocos acima da dobra**, e o resto fica num acordeão
**"Ver mais sobre esta região"**. Cada bloco com **fonte + data**.

**Visíveis (acima da dobra):**
1. **Leitura do AgroPilot** (topo, sempre visível) — a síntese que conecta preço
   × piso × canal numa decisão (§5.7). É o primeiro e o mais importante.
2. **Preço de mercado** — preço da cultura na UF. **Fonte: CONAB** (pesquisa de
   preços por UF; preço de mercado real, público — não cotação diária de bolsa).
   Sempre com a data da pesquisa. É **referência/contexto**, não ordem de venda.
3. **Piso de proteção (PGPM)** — preço mínimo garantido por cultura/safra.
   **Fonte: CONAB/PGPM** (redistribuição autorizada — §5.4). Permite a
   comparação "mercado × piso", que é o coração da leitura.
4. **Canais de venda** — **categorias reais**, nunca compradores nominais
   fabricados: cooperativas, cerealistas e **PAA/PNAE** (compra pública que paga
   prêmio à agricultura familiar — fato público).

**Colapsados em "Ver mais sobre esta região":**
5. **Tipo de solo predominante** — descrição simples ("terra que segura água").
   Fonte: ZARC/dicionário de solos.
6. **O que a região mais produz** — culturas por área/produção. **Fonte: SIGEF.**
7. **Força no seguro rural** — culturas que concentram apólices/valor (pujança +
   risco histórico; indica também % de pequenos produtores). **Fonte: PSR/SISSER**, 2016–2024.
8. **Irrigação disponível** — área irrigada. **Fonte: ANA — Atlas Irrigação.**
9. **Indicador diário (Cepea/ESALQ)** — **apenas LINK externo** ao site do Cepea
   (restrição de licença: não copiar/redistribuir o número).
10. **Oportunidade regional** (insight original) — culturas que o ZARC indica
    como aptas mas que a região **pouco explora** (cruzamento ZARC × SIGEF).
    Estruturar e marcar pendente até o dado ligar.

### 5.4 Fontes de preço — o que é honesto usar
| Fonte | O que dá | Uso no AgroPilot | Licença |
|---|---|---|---|
| **CONAB — PGPM** | preço mínimo oficial por cultura/safra | piso de proteção (bloco 3) | **pública, redistribuição autorizada** |
| **CONAB — pesquisa de preços** | preço de mercado por UF, 112+ produtos, série periódica | preço de mercado (bloco 2) | pública / aberta |
| **CEASA** | hortifruti por entreposto | preço de hortaliças (fase posterior) | pública (varia por praça) |
| **Cepea/ESALQ** | indicador diário (soja, milho, boi) | **link externo** apenas | restringe redistribuição |

> ✅ **PGPM destravado.** O Portal de Informações Agropecuárias da CONAB autoriza
> a reprodução dos Preços Mínimos, desde que citada a fonte e mantida a
> integridade. Os valores da safra 2026/27 são públicos e **estáveis** (não mudam
> diariamente). Logo, o AgroPilot **pode exibir o PGPM real com fonte** — é o
> número honesto mais fácil de pôr de pé e sustenta a comparação do bloco 3.
>
> ⚠️ **Cepea nunca entra como número** (só link). **Nunca** inventar "preço de
> hoje". A pesquisa de preços CONAB é periódica (não diária) — a data da pesquisa
> fica sempre visível; onde faltar cotação, o bloco mostra "sem cotação".

### 5.5 Camadas de dados — do front local ao backend real
Fase 1 (feito), front sem backend:
- `src/lib/mapa-local.ts` — 27 UFs + `insightsDaUF(uf)` com `pendente`/`sem_dado`
  ou exemplos rotulados, **mesma assinatura** da futura chamada à API.
- `src/lib/precos.ts` — resultado sempre `{ valor, unidade, fonte, data, tipo }`
  + estado "sem cotação". Origens CONAB (mercado) / PGPM (piso) / Cepea (link).
- Tipos em `types.ts`: `InsightsRegionais`, `PrecoRef`, `CanalVenda`.

Fase 2 (backend): o front troca `insightsDaUF`/`precos` por **uma** chamada a
`/api/regiao/{uf}` (§5.6), **sem mudar a UI** — por isso as assinaturas são
estáveis desde já. Fallback ao local quando o backend estiver offline.

### 5.6 Endpoint único `/api/regiao/{uf}` (performance e escala do MVP)
Decisão de arquitetura: **o front NÃO orquestra 6 chamadas.** O backend monta o
bundle inteiro e devolve pronto, incluindo a síntese.

```
GET /api/regiao/{uf}?cultura=milho
        │
   FastAPI (determinístico, cacheável)
        ├── preço de mercado   ← conab_precos  (UF + cultura)
        ├── piso PGPM          ← conab_pgpm    (cultura + safra)
        ├── ZARC da UF         ← zarc          (já no Mongo, indexado)
        ├── produção           ← sigef_agregado
        ├── seguro             ← psr_agregado
        ├── canais             ← regra (PAA/PNAE + cooperativa)
        └── sintetizar(...)    ← §5.7 (compara preço × piso × canal)
        ▼
   { regiao, cultura, blocos[], sintese, meta:{ fontes, datas, degradado } }
```

Por que escala e é rápido no MVP:
- **1 request** por UF (não 6) → menos latência, menos CORS, front simples.
- **Determinístico** → resposta **cacheável** por horas (preço/PGPM mudam devagar);
  cache em memória por `(uf, cultura)` já basta para a demo.
- **Degrada por bloco** (doc-mestre §14): se faltar preço, aquele bloco vem
  `sem_dado` e `meta.degradado=true`; o endpoint **nunca** retorna 500 por isso.
- Usa os índices já criados (`zarc_join`, `psr_geo_cultura_ano`, etc.).

### 5.7 A Leitura do AgroPilot — o diferencial (determinística no MVP)
O que nenhum dashboard nem "ChatGPT agrícola" faz: **conectar preço de mercado ×
piso oficial × canal de compra pública numa única leitura com fonte.** No MVP ela
é **determinística** (função que compara e escreve), não precisa de LLM:

```python
def sintetizar(preco, pgpm, canais, seguro, cultura, uf):
    if preco and pgpm:
        rel = "acima" if preco.valor > pgpm.valor else "abaixo"
        frase_preco = (f"Em {uf}, {cultura} está sendo pesquisada a R$ {preco.valor} "
                       f"({preco.data}, CONAB), {rel} do piso garantido de "
                       f"R$ {pgpm.valor} (PGPM {pgpm.safra}).")
    elif pgpm:
        frase_preco = (f"O piso garantido para {cultura} é R$ {pgpm.valor} (PGPM). "
                       f"Preço de mercado ainda não disponível para {uf}.")
    else:
        frase_preco = f"Ainda sem cotação de {cultura} para {uf}."
    frase_canal = ("O PAA/PNAE costuma pagar prêmio à agricultura familiar — "
                   "vale checar o edital.") if tem_familiar(seguro) else ""
    return montar(frase_preco, frase_canal, limitacoes=[...])  # máx 4 frases, com fonte
```

Regras: só usa números presentes no bundle; expõe conflito/ausência; nunca "venda
agora". A **LLM entra depois** (prompt travado §9.3) só para reescrever essa
mesma frase em tom mais natural — o **conteúdo já é defensável sem ela**.

> **Frase-ouro do pitch (honesta e repetível):** *"O AgroPilot compara o preço de
> mercado com o piso oficial e aponta canais de compra pública que pagam prêmio à
> agricultura familiar. Tudo com fonte e data."*

---

## 6. Navegação e demais telas

### 6.1 BottomNav — nova hierarquia
Recomendação (3 abas, mais limpo no mobile, Mapa protagonista):
```
🗺️ Mapa  ·  🌱 Minha Safra  ·  💬 Assistente
```
(Alternativa com 4 abas: `Mapa · Preços · Minha Safra · Assistente`, se preços
virar visão própria. Em qualquer caso, **Mapa é a 1ª aba e a tela inicial**.)

- `src/app/page.tsx` e o fim do onboarding passam a redirecionar para `/mapa`.

### 6.2 Minha Safra (secundária)
Estado da propriedade + decisão do dia + próximo passo + avisos. Deixa de ser a
porta de entrada; continua como aba de acompanhamento (ligada ao loop §8).

### 6.3 Assistente (apoio, não protagonista)
- Chat com voz/texto/chips (existente). Respostas via resolvedor local honesto.
- Chips **comerciais**: "Compensa vender agora ou esperar?", "Qual canal paga
  mais pra agricultura familiar?", "Como funciona o PAA/PNAE?".
- Opcional: botão "Perguntar sobre esta região" no card do Mapa, levando ao
  Assistente com o contexto da UF.

---

## 7. Níveis de observabilidade (um produto, não dois)

Não existe "AgroPilot pequeno" e "AgroPilot grande". Existe **a mesma engine com
mais ou menos evidência**:

| Produtor | Fornece | O AgroPilot usa |
|---|---|---|
| **Familiar / pequeno** | município, cultura, área, solo, data de plantio | dados públicos (CONAB, ZARC, SIGEF, PSR, ANA) |
| **Médio / grande** | vários talhões, histórico, sensores, imagens, dados meteo próprios | o mesmo motor + mais evidência → análise mais fina |

Quanto mais dados, mais refinada a análise. **Robótica** (drone/rover) não é o
produto — é **uma das formas de obter evidência** para alimentar o loop (§8).

---

## 8. Loop preditivo e gêmeo digital (roadmap de inteligência)

### 8.1 Gêmeo digital simplificado
Estado vivo da propriedade: `localização · área · cultura · solo · estágio da
safra · histórico climático · condições atuais · riscos · decisões · eventos`.
Persiste em `seasons` (documento-mestre §5). É a fundação do loop.

### 8.2 Predição de **risco**, não de produtividade
Em vez de "sua fazenda produzirá 62 sc/ha" (frágil), prever **eventos de risco**:
```
Próximos 15 dias — RISCO DA SAFRA
Excesso hídrico   ███████░░░  (índice)
Déficit hídrico   ███░░░░░░░  (índice)
Janela inadequada ██░░░░░░░░  (índice)
```
O índice é **determinístico e explicável** (RiskEngine, documento-mestre §7.3:
veto → score, bandas de clima, encolhimento do histórico). **Não** é um ML
treinado em 24h. Se os dados históricos não sustentarem validação estatística,
chama-se **índice de risco baseado em evidências** — não "previsão com X% de
acurácia".

### 8.3 Simulador "E se?"
Como o motor é determinístico, roda cenários e mostra o **diff**:
```
                 10/10      20/10
Risco hídrico    baixo      médio
Janela ZARC      ✓          ✓
Exposição        menor      maior
```
Variável inicial recomendada: **data de plantio** (ZARC dá risco por decêndio →
mudar a data muda o risco de forma auditável, sem inventar). O sistema **não
escolhe** pelo produtor; mostra como a decisão altera o cenário.

### 8.4 Early Warning + próxima decisão
- **Early Warning:** identifica combinação de fatores (chuva acumulada +
  previsão + solo + estágio) que merece atenção → sugere **inspeção**, não
  "aplique produto X".
- **Próxima decisão:** máquina de estados da safra
  (`PLANEJAMENTO → PREPARAÇÃO → PLANTIO → DESENVOLVIMENTO → MANEJO → COLHEITA`)
  indica qual será a próxima decisão relevante. Transforma o app em copiloto de
  decisões, não chatbot.

---

## 9. IA: onde vive, onde morre (anti-"pato")

> **Princípio único:** *IA só existe onde há linguagem humana entrando ou saindo.
> Todo o resto é determinístico (lookup, comparação, agregação, cálculo). Na
> dúvida, é regra.*

"Pato" = IA espalhada em 10 lugares, medíocre em todos. "Produto" = IA concentrada
em 2–3 pontos de linguagem, excelente neles.

### 9.1 Onde a IA VIVE (linguagem humana)
| Ponto | Entrada/Saída | Papel |
|---|---|---|
| **Assistente — entrada** | texto livre do produtor ("compensa vender agora?") | extrai intenção/entidade (regionalismo, typo, "tá/tô") |
| **Diário — entrada** | "choveu demais, não plantei" | extrai eventos estruturados p/ o gêmeo digital |
| **Leitura do AgroPilot — saída** | EvidenceBundle / insights da UF | **sintetiza** os blocos em UMA leitura comercial/agronômica |

A **Leitura do AgroPilot** (bloco 1 do card do Mapa e resumo do Radar) é o maior
valor: nenhuma regra conecta evidências soltas numa narrativa. A IA costura
preço × piso × canais × produção numa frase que o produtor usa para decidir.

### 9.2 Onde a IA MORRE (determinístico)
Coroplético do mapa · ranking de produção · concentração de apólices · cálculo de
decêndio · comparação preço × piso · status dos cards · classificação de cultura ·
geração de alerta · próxima decisão (máquina de estados) · **qualquer decisão de
venda** · **previsão de preço futuro** · recomendação de defensivo.

### 9.3 Prompt travado (anti-pato) — para a Leitura do AgroPilot
```
Você transforma o bundle de dados em UMA leitura curta para o produtor.
REGRAS INVIOLÁVEIS:
1. NÃO invente números — todo número tem que estar no bundle.
2. NÃO invente fonte — toda afirmação aponta para um campo.
3. Se houver "sem_dado", mencione a ausência.
4. Se evidências conflitam (preço alto × piso baixo × canal), exponha o conflito.
5. NÃO dê ordem de venda ("venda agora"). NÃO receite defensivo.
6. NÃO confirme elegibilidade de programa público — diga "verifique na fonte".
7. Linguagem coloquial, direta, sem jargão. Máx 4 frases.
SAÍDA (JSON estrito): { resumo, evidencias_usadas, limitacoes }
```

### 9.4 Faseamento da IA: síntese determinística primeiro, LLM por último
A "Leitura do AgroPilot" (§5.7) **não depende de LLM no MVP**:
- **Fase 2:** `sintetizar()` **determinística e honesta** (compara os dados
  presentes; nunca inventa número) — no backend (`sintese.py`) e espelhada no
  front. É isto que vai à banca. O ponto de plug da LLM fica marcado em comentário.
- **Fase 3:** a LLM (prompt travado §9.3) só **reescreve** essa frase em tom mais
  natural — o conteúdo já é defensável sem ela.
- **Proibido em qualquer fase:** IA decorativa, IA decidindo venda, IA prevendo
  preço, número sem fonte.

### 9.5 Reframe para o pitch
> *"O AgroPilot não é um agrônomo nem um corretor de IA. É a camada de tradução
> entre o dado técnico/comercial oficial e a ação prática do produtor. O agrônomo
> continua agrônomo; a CONAB continua CONAB. A gente entrega o que faltava: isso
> no bolso, na linguagem de quem está no campo."*

---

## 10. MVP e ordem de construção

> ⚠️ **"Só front" era a FASE 1 — e ela já foi cumprida.** Parar no front puro é
> suicídio no pitch: o card de preço ficaria com dado de exemplo, e à pergunta
> "de onde veio esse preço?" a resposta seria "de um mock" — perda direta em
> *Uso e análise dos dados*. A **Fase 2 (backend servindo ≥ 3 dados reais) é
> obrigatória** e cabe no tempo (~6h30, §10.3).

### 10.1 Fase 1 — já entregue (front navegável)
- Front (Next + Tailwind): login, onboarding (1 pergunta/tela), Minha Safra,
  Radar (4 estados), Assistente (voz/texto/chips). Build passando.
- Correlação das 6 bases + testes; backend FastAPI com mock + consulta parcial.

### 10.2 Fase 2 — fechar os 3 furos (foco atual)
Prioridade por impacto no pitch:

| # | Entrega | Onde | ~Tempo | Impacto |
|---|---|---|---|---|
| 1 | Ingerir **PGPM** (tabela 26/27 real) + **CONAB preços** por UF | `correlacao/conab.py` → `conab_pgpm`, `conab_precos` | 2h | ⭐⭐⭐ sem isso o pitch cai |
| 2 | **Síntese determinística de verdade** (compara preço×piso×canal) | `back/app/core/sintese.py` + espelho local no front | 2h | ⭐⭐⭐ é o produto |
| 3 | Endpoint único **`/api/regiao/{uf}`** (bundle + cache + degrada) | `back/app/routes/regiao.py` | 1h | ⭐⭐⭐ liga front↔back |
| 4 | Aba **Mapa** = SVG estático clicável (sem pan/zoom) | front `mapa/` | 1h | ⭐⭐ devolve ~3h |
| 5 | Card **4 blocos visíveis** + "Ver mais" colapsado | front `mapa/` | 30min | ⭐⭐⭐ banca entende em 10s |
| 6 | Front consome `/api/regiao/{uf}` (fallback ao local) | front `lib/` | — | ⭐⭐⭐ |

**Total ≈ 6h30.** Fecha Furo 1 (dado real), Furo 2 (card enxuto), Furo 3 (mapa é
navegação, síntese é produto).

### 10.3 Fase 3 — depois (aprofundamento)
- **RiskEngine** + **EvidenceBundle** (documento-mestre §6, §7) e o loop §8.
- Camada **LLM** (prompt travado §9.3) reescrevendo a síntese já determinística.
- CEASA, PAA/PNAE como fontes; drill-down por município; pan/zoom no mapa.

### 10.4 O diferencial, em uma linha
> Enquanto os outros fazem **dados → recomendação**, o AgroPilot
> **compara preço de mercado × piso oficial × canal de compra pública**, com
> fonte e data em tudo, e IA só onde há linguagem humana.

---

## 11. Conformidade e limites (eliminatório na banca)
- **LGPD:** PII filtrada na entrada (documento-mestre §9); dado agregado por
  município/UF; nunca reidentificar pessoa.
- **Licença de dados:** CONAB/ZARC/SIGEF/PSR/ANA são públicas; **Cepea é link**,
  não cópia.
- **Legal agronômico:** não substitui responsável técnico (Lei 14.785/2023);
  defensivo exige receituário (art. 39). Não confirma elegibilidade de programa.
- **Comercial:** preço é **referência com data**, não recomendação de venda.
  Sem previsão de preço apresentada como certeza.

---

*Referências: `docs/documento-mestre-agropilot.md` (correlação, RiskEngine,
EvidenceBundle, workers), `docs/dicionario-de-dados.md` (bases), `CONTRATO_API.md`
(contrato front↔back), `arquitetura-front-and-end.md` (estratégia de paralelismo).*
