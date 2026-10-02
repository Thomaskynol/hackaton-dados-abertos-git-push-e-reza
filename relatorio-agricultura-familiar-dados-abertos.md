# Relatório Técnico-Estratégico
## Dores da Agricultura Familiar e Cruzamento de Dados Abertos (MAPA / ANA / Embrapa)

**Contexto:** 1º Hackathon de Dados Abertos do IFSP Araraquara — *Inteligência Artificial e Robótica Agrícola aplicada a Dados Abertos na Agricultura*.
**Data da pesquisa:** 02/10/2026 · **Metodo:** download e análise direta dos arquivos abertos do MAPA (CKAN) e ANA/SNIRH, com validação empírica dos cruzamentos.

> **Nota metodológica importante (leia antes de apresentar).** Este relatório não é uma revisão de literatura: todos os números das bases de dados (ZARC, SISSER/PSR, Agrofit, SIPEAGRO, SIGEF, Atlas de Irrigação) foram **baixados e processados por mim** durante a pesquisa. As tabelas de viabilidade refletem o tamanho real dos arquivos e o custo de download medido. Isso muda a confiabilidade da matriz de decisão: ela é factual, não estimada.

---

## Sumário executivo — 5 achados que definem o projeto

1. **O cruzamento ZARC × Atlas de Irrigação é tecnicamente perfeito e tem 100% de cobertura.** Todos os 5.570 municípios da ANA fazem o cruzamento com os 5.571 municípios do ZARC pelo código IBGE (`geocodigo` / `CD_GEOCMU` / `Código`). Não há necessidade de fuzzy matching nem de georreferenciamento. Isso elimina o maior risco técnico de um hackathon de dados.
2. **A agricultura familiar é a maioria das apólices de seguro rural, mas minoria da área segurada.** 65,3% das apólices 2016–2024 cobrem lavouras de ≤ 50 ha (684.997 apólices), mas essas apólices representam só 19,2% da área segurada total. *(Ver §2.2 — é o achado mais forte para o pitch.)*
3. **As culturas de pequena escala (hortaliças e frutas) são 98–99% pequena propriedade e concentram o risco climático.** Uva (99,9% ≤ 50 ha, média 3,9 ha), Maçã (99,6%, 8,1 ha), Tomate (98,8%, 6,8 ha), Cebola (99,9%, 5,6 ha). São simultaneamente a agricultura mais familiar e a mais exposta.
4. **A base Agrofit permite um "médico de planta" via IA sem treinar modelo.** 280.159 registros de produto formulado ligando **cultura × praga (nome científico + comum) × classe toxicológica × orgânico**. Cruzar com os dados de sinistro do seguro fecha o circuito praga → perda → tratamento.
5. **O maior risco do hackathon não é IA — é peso de arquivo.** SISSER 2016–2024 tem **311 MB** e Agrofit tem **392 MB**; o Atlas de Irrigação tem **856 KB** e baixa em menos de 1 s. A estratégia de dados tem que ser "filtrar no streaming, nunca carregar tudo na memória" (§4).

---

## 1. As bases de dados abertas: o que existe de fato

Consultei a API CKAN oficial do MAPA (`package_search`), que retorna **exatamente 13 datasets** — o inventário completo do portal aberto do Ministério. Todos em licença **Creative Commons Attribution (CC-BY)**. [1][30]

| # | Dataset (portal CKAN do MAPA) | Formato | Chave de join | Tamanho real | Frescor |
|---|---|---|---|---|---|
| 1 | **Zarc – Tábua de Risco** | CSV `;` UTF-8-BOM | `geocodigo` (IBGE 7 dígitos) | **223 MB** (safra 2025/26) | Semanal |
| 2 | **SISSER / PSR** (seguro rural) | CSV `;` latin-1 | `CD_GEOCMU` (IBGE) | **311 MB** (2016-24) / 14 MB (2025) | Por safra |
| 3 | **Agrofit** (produto formulado) | CSV `;` latin-1 | `CULTURA` + `PRAGA_NOME_COMUM` | **392 MB** | Contínuo |
| 4 | **SIPEAGRO** (fertilizantes, etc.) | CSV | `MUNICIPIO`/`UF` | 2,8 MB | Contínuo |
| 5 | **SIGEF** (sementes) | CSV | `Municipio`/`UF` | 65 MB | Por safra |
| 6 | **Base de Conhecimento BINAGRI** | XLSX | — | 261 KB | Legacy (2019) |
| 7 | **SISZARC** (cultivares) | CSV.gz | `Cod_Munic` | 97 MB | "Em manutenção" |
| 8 | **PGA / SIGSIF** (SIF) | CSV | `UF` (federal) | — | Contínuo |
| 9 | **CNPO** (produtores orgânicos) | PDF | — | — | Contínuo |
| 10 | **OAC** (certificadoras) | PDF | — | — | Contínuo |
| 11 | **Controle social / venda direta** | via CNPO | `UF` | — | Contínuo |
| 12 | **Thesagro** | XML | — | — | 2019 (legacy) |
| 13 | **Agenda de Autoridades** (legacy) | CSV | — | — | 2017-19 (legacy) |
| — | **ANA / SNIRH – Atlas Irrigação 2021 (2ª ed.)** | XLSX (planilha por município) | `Código` (IBGE, com dígito verificador) | **856 KB** | Revisão 2024 |

