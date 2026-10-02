# Dicionário das bases de dados

Pasta `base de dados/` (ignorada no git — arquivos pesados, ~680MB).
Separador `;`, encoding latin1 (acentos quebram se ler como UTF-8).

## 1. `agrofitprodutosformulados.csv` — 1,47M linhas

Cada linha = um uso autorizado (produto × cultura × praga). Mesmo produto repete N linhas.

| Coluna | Significado |
|---|---|
| NR_REGISTRO | Nº registro produto no MAPA |
| MARCA_COMERCIAL | Nome comercial produto formulado |
| FORMULACAO | Tipo formulação (EC, WP, ou biológico ex: Nematóides vivos) |
| INGREDIENTE_ATIVO | IA + grupo químico + concentração |
| TITULAR_DE_REGISTRO | Empresa detentora registro |
| CLASSE | Classe agronômica (Herbicida, Inseticida, Fungicida, Agente Biológico...) |
| MODO_DE_ACAO | Sistêmico/contato etc. Vazio em biológicos |
| CULTURA | Cultura autorizada. "Todas as culturas" = amplo espectro |
| PRAGA_NOME_CIENTIFICO | Espécie-alvo nome científico |
| PRAGA_NOME_COMUM | Espécie-alvo nome popular |
| EMPRESA_PAIS_TIPO | Cadeia produtiva: empresa + país + papel (FORMULADOR, MANIPULADOR, FABRICANTE) |
| CLASSE_TOXICOLOGICA | Toxicidade humana (nova: Não Classificado, Categoria 1–5) |
| CLASSE_AMBIENTAL | Periculosidade ambiental (I–IV) |
| ORGANICOS | SIM/NAO p/ agricultura orgânica |
| SITUACAO | TRUE = registro vigente |

Sem dicionário oficial. Fonte: <https://dados.agricultura.gov.br/dataset/sistema-de-agrotoxicos-fitossanitarios-agrofit>. Acima inferido do domínio + valores reais.

## 2. `agrofitprodutostecnicos.csv` — 3k linhas

Produto técnico (matéria-prima, não vai ao campo — sem cultura/praga).

| Coluna | Significado |
|---|---|
| NUMERO_REGISTRO | Nº registro produto técnico |
| PRODUTO_TECNICO_MARCA_COMERCIAL | Nome comercial produto técnico |
| INGREDIENTE_ATIVO(GRUPO_QUIMICI)(CONCENTRACAO) | IA + grupo químico + teor (g/kg) |
| CLASSE | Classe agronômica |
| TITULAR_REGISTRO | Detentor registro |
| EMPRESA_\<PAIS\>_TIPO | Fabricantes por país + papel (FABRICANTE) |
| CLASSIFICACAO_TOXICOLOGICA | Toxicidade humana (I = extremamente tóxico, escala antiga) |
| CLASSIFICACAO_AMBIENTAL | Periculosidade ambiental (I–IV) |

## 3. `dados-abertos-tabua-de-risco-safra-2026-2027.csv` — 957k linhas

ZARC: janela plantio por município/cultura.
Dicionário oficial (PDF): <https://dados.agricultura.gov.br/dataset/6d3d141c-885e-41a4-ab7f-dc8ff323b96f/resource/bebb0ebb-bc75-460c-b900-a7a1ebd87bee/download/dicionario-de-dados-tabua-de-risco-2026.pdf>

| Coluna | Significado |
|---|---|
| Nome_cultura | Cultura zoneada |
| SafraIni / SafraFin | Ano inicial/final safra (2026/2027) |
| Cod_Cultura | Código cultura zoneada |
| Cod_Ciclo | 13 Perene, 19 Semiperene, 20–26 Grupos I–VI |
| Cod_Solo | 1 Arenoso, 2 Textura Média, 3 Argiloso, 11–16 AD1–AD6 |
| geocodigo | Código IBGE município |
| UF / municipio | Sigla UF / nome município |
| Cod_Clima / Nome_Clima | 0 Não se aplica, 1–3 frio, 4 Semiárido, 5 Ameno, 6 Quente, 7 Tropical, 8–9/11 Subtropical |
| Cod_Outros_Manejos / Nome_Outros_Manejos | 1 Sequeiro, 2 Irrigado, 3 Irrigado c/ controle geada |
| Produtividade | Classificação por produtividade |
| Cod_NM | Nível manejo 1–4 |
| Cod_Munic | Código município no SICOR (crédito rural/Proagro) |
| Cod_Meso / Cod_Micro | Códigos IBGE meso/microrregião |
| Portaria | Número + data portaria Zarc no DOU |
| dec1–dec36 | Risco/aptidão plantio por decêndio (36 períodos de 10 dias no ano) |

## 4. `dados_abertos_psr_2025csv.csv` — 46k linhas

Subvenção seguro rural (SISSER).
Dicionário oficial (PDF): <https://dados.agricultura.gov.br/dataset/baefdc68-9bad-4204-83e8-f2888b79ab48/resource/2c5c55d0-1473-4749-b08f-cfaf887a9fa3/download/dicionariodedados-sisser.pdf>