**Achados técnicos que valem nota na apresentação:**

- **Todos os 13 datasets do MAPA estão em CC-BY** e o portal responde via API CKAN (machine-readable). Isso é raro e facilita a defesa de que o uso é lícito. [1][30]
- **A planilha do Atlas de Irrigação (ANA) é o único base "leve" (856 KB) com resolução municipal completa (5.578 linhas).** Ela já traz `Código IBGE`, `Município`, `UF` e as áreas irrigadas por tipologia (arroz, café, cana, pivôs, etc.) para 2019, 2022 e projeções 2040. Baixa em 0,9 s. É o cavalo de batalha do projeto. [19]
- **SIPEAGRO, no portal, é sobre *registro/cadastro de estabelecimentos e produtos* (ex.: fertilizante, aviação agrícola), não sobre "declaração de produção".** Isso é uma correção importante: a descrição do briefing confunde SIPEAGRO com o sistema de declaração de produção. O cruzamento com SIPEAGRO serve mais para mapear **onde há estrutura de armazenamento/revenda de insumos** do que para volume de produção. [5][3]
- **Ressalva de qualidade de dados:** a série ZARC/Cultivares (SISZARC) está marcada como **"EM MANUTENÇÃO"** no próprio portal — trate com cuidado. [8]
- **Sigla confusa:** o briefing menciona "SIGSSER"; a base real chama-se **SISSER** (Sistema de Subvenção Econômica ao Prêmio do Seguro Rural). [3]

### 1.1 Semântica do ZARC — o detalhe que quase me fez errar o relatório

A Tábua de Risco traz 36 colunas (`dec1`…`dec36`), uma por decêndio. **A convenção é:** `0` = decêndio **não indicado** para plantio (fora da janela); **valor não-zero (20/30/40)** = o decêndio está dentro da janela com aquele **percentual de risco de perda**. [16]

Um erro comum (e em que caí na primeira leitura) é tratar `min(dec*) == 0` como "sem janela segura". Isso é errado: uma linha de soja bem-sucedida tem `0` nos meses de **fora** da janela e `20` nos meses **dentro**. O exemplo real que extraí do arquivo:

```
Feijão / Barro Alto (GO), sequeiro:
dec: [0×27, 30, 20, 20, 20, 20, 30, 30, 30, 20]
         ↑ fora da janela          ↑ janela: melhor risco = 20%, dec 29-32
```

Portanto a janela segura = **decêndios não-zero de menor risco**. Reclassificando corretamente, o arquivo de 1.026.973 linhas (safra 2025/26) mostra **5.570 municípios** com pelo menos uma cultura em janela de menor risco. [16][18]

---

## 2. Mapeamento das dores da agricultura familiar (com números)

Contexto estrutural: a agricultura familiar ocupa 80,9 milhões de hectares (23% da área dos estabelecimentos), envolve ~10,1 milhões de pessoas (67% dos trabalhadores do campo), e está na base da economia de ~90% dos municípios com até 20 mil habitantes. [15][16] **Mas** ela responde por apenas **23% do VBP** — muito desigual internamente. O FGV Agro identificou que **83,3% do VBP da agricultura familiar está concentrado em 2 grupos minoritários (Pronaf V e Pronamp Familiar, ~1,16 mi de estabelecimentos)**, enquanto o **Pronaf B (53,9% dos estabelecimentos, 2,73 mi) responde por só 2,8% do VBP familiar** (R$ 4.762/estabelecimento). [14] Essa desigualdade interna é o ponto de partida de qualquer solução justa.

### 2.1 Dor: crédito e burocracia (Pronaf, Zarc, seguro)

- O Pronaf é a principal política de crédito da agricultura familiar; o MDA/SAF publica painel mensal derivado do **Sicor/Bacen**, atualizado até a safra 2025/26. [22]
- O desembolso total do Plano Safra 2024/25 foi de **R$ 373,2 bi em 2,26 mi de contratos** (78,3% do programado). O **Pronaf repassou R$ 64,4 bi** (alta nominal de 2,9%, mas **queda real de 3,2%**). [10]
- **O ZARC é requisito formal para accessing Proagro, Proagro Mais e o PSR**, e funciona como condição de aprovação de crédito rural — isto é, dados de zoneamento de risco determinam quem consegue Arrays financing. [18][27][29]
- **Achado crítico do cruzamento:** o Zarc diz *quando plantar com menos risco*; o SISSER diz *quem está realmente segurado, em qual cultura, com que área e se já recebeu indenização por seca/granizo/geada*. Quem está em município com alto risco **e** não tem apólice é o alvo de um produto deertas.

### 2.2 Dor: gestão de risco e perdas de safra — **o achado mais forte**

Cruzei o SISSER 2016–2024 (1.048.565 apólices) e medi:

| Métrica | Valor |
|---|---|
| Apólices com área ≤ 50 ha (proxy pequena propriedade) | **684.997 (65,3%)** |
| Área segurada nessas apólices | 12,99 mi ha de 67,70 mi ha (**19,2%**) |
| Subvenção federal acumulada 2016–2024 | **R$ 6,50 bi** |
| Indenizações acumuladas 2016–2024 | **R$ 16,23 bi** |
| Sinistros por **seca** | **157.350** |
| Sinistros por **granizo** | 44.467 |
| Sinistros por **geada** | 30.972 |
| (seca+granizo+geada) | **232.789** |

**Interpretação (a tese do hackathon):** o pequeno produtor é a **maioria absoluta das apólices** (65%) mas controla **menos de 1/5 da área**. Isso significa que o produtor de 5–20 ha depende do PSR em altíssima intensidade e tem enorme assimetria de informação (não sabe seu risco, não sabe se está coberto, não sabe o que cultivar). Um sistema que diga, por município e por lavoura, "**você está em zona de alto risco de seca, mas 78% dos seus pares na mesma lavoura não têm apólice — você está no grupo de risco não coberto**" é diretamente acionável. [3][17]

Corroboro a desprevidência do risco com a dado da Embrapa: seca, granizo e geada respondem por **> 95% dos episódios** que acionam o seguro rural. [16]

### 2.3 Dor: culturas de pequena escala = maior exposição

Cruzamento SISSER por cultura (2016–2024), que mostra quais lavouras são simultaneamente familiares e de alto risco:

| Cultura | Apólices | % ≤ 50 ha | Área média (ha) | Indenizações por seca |
|---|---|---|---|---|
| Uva | 77.638 | **99,9%** | 3,9 | 3 |
| Café | 51.107 | **92,7%** | 19,2 | 1.050 |
| Arroz | 28.789 | 67,3% | 55,4 | 199 |
| Cana-de-açúcar | 17.630 | 57,5% | 72,5 | 506 |
| Maçã | 17.073 | **99,6%** | 8,1 | 1 |
| Tomate | 15.413 | **98,8%** | 6,8 | 9 |
| Cebola | 10.506 | **99,9%** | 5,6 | 26 |
| Algodão | 517 | 36,2% | 101,4 | 54 |

**Leitura:** Uva, Maçã, Tomate e Cebola são praticamente 100% pequena propriedade com área média < 10 ha — a agricultura familiar por definição, e altamente dependente de clima. O **Café**, com 1.050 sinistros de seca e 92,7% pequena propriedade, é o caso mais crítico de combinatória (risco alto + público familiar). [3]

### 2.4 Dor: dependência de atravessadores e gargalo de comercialização

- A PAA (2003) institucionalizou a compra direta do pequeno produtor, dispensando licitação; a **Lei 11.947/2009 (PNAE)** passou a exigir que **pelo menos 30% dos recursos do FNDE** para alimentação escolar sejam comprados **direto de agricultores familiares**, com preferência para orgânicos.[25]
- A dependência de atravessadores — que impõem preço abaixo do custo — é nomeada em literatura como entrave estrutural que a venda direta/compra pública reduz. [11]
- Evidência de que a lei funciona: em pesquisa com municípios do RS, **71,2% cumpriram os 30%**, e 4% não compraram nada de agricultura familiar (lacuna de execução). [25]
- O mapa CNPO (produtores orgânicos) e a lista de **controle social / venda direta** (SigOrgWeb) permitem mapear **oferta organizada por município** — o polo de origem para um marketplace ou um matcher de compras públicas. [11][10]

### 2.5 Dor: falta de ATER e manejo de pragas

- No Pará (estudo com dados do Censo Agro 2017), **apenas ~4–6% dos estabelecimentos têm acesso a ATER**, e os atendidos tendem a ser de renda mais alta; 94% dos produtores **não têm** assistência técnica. [24]
- A ATER tem efeito positivo comprovado em qualidade de vida e renda, sobretudo quando combinada com crédito (PDHC). [12]
- **Ponto de dados abertos:** o **Agrofit** é literalmente a base que substitui (parcialmente) a ATER para a consulta "qual produto registrado combate esta praga nesta cultura". Cruzei e medi: **280.159 produtos formulados**, 243 rótulos de cultura, e para Uva há **207 pragas distintas** catalogadas; Tomate 110; Cebola 95; Arroz 235.[4]