| Coluna | Significado |
|---|---|
| NM_RAZAO_SOCIAL | Seguradora emissora |
| CD_PROCESSO_SUSEP | Código produto na SUSEP |
| NR_PROPOSTA / ID_PROPOSTA | Proposta na seguradora / identificador no SISSER |
| DT_PROPOSTA | Data contratação proposta |
| DT_INICIO_VIGENCIA / DT_FIM_VIGENCIA | Início/fim cobertura |
| NM_SEGURADO | Nome produtor segurado |
| NR_DOCUMENTO_SEGURADO | CPF/CNPJ segurado |
| NM_MUNICIPIO_PROPRIEDADE / SG_UF_PROPRIEDADE | Município/UF propriedade |
| LATITUDE / LONGITUDE | Coordenadas texto original |
| NR_GRAU_LAT / NR_MIN_LAT / NR_SEG_LAT | Grau/minuto/segundo latitude |
| NR_GRAU_LONG / NR_MIN_LONG / NR_SEG_LONG | Grau/minuto/segundo longitude |
| NR_DECIMAL_LATITUDE / NR_DECIMAL_LONGITUDE | Decimais derivadas (fora do dicionário oficial) |
| NM_CLASSIF_PRODUTO | Tipo seguro |
| NM_CULTURA_GLOBAL | Cultura/atividade segurada |
| NR_AREA_TOTAL | Área total segurada |
| NR_ANIMAL | Nº animais (pecuária) |
| NR_PRODUTIVIDADE_ESTIMADA / NR_PRODUTIVIDADE_SEGURADA | Produtividade estimada / coberta |
| NivelDeCobertura | Nível cobertura seguro |
| VL_LIMITE_GARANTIA | Valor segurado |
| VL_PREMIO_LIQUIDO | Prêmio líquido |
| PE_TAXA | Percentual taxa prêmio |
| VL_SUBVENCAO_FEDERAL | Parte prêmio paga governo |
| NR_APOLICE | Número apólice na seguradora |
| DT_APOLICE / ANO_APOLICE | Data/ano apólice |
| CD_GEOCMU | Geocódigo IBGE município |
| VALOR_INDENIZAÇÃO | Indenização paga em sinistro |
| EVENTO_PREPONDERANTE | Causa sinistro (seca, geada, granizo...) |

## 5. `sigefcamposproducaodesementes.csv` — 610k linhas

Inscrição campo produção comercial (Lei 10.711/2003).
Dicionário oficial v2.1 (PDF): <https://dados.agricultura.gov.br/dataset/c7784a6e-f0ec-4196-a1ce-1d2d4784a58e/resource/0ac82d3a-2a2c-4b80-a7d9-1af685b6865f/download/dicionario_de_dados___cgsm_12.12.2023_v2.1.pdf>

| Coluna | Significado |
|---|---|
| Safra | Safra plantio/colheita (ex 2019/2020) |
| Especie | Espécie vegetal |
| Categoria | Genética, Básica, C1, C2, S1, S2 |
| Cultivar | Cultivar produzida |
| Municipio / UF | Localização campo |
| Status | Recebido/Declarado (genética), Homologado, Inscrito, Aprovado |
| Data do Plantio / Data de Colheita | Datas campo |
| Area | Hectares |
| Producao bruta | Toneladas recebidas na UBS |
| Producao estimada | Toneladas estimadas na inscrição |

## 6. `sigefdeclaracaoareaproducao.csv` — 262k linhas

Reserva semente uso próprio (Portaria MAPA 538/2022). Mesmo dicionário item 5.

| Coluna | Significado |
|---|---|
| TIPOPERIODO | Tipo período (= safra) |
| PERIODO | Safra plantio/colheita |
| AREATOTAL | Hectares propriedade |
| MUNICIPIO / UF | Localização área |
| ESPECIE / CULTIVAR | Reservadas |
| AREAPLANTADA | Hectares cultivados c/ cultivar |
| AREAESTIMADA | Hectares pretende plantar safra seguinte |
| QUANTRESERVADA | Kg semente reservada |
| DATAPLANTIO | Data plantio |

## 7. `_ANA_AtlasIrrigacao_AreaAtualePotencial_Mun_UF.xlsx`

Abas `Atlas_mun` (header linha 7) e `Atlas_UF` (linha 7). Valores hectares, ano-base 2019.
Sem dicionário coluna-a-coluna. Docs: <https://www.ana.gov.br/atlasirrigacao/> e <https://metadados.snirh.gov.br/geonetwork/srv/api/records/1b19cbb4-10fa-4be4-96db-b3dcd8975db0>.
Colunas verificadas no arquivo real.

| Coluna | Significado |
|---|---|
| Código | IBGE município (na UF: Região + sigla + nome) |
| Município / UF | Nomes |
| Arroz Inundado | Arroz irrigado por inundação |
| Café | Café irrigado |
| Cana-de-Açúcar Irrigada | Cana c/ irrigação plena (água manancial) |
| Outras Culturas em Pivôs Centrais | Grãos/anuais em pivô exceto arroz/café/cana |
| Pivôs Centrais - Total | Área equipada pivô (inclui sobreposição) |
| Outras culturas e sistemas | Gotejo, aspersão convencional, sulco... |
| Área Total Irrigada | Soma c/ água mananciais |
| Cana-de-Açúcar Fertirrigada | Vinhaça/reúso — não conta água manancial |
| Área Total (Irrigada e Fertirrigada) | Soma total |
| Grupo Predominante no Município | Tipologia dominante (só aba mun) |
| Sistema Predominante no Município | Método dominante (só aba mun) |
| AAI com água superficial em sequeiro / em pastagem / subterrânea | Área adicional irrigável por fonte/uso |
| AAI - Potencial Total | Potencial físico-hídrico |
| AAI - Potencial Efetivo | Parcela c/ segurança hídrica + viabilidade |

## 8. `_ANA_AtlasIrrigacao_AreaAtual_Projecao2030-2040_env.xlsx`

Só aba `Atlas_mun`. Mesmo bloco tipologia repetido 3×: 2019 + projeções 2030 e 2040.
Colunas: `Código`, `Município`, `UF` + por ano `Arroz Inundado`, `Café`, `Cana Irrigada`, `Outras em Pivôs`, `Pivôs - Total`, `Outras culturas e sistemas`, `Área Total Irrigada` (fertirrigada e total geral só no bloco 2019).