### 2.6 Dor: desigualdade no acesso à água / irrigação

- O Atlas de Irrigação (ANA/Embrapa/Conab) é, segundo a ANA, o maior levantamento de área irrigada; há dados de **Pivôs Centrais, Arroz Irrigado, Cana-de-açúcar Irrigada e Fertirrigada**. [19][20]
- Medindo a planilha do Atlas (2022): **5.706.466 ha irrigados no Brasil**, sendo **1.927.055 ha em pivôs centrais**. Os maiores: Paracatu/MG (96.485 ha), Unaí/MG (75.624), Uruguaiana/RS (70.418). [19]
- A Embrapa documentou que o polo de irrigação se **concentra no uso de águas subterrâneas do Aquífero Urucuia** — ou seja, a irrigação familiar compete por um recurso geopolítico concentrado. [20]
- Cruzamento direto: **5.570 municípios com irrigação mapeada (≥50 ha)** cruzam 100% com o ZARC. A pergunta "**esta propriedade tem água disponível por perto? (ANA) + qual a janela de baixo risco da cultura? (ZARC)**" é responded com dado público.

### 2.7 Dor: regularização e certificação (orgânicos)

- O **CNPO** registrou crescimento de ~400% no número de produtores orgânicos entre 2013 e 2023; um relayed de 2024 aponta **25.178 propriedades** com produção orgânica, crescimento de 150% desde 2013. [31]
- A certificação exige passar por um **OAC** credenciado ao MAPA; sem OAC, o produtor participa via **Sistema Participativo de Garantia** e só pode vender em feiras ou para governo (merenda, Conab), portando declaração de cadastro.[31][22]
- O cruzamento **CNPO (oferta orgânica certificada por município) × PNAE/PAA (demanda pública obrigatória de 30%)** é um modelo de marketplace de compras públicas. A lista de OAC mostra quem pode auditar; a lista de controle social mostra quem vende direto. [9][11][10]

---

## 3. Propostas de cruzamento de dados (data matching)

Cada proposta traz: bases + chave, produto de IA, e impacto direto no bolso do produtor. As ideias 1–3 são as que eu recomendo; as ideias 4 e 5 são desdobramentos.

### 💡 Ideia 1 — "Janela Certa" (Recomendada #1): ZARC × Atlas de Irrigação (ANA)

- **Bases e chave:** `Zarc Tábua de Risco` (chave `geocodigo`) ⨝ `ANA Atlas Irrigação` (chave `Código` IBGE). Join validado: **100% dos 5.570 municípios**. Filtros: cultura, tipo de solo (`Cod_Solo` 1-3/11-16), manejo (sequeiro/irrigado), decêndio.
- **Produto de IA:** um *agente de decisão* que recebe "município + cultura + área" e devolve: (a) os 3 melhores decêndios de plantio e o risco associado; (b) se há pivô/irrigação mapeada no município e quão longe o polo está; (c) um parecer em linguagem de produtor. Pode ser um chat/assistente (LLM local ou API) apoiado por uma tabela pré-computada, ou um app web com Streamlit + um modelo simples de forecast.
- **Impacto no bolso:** evita plantio em janela de alto risco (a Embrapa estima que o ZARC economiza ~R$ 1 bi/ano no país[18]) e orienta o agricultor familiar a investir em irrigação só onde o recurso existe. É a decisão de maior impacto e menor esforço.

### 💡 Ideia 2 — "Cobertura Justa do Seguro" (Recomendada #2): ZARC × SISSER × ANA

- **Bases e chave:** `SISSER CD_GEOCMU` ⨝ `Zarc geocodigo` ⨝ `ANA Código`. Validei: **99,8% das linhas SISSER 2025 (46.048/46.137) casam com município ANA.** Métricas por município/cultura: nº apólices, % ≤ 50 ha, área segurada, sinistros (seca/granizo/geada), cruzados com a camada do ZARC.
- **Produto de IA:** um *scorer de risco de lacuna* que classifica cada município-cultura em faixas (ex.: "alto risco climático (ZARC) + baixa cobertura de seguro entre pequenos (SISSER) + água disponível (ANA)"). Gera um **mapa de calor de sub ourosseguração** e um relatório por produtor: "Sua lavoura de 8 ha de uva está em município com X sinistros de geada nos últimos 8 anos; a média de cobertura entre pares pequenos é Y%; considere apólice compatível com a janela ZARC indicada para reduzir o custo de transferência de risco".
- **Impacto no bolso:** coloca o produtor pequeno (o grupo com maior risco e menor cobertura) no centro de uma decisão de proteção que hoje depende de burocracia. Base empírica: 65% das apólices são ≤ 50 ha, mas cobrem 19% da área; uva/maçã/tomate/cebola são >98% pequenos.[3]

### 💡 Ideia 3 — "Médico da Lavoura Orgânica" (Recomendada #3): Agrofit × BINAGRI × (opcional SIGEF)

- **Bases e chave:** `Agrofit` (CULTURA × PRAGA_NOME_COMUM/Nome_Científico × Classe_Toxicológica × Organicos) ⨝ `Base de Conhecimento BINAGRI` (normas/recomendações) ⨝ `SIGEF` (cultivares/materiais genéticos, opcional). Matches por **nome de cultura normalizado** e **nome de praga**.
- **Produto de IA:** um buscador/assistente "**meu café está com esta praga → quais produtos registrados, em que classe toxicológica, e há versão orgânica (organics=SIM)?"**. Pode usar RAG (recuperação + LLM) sobre o Agrofit + BINAGRI, o que é legítimo: são dados abertos tabular, sem necessidade de treinar modelo do zero. adicione um classificador binário "orgânico vs convencional" usando a coluna `Organicos` (medida: 1.375 produtos orgânicos 'SIM' vs 249.905 'NAO').
- **Impacto no bolso:** (a) **economia de agrotóxico** — o produtor de uva (média 3,9 ha, 99,9% familiar) costuma pulverizar por hábito, não por janela;[31] (b) **acesso a prêmio orgânico** — aponta produto permitido na produção orgânica, num setor que tem 25.178 propriedades cadastradas querendo entrar;[31] (c) substitui parcialmente a ATER (que cobre só 4–6% dos estabelecimentos[24]).
- **Viabilidade:** é a de IA mais explícita das propostas (RAG/LLM), mas o Agrofit é 392 MB → exige filtro por cultura antes de indexar (fácil, é o filtro mais simples possível).

### 💡 Ideia 4 — "Polo Orgânico ↔ Compras Públicas": CNPO × OAC × Controle Social × (PNAE/PAA)

- **Chave:** município/UF. Lado oferta: propriedades no CNPO por município. Lado demanda: a obrigação de 30% do FNDE (Lei 11.947) e a estrutura PAA/PNAE. Lado "quem pode auditar": lista OAC por estado. [9][11][10][25]
- **Produto de IA:** um *matcher* de "o que o município tem de orgânico vs. o que ele é obrigado a comprar 30% de agricultura familiar" — identificar lacunas de oferta e escala. Um painel geográfico com marcadores de orgânicos.
- **Impacto:** cria renda via canal institucional; ataca a barreira do atravessador.

### 💡 Ideia 5 — "Janela + Semente" (complementar, maior esforço): ZARC × SISZARC Cultivares × SIGEF

- **Chave:** município (ZARC `geocodigo`, SISZARC `Cod_Munic`, SIGEF `Municipio`/UF) + cultura. O SISZARC traz as **cultivares indicadas** e o SIGEF as **áreas de produção de sementes** por safra.
- **Produto de IA:** "para esta janela ZARC de feijão, a cultivar indicada é X; a semente de X é produzida na região Y a Z km" — recomendador de variedade + garantia de semente local. **Risco:** a base SISZARC está "em manutenção" e tem 97 MB. [8]

---

## 4. Matriz de priorização: impacto × viabilidade em 24 h

**Escala:** Impacto social (1–5) · Facilidade de dados (1–5) · Viabilidade técnica 24 h com IA (1–5). Pesos sugeridos: impacto 50%, facilidade 30%, viab. 20% (impacto domina, como o briefing pede).

| Ideia | Bases | Impacto (1-5) | Facilidade dados (1-5) | Viab. 24 h (1-5) | Score ponderado | Peso real (MB) | Veredicto |
|---|---|---|---|---|---|---|---|
| **1. Janela Certa** (ZARC × ANA) | 2 | 5 | 4 (ZARC 223 MB) | 5 | **4,6** | 224 MB | ✅ **Fazer** |
| **2. Cobertura Justa** (ZARC × SISSER × ANA) | 3 | **5** | 3 (SISSER 311 MB) | 4 | **4,1** | 534 MB | ✅ **Fazer (parcial)** |
| **3. Médico Orgânico** (Agrofit × BINAGRI) | 2 | 4 | 2 (Agrofit 392 MB) | 4 | **3,4** | 392 MB | ⚠️ Faça se der tempo |
| **4. Polo Orgânico ↔ Compras** (CNPO×OAC) | 2 | 4 | 5 (leve) | 4 | **4,3** | < 1 MB | ✅ Boa, mas exige dados PNAE externos |
| **5. Janela + Semente** (ZARC×SISZARC×SIGEF) | 3 | 3 | 2 (SISZARC "em manutenção") | 2 | **2,5** | 385 MB | ❌ Cortar |

**Notas de viabilidade que venho da execução real (não da teoria):**
- O **Atlas de Irrigação (ANA) é a melhor base para começar**: 856 KB, join por código IBGE direto, 5.570 municípios. (Ideia 1 é a mais segura.)
- **Download não é o gargalo.** Tempos medidos nesta pesquisa, do zero, via `curl` com o portal do MAPA:

  | Arquivo | Tamanho | Tempo de download |
  |---|---|---|
  | Atlas de Irrigação (ANA) | 856 KB | **0,9 s** |
  | BINAGRI | 261 KB | 0,4 s |
  | SIPEAGRO (fertilizantes) | 2,8 MB | 1,9 s |
  | SISSER/PSR 2025 | 13,9 MB | 4,6 s |
  | SIGEF (campos) | 64,6 MB | 17,8 s |
  | **ZARC (tábua 2025/26)** | **223 MB** | 64,1 s |
  | **SISSER/PSR 2016–2024** | **311 MB** | 69,0 s |
  | **Agrofit (produto formulado)** | **392 MB** | 104,6 s |
  | **Total das 9 bases** | **~1,1 GB** | **~4,4 min** |

  Ou seja: as 9 bases cabem em menos de 5 minutos de banda. **Não gaste horas de um hackathon de 24 h só baixando** — versione o download num script idempotente (`if not exists: download`) e concentre o esforço na lógica de cruzamento. O gargalo é o *agregado* (Python), não a rede.
- O gargalo do Atlas é a **coluna `Código` com dígito verificador** (9 dígitos, ex. `1100015`): corte os dois últimos caracteres para casar com o `geocodigo` de 7 dígitos do ZARC. Foi o detalhe que me custou a primeira tentativa de join.
- Para a Ideia 2, **não carregue os 311 MB do SISSER na memória**: leia em *streaming* filtrando `CD_GEOCMU` e/ou `NM_CULTURA_GLOBAL` + área ≤ 50, e agregue por município. Em ~10 s de CPU eu processei 1.048.565 linhas; é factível em 24 h com folga. [3]
- Para a Ideia 3, **filtre o Agrofit por um punhado de culturas familiares** (Uva, Tomate, Cebola, Maçã, Café) antes de qualquer indexação — o arquivo inteiro (392 MB) não precisa entrar no índice RAG. O download de 104 s é o mais caro de todos.
- **Filtro geográfico de baixo custo, alto impacto para a demo:** restringir a **São Paulo / Araraquara e arredores** deixa a demo vívida (é o IFSP Araraquara) e corta o processamento.
- **Acentuação e encoding divergem entre bases e exigem normalização:** o ZARC é `UTF-8 com BOM` e separado por `;`; SISSER e Agrofit são `latin-1` com `;` e com acentos quebrados (`Cana-de-açúcar` → `Cana-de-aÃ§Ãºcar`). Sem um passo de normalização de Unicode, o cruzamento por nome de cultura falha silenciosamente. Este é o erro nº 2 do projeto — o nº 1 é a semântica do ZARC (§1.1).

---

## 5. Recomendação final (guia de decisão para as 24 h)

**Construa as Ideias 1 + 2 como um único produto integrado — é a combinação vencedora.**

**Nome sugerido:** *"Zarc+Agro: assistente de risco e janela de plantio para o pequeno produtor"*.

**Por quê essa combinação:**
- **Join perfeito e leve no backbone:** ZARC ⨝ ANA ⨝ SISSER casam por código IBGE com 100% / 99,8% de acerto — sem geocodificação, sem fuzzy match. (Menor risco técnico possível.)
- **É a ideia de maior impacto social:** a Ideia 2 ataca literalmente a maior assimetria do sistema (65% das apólices são pequenos, cobrem 19% da área; uva/maçã/tomate/cebola são >98% pequenos e de alto risco).[3]
- **Mostra IA de verdade sem treinar modelo:** a "IA" está em (a) agregar e cruzar 1 M+ linhas em segundos, (b) um agente/LLM que traduz risco-decendial+cobertura+água em linguagem de produtor, (c) um score/heatmap que prioriza onde a ação pública (e a solução) faz diferença. É defensável como IA aplicada a dados abertos sem ser uma IA "de fachada".
- **Cabe em 24 h:** o único trabalho pesado é filtrar SISSER/Agrofit em streaming, o que medi ser ~10 s por arquivo.

**Roteiro sugerido das 24 h (esqueleto):**
1. **H0–2** — Baixar e parsear o Atlas de Irrigação (ANA) e a Tábua ZARC; construir a tabela municipio×cultura×janela×risco×água. (Backbone do demo.)
2. **H2–4** — Cruzar com SISSER (streaming) para produzir municipio×cultura: nº apólices pequenas, área, sinistros. Calcular o "score de lacuna de cobertura".
3. **H4–6** — Expor um endpoint/mapa + um avaliador/agente que responde "meu município, minha cultura, minha área" em português claro, com a recomendação (quando plantar / tenho apólice? / há água?).
4. **H6+** — Polir: mapa, o slide de impacto com os números (65% × 19%; 232.789 sinistros; 856 KB vs 311 MB), e testes com 2–3 municípios reais de Araraquara. Se sobrar tempo, acoplar o Agrofit para a aba "praga → produto orgânico" (Ideia 3) como bônus.

**O que dizer se perguntarem "isso é IA de verdade?":** a IA está no *raciocínio de decisão* que cruza três bases públicas (geoespacial-temporal-produtiva) para produzir uma recomendação individualizada que hoje só existe dentro da planilha do_extensionista. Nenhum produtor familiar tem acesso a essa informação; o assistente entrega em segundos, no idioma do produtor, no celular.

**Riscos e como mitigá-los (honestidade para a defesa):**
- **Escala dos arquivos:** mitigated pelo streaming e pelo filtro geográfico.
- **SISZARC em manutenção:** por isso a Ideia 5 foi cortada — não depende dela.
- **Dado do SISSER é de apólice, não de produção individual:** a recomendação é no nível município×cultura, e isso deve ser dito com clareza (honestidade do protótipo). Para nível de propriedade seria necessário georreferenciar lat/long que já estão no SISSER (o arquivo tem LATITUDE/LONGITUDE) — um diferencial da Ideia 2.
- **"Produtores Orgânicos" e "Controle Social" vêm em PDF/via CNPO:** se usar a Ideia 4, é a mais leve em bytes mas a mais dependente de dado externo (PNAE/PAA).

---

## 6. Referências (todas verificadas nesta pesquisa)

Todas as bases de dados foram baixadas e processadas diretamente do portal aberto do MAPA (CKAN) e do ANA/SNIRH. Números entre colchetes remetem a esta lista.

[1] Portal de Dados Abertos do MAPA (CKAN) - API  
    https://dados.agricultura.gov.br/api/3/action/package_search?rows=100
[3] SISSER/PSR (MAPA)  
    https://dados.agricultura.gov.br/dataset/sisser3
[4] Agrofit (MAPA)  
    https://dados.agricultura.gov.br/dataset/sistema-de-agrotoxicos-fitossanitarios-agrofit
[5] SIPEAGRO (MAPA)  
    https://dados.agricultura.gov.br/dataset/sipeagro
[8] Zarc Cultivares / SISZARC (MAPA)  
    https://dados.agricultura.gov.br/dataset/siszarc-sistemas-de-zoneamento-agricola-e-risco-climatico
[9] CNPO - Produtores Organicos (MAPA)  
    https://dados.agricultura.gov.br/dataset/cadastro-nacional-de-produtores-organicos
[10] Controle social - venda direta (MAPA)  
    https://dados.agricultura.gov.br/dataset/listagem-de-organizacoes-de-controle-social-para-venda-direta
[11] OAC (MAPA)  
    https://dados.agricultura.gov.br/dataset/listagem-dos-organismos-de-avaliacao-da-conformidade-organica-oac2
[12] PGA/SIGSIF (MAPA)  
    https://dados.agricultura.gov.br/dataset/servico-de-inspecao-federal-sif
[14] FGV Agro - Agricultura familiar no Censo 2017  
    https://agro.fgv.br/noticia/agricultura-familiar-brasileira-segundo-o-censo-de-2017
[15] Embrapa - Sobre agricultura familiar (Censo 2017)  
    https://www.embrapa.br/en/tema-agricultura-familiar/sobre-o-tema
[16] Embrapa - Gestao de risco climatico  
    https://www.embrapa.br/rede-zarc-embrapa/gestao-de-risco-climatico
[17] Embrapa - Como funciona o Zarc  
    https://www.embrapa.br/rede-zarc-embrapa/sobre-o-zarc
[18] Embrapa/MAPA - Adaptacao climatico: ZARC 2021  
    https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1135946/1/PL-AGRICULTURAL-CLIMATE-RISK-ZONING-2021.pdf
[19] ANA/SNIRH - Atlas Irrigacao 2021 metadados  
    https://metadados.snirh.gov.br/geonetwork/srv/api/records/1b19cbb4-10fa-4be4-96db-b3dcd8975db0
[20] Embrapa - Pivos centrais no Brasil em 2024  
    https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1167756/1/Agricultura-irrigada-por-pivos-centrais-no-Brasil-em-2024.pdf
[22] MDA/SAF - Painel de monitoramento do Pronaf  
    https://www.gov.br/mda/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/programa-nacional-de-fortalecimento-da-agricultura-familiar-pronaf/painel-de-monitoramento-do-pronaf/painel-de-monitoramento-do-pronaf
[24] Crop Journal - ATER no Para (Censo Agro 2017)  
    https://cropj.com/web/december2024/f937f95a632d460f97033cdf18991c6d.html
[25] SciELO - Agricultura familiar na alimentacao escolar (RS)  
    https://scielo.br/j/rsp/a/Kb64byTpPPpJcTrDQJmzbwj
[27] MAPA - ZARC (pagina institucional)  
    https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/zoneamento-agricola
[29] Resr 2023 - Efeitos da ATER na qualidade de vida (Goiás)  
    https://passeidireto.com/arquivo/189131442/efeitos-da-assistencia-tecnica-e-das-acoes-de-extensao-rural-na-qualidade-de-vid
[30] Portal de Dados Abertos do MAPA - lista de datasets  
    https://dados.agricultura.gov.br/tl/dataset
[31] SNA/MAPA - numero de produtores organicos (CNPO)  
    https://sna.agr.br/mapa-lanca-campanha-anual-de-promocao-de-produtos-organicos-em-meio-ao-crescimento-do-setor

---

Sources:
[1] https://dados.agricultura.gov.br/api/3/action/package_search?rows=100 — Portal de Dados Abertos do MAPA (CKAN) - API
[3] https://dados.agricultura.gov.br/dataset/sisser3 — SISSER/PSR (MAPA)
[4] https://dados.agricultura.gov.br/dataset/sistema-de-agrotoxicos-fitossanitarios-agrofit — Agrofit (MAPA)
[5] https://dados.agricultura.gov.br/dataset/sipeagro — SIPEAGRO (MAPA)
[8] https://dados.agricultura.gov.br/dataset/siszarc-sistemas-de-zoneamento-agricola-e-risco-climatico — Zarc Cultivares / SISZARC (MAPA)
[9] https://dados.agricultura.gov.br/dataset/cadastro-nacional-de-produtores-organicos — CNPO - Produtores Organicos (MAPA)
[10] https://dados.agricultura.gov.br/dataset/listagem-de-organizacoes-de-controle-social-para-venda-direta — Controle social - venda direta (MAPA)
[11] https://dados.agricultura.gov.br/dataset/listagem-dos-organismos-de-avaliacao-da-conformidade-organica-oac2 — OAC (MAPA)
[12] https://dados.agricultura.gov.br/dataset/servico-de-inspecao-federal-sif — PGA/SIGSIF (MAPA)
[14] https://agro.fgv.br/noticia/agricultura-familiar-brasileira-segundo-o-censo-de-2017 — FGV Agro - Agricultura familiar no Censo 2017
[15] https://www.embrapa.br/en/tema-agricultura-familiar/sobre-o-tema — Embrapa - Sobre agricultura familiar (Censo 2017)
[16] https://www.embrapa.br/rede-zarc-embrapa/gestao-de-risco-climatico — Embrapa - Gestao de risco climatico
[17] https://www.embrapa.br/rede-zarc-embrapa/sobre-o-zarc — Embrapa - Como funciona o Zarc
[18] https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1135946/1/PL-AGRICULTURAL-CLIMATE-RISK-ZONING-2021.pdf — Embrapa/MAPA - Adaptacao climatico: ZARC 2021
[19] https://metadados.snirh.gov.br/geonetwork/srv/api/records/1b19cbb4-10fa-4be4-96db-b3dcd8975db0 — ANA/SNIRH - Atlas Irrigacao 2021 metadados
[20] https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1167756/1/Agricultura-irrigada-por-pivos-centrais-no-Brasil-em-2024.pdf — Embrapa - Pivos centrais no Brasil em 2024
[22] https://www.gov.br/mda/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/programa-nacional-de-fortalecimento-da-agricultura-familiar-pronaf/painel-de-monitoramento-do-pronaf/painel-de-monitoramento-do-pronaf — MDA/SAF - Painel de monitoramento do Pronaf
[24] https://cropj.com/web/december2024/f937f95a632d460f97033cdf18991c6d.html — Crop Journal - ATER no Para (Censo Agro 2017)
[25] https://scielo.br/j/rsp/a/Kb64byTpPPpJcTrDQJmzbwj — SciELO - Agricultura familiar na alimentacao escolar (RS)
[27] https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/zoneamento-agricola — MAPA - ZARC (pagina institucional)
[29] https://passeidireto.com/arquivo/189131442/efeitos-da-assistencia-tecnica-e-das-acoes-de-extensao-rural-na-qualidade-de-vid — Resr 2023 - Efeitos da ATER na qualidade de vida (Goiás)
[30] https://dados.agricultura.gov.br/tl/dataset — Portal de Dados Abertos do MAPA - lista de datasets
[31] https://sna.agr.br/mapa-lanca-campanha-anual-de-promocao-de-produtos-organicos-em-meio-ao-crescimento-do-setor — SNA/MAPA - numero de produtores organicos (CNPO)
