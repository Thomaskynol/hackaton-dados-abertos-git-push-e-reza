/**
 * AgroPilot 24/7 — Data Store & Agricultural Domain Knowledge
 * Embrapa, MAPA/ZARC, INMET, and Cepea references for Brazil.
 */

const AGRO_DATA = {
  // Perfil padrão do produtor (pequeno produtor familiar / médio)
  currentProfile: {
    nome: "Seu Sebastião da Silva",
    telefone: "(64) 99821-4472",
    propriedade: "Sítio Bela Vista",
    municipio: "Rio Verde - GO",
    areaHa: 14.5,
    culturaAtual: "soja",
    tipoSolo: "AD3", // AD1: Arenoso (CAD < 35mm), AD2: Médio (CAD 35-50mm), AD3: Argiloso (CAD > 50mm)
    faseCiclo: "vegetativo", // plantio, vegetativo, floracao, maturacao, colheita
    diasAposEmergencia: 28,
    proagroAtivo: true,
    pronafElegivel: true
  },

  // Base de culturas universais (Princípio #1: Universal)
  culturas: {
    soja: {
      nome: "Soja (Grão)",
      variedade: "TMG 7062 IPRO (Ciclo Médio 115 dias)",
      icone: "🌱",
      faseAtual: "V4 - 4º Trifólio Aberto",
      diasParaColheita: 87,
      umidadeSoloAtual: "68% (Adequada)",
      precipitacaoSemana: "42 mm",
      pragaAlvo: "Lagarta-da-soja e Percevejo-marrom",
      doencaAlvo: "Ferrugem Asiática (Phakopsora pachyrhizi)",
      precoSacaReferencia: 128.50
    },
    milho: {
      nome: "Milho Safrinha",
      variedade: "FS 450 PWU (Precoce 125 dias)",
      icone: "🌽",
      faseAtual: "V6 - Sexta Folha",
      diasParaColheita: 95,
      umidadeSoloAtual: "55% (Atenção)",
      precipitacaoSemana: "18 mm",
      pragaAlvo: "Cigarrinha-do-milho (Dalbulus maidis)",
      doencaAlvo: "Enfezamento e Mancha Branca",
      precoSacaReferencia: 58.20
    },
    cafe: {
      nome: "Café Arábica",
      variedade: "Catuaí Vermelho IAC 99",
      icone: "☕",
      faseAtual: "Chumbinho / Expansão do Fruto",
      diasParaColheita: 110,
      umidadeSoloAtual: "72% (Ótima)",
      precipitacaoSemana: "55 mm",
      pragaAlvo: "Broca-do-café (Hypothenemus hampei)",
      doencaAlvo: "Ferrugem do Cafeeiro (Hemileia vastatrix)",
      precoSacaReferencia: 1420.00
    },
    feijao: {
      nome: "Feijão Carioca",
      variedade: "BRS FC402 (Ciclo 85 dias)",
      icone: "🍲",
      faseAtual: "R5 - Pré-floração",
      diasParaColheita: 42,
      umidadeSoloAtual: "62% (Boa)",
      precipitacaoSemana: "30 mm",
      pragaAlvo: "Mosca-branca (Bemisia tabaci)",
      doencaAlvo: "Antracnose",
      precoSacaReferencia: 245.00
    },
    mandioca: {
      nome: "Mandioca de Mesa (Aipim)",
      variedade: "BRS 399",
      icone: "🥔",
      faseAtual: "Acúmulo de Amido",
      diasParaColheita: 60,
      umidadeSoloAtual: "58% (Resistente)",
      precipitacaoSemana: "25 mm",
      pragaAlvo: "Mandarová da mandioca",
      doencaAlvo: "Podridão radicular",
      precoSacaReferencia: 42.00
    }
  },

  // Zoneamento Agrícola de Risco Climático (ZARC) - Dados Oficiais Decendiais
  // Decêndios de Outubro a Dezembro (D1 = 1-10, D2 = 11-20, D3 = 21-final)
  zarcDecendios: [
    { decendio: "Out/D1", data: "01-10 Out", ad1: 40, ad2: 30, ad3: 20, status: "Apto c/ cautela", aptoProagro: true },
    { decendio: "Out/D2", data: "11-20 Out", ad1: 30, ad2: 20, ad3: 20, status: "Janela Ideal", aptoProagro: true },
    { decendio: "Out/D3", data: "21-31 Out", ad1: 20, ad2: 20, ad3: 20, status: "Janela Ouro ★", aptoProagro: true },
    { decendio: "Nov/D1", data: "01-10 Nov", ad1: 20, ad2: 20, ad3: 20, status: "Janela Ouro ★", aptoProagro: true },
    { decendio: "Nov/D2", data: "11-20 Nov", ad1: 30, ad2: 20, ad3: 20, status: "Janela Ideal", aptoProagro: true },
    { decendio: "Nov/D3", data: "21-30 Nov", ad1: 40, ad2: 30, ad3: 20, status: "Risco Moderado", aptoProagro: true },
    { decendio: "Dez/D1", data: "01-10 Dez", ad1: 40, ad2: 40, ad3: 30, status: "Janela Tardil", aptoProagro: false },
    { decendio: "Dez/D2", data: "11-20 Dez", ad1: 50, ad2: 40, ad3: 40, status: "Risco Alto (Inapto)", aptoProagro: false }
  ],

  // Alertas Proativos Iniciais (Princípio #2: Proativo - Não espera perguntar)
  alertasProativos: [
    {
      id: "alt-01",
      tipo: "critico",
      categoria: "clima",
      icone: "⛈️",
      titulo: "Alerta de Chuva Excessiva e Vento Forte em 48h",
      descricao: "Frente fria com precipitação acumulada prevista de 75mm em 24h e rajadas de 55 km/h em Rio Verde - GO. Risco de acamamento no talhão baixo.",
      porQue: "Queda na pressão barométrica detectada pelo radar CPTEC + frente polar atingindo o sudoeste goiano.",
      fonte: "INMET / CPTEC Radar Sudoeste GO • Modelo GFS 0.25°",
      confianca: 94,
      dataHora: "Há 15 minutos",
      acaoRecomendada: "Suspender dessecação foliar e desobstruir curvas de nível do talhão 2.",
      missaoId: "mis-01",
      lido: false
    },
    {
      id: "alt-02",
      tipo: "warning",
      categoria: "fitossanitario",
      icone: "🐛",
      titulo: "Condição Favorável para Eclosão de Lagarta Helicoverpa",
      descricao: "Temperatura média de 29°C aliada a umidade de 74% acelerou o ciclo de ovos em propriedades vizinhas (raio de 12 km).",
      porQue: "Microclima dentro da faixa ótima de eclosão (28-31°C) com histórico regional confirmado pela cooperativa.",
      fonte: "Boletim Fitossanitário Regional Comigo / Embrapa Soja",
      confianca: 89,
      dataHora: "Hoje, às 08:30",
      acaoRecomendada: "Realizar amostragem de pano de batida em 10 pontos da lavoura antes de tomar decisão de pulverização.",
      missaoId: "mis-02",
      lido: false
    },
    {
      id: "alt-03",
      tipo: "opportunity",
      categoria: "mercado",
      icone: "📈",
      titulo: "Janela de Fixação de Preço Favorável: Soja a R$ 131,00/sc",
      descricao: "Dólar em alta e prêmio no porto de Paranaguá elevaram o preço local em +R$ 2,50/sc para entrega futura.",
      porQue: "Relatório USDA com corte de safra americana + demanda aquecida da China no line-up de navios.",
      fonte: "Cepea/Esalq & Indicador B3",
      confianca: 92,
      dataHora: "Ontem",
      acaoRecomendada: "Considerar travar 15% a 20% dos custos de produção (barter ou contrato futuro).",
      missaoId: null,
      lido: true
    }
  ],

  // Missões de Campo Práticas (Princípio #6: Executar Ações)
  missoesCampo: [
    {
      id: "mis-01",
      titulo: "Desobstrução e Vistoria de Curvas de Nível (Talhão 2)",
      cultura: "Soja",
      prioridade: "alta",
      prazo: "Antes da tempestade (Hoje até 17h)",
      instrucoes: "Evitar enxurradas e perda de solo fértil com a chuva prevista de 75mm.",
      checkpoints: [
        { id: "c1", texto: "Verificar saída dos terraços na baixada do talhão", concluido: false },
        { id: "c2", texto: "Remover galhos e restos de palhada que bloqueiam o escoamento", concluido: false },
        { id: "c3", texto: "Registrar foto com o celular para histórico da propriedade", concluido: false }
      ],
      concluida: false
    },
    {
      id: "mis-02",
      titulo: "Amostragem Fitossanitária com Pano de Batida",
      cultura: "Soja",
      prioridade: "media",
      prazo: "Amanhã pela manhã (07h às 10h)",
      instrucoes: "Contar número de lagartas pequenas (< 1,5cm) e grandes (> 1,5cm) por metro linear.",
      checkpoints: [
        { id: "c4", texto: "Efetuar 10 batidas distribuídas em zigue-zague", concluido: false },
        { id: "c5", texto: "Checar se o nível de dano econômico ultrapassou 20 lagartas/metro", concluido: false },
        { id: "c6", texto: "Consultar agrônomo da cooperativa para receituário caso atinja o limiar", concluido: false }
      ],
      concluida: false
    },
    {
      id: "mis-03",
      titulo: "Checagem de Bicos e Pressão do Pulverizador",
      cultura: "Geral",
      prioridade: "media",
      prazo: "Esta semana",
      instrucoes: "Evitar desperdício de defensivos e deriva em horários de vento.",
      checkpoints: [
        { id: "c7", texto: "Coletar vazão de 4 bicos com copo dosador graduado em 1 minuto", concluido: true },
        { id: "c8", texto: "Substituir pontas desgastadas com variação superior a 10%", concluido: true },
        { id: "c9", texto: "Checar filtros de linha e manômetro", concluido: true }
      ],
      concluida: true
    }
  ],

  // Cotações de Mercado em Tempo Real
  cotacoes: [
    { produto: "Soja (Saca 60kg)", regiao: "Rio Verde - GO", preco: "R$ 128,50", variacao: "+1.2%", tendencia: "up", fonte: "Cepea/Esalq" },
    { produto: "Milho (Saca 60kg)", regiao: "Campinas - SP", preco: "R$ 58,20", variacao: "-0.5%", tendencia: "down", fonte: "B3 Futuro" },
    { produto: "Café Arábica Tipo 6", regiao: "Cerrado Mineiro", preco: "R$ 1.420,00", variacao: "+2.8%", tendencia: "up", fonte: "Cepea" },
    { produto: "Feijão Carioca", regiao: "Brasília - DF", preco: "R$ 245,00", variacao: "+0.0%", tendencia: "neutral", fonte: "Conab" },
    { produto: "Mandioca de Mesa (cx 20kg)", regiao: "Paranavaí - PR", preco: "R$ 42,00", variacao: "+3.1%", tendencia: "up", fonte: "Ceasa" }
  ],

  // Canais de Comercialização para o Pequeno Produtor
  canaisVenda: [
    {
      canal: "Cooperativa Local (Comigo)",
      precoMedio: "R$ 128,50 / saca",
      prazoPagamento: "À vista ou 30 dias",
      seguranca: "Máxima (Garantia de recebimento)",
      requisito: "Estar cooperado e com grão limpo < 1% impureza"
    },
    {
      canal: "Programa PAA / PNAE (Merenda Escolar)",
      precoMedio: "R$ 138,00 / saca (+7% sobre mercado)",
      prazoPagamento: "Governo (45 a 60 dias)",
      seguranca: "Alta (Contrato público)",
      requisito: "DAP / CAF válida (Agricultura Familiar)"
    },
    {
      canal: "Cerealista Regional",
      precoMedio: "R$ 129,50 / saca",
      prazoPagamento: "15 dias",
      seguranca: "Média (Checar histórico comercial)",
      requisito: "Carga fechada (mínimo 300 sacas)"
    }
  ],

  // Cenários de Simulação para a Banca do Hackathon
  cenariosSimulacao: {
    geada: {
      titulo: "Simulação: Alerta Urgente de Geada Fraca a Moderada",
      tipo: "critico",
      icone: "❄️",
      descricao: "Massa de ar polar potente avançando com previsão de temperatura de 2.8°C na relva nas próximas 36 horas!",
      porQue: "Previsão sinótica INMET com céu limpo, vento calmo e queda abrupta do ponto de orvalho.",
      fonte: "INMET / CPTEC Alerta Meteorológico Especial",
      confianca: 96,
      acaoRecomendada: "Para lavouras de café e hortaliças: irrigação noturna por aspersão para elevação térmica ou ensacamento de mudas.",
      chatPrompt: "URGENTE: O sistema detectou previsão de temperatura de 2.8°C na madrugada de quinta-feira. Risco de geada na baixada!"
    },
    praga: {
      titulo: "Simulação: Surto de Cigarrinha-do-milho Detectado na Região",
      tipo: "warning",
      icone: "🦗",
      descricao: "Capturas em armadilhas de monitoramento subiram 340% nos municípios vizinhos. Vetor do complexo de enfezamentos.",
      porQue: "Migração de áreas de milho safrinha colhidas recentemente sem destruição de plantas tiguera.",
      fonte: "Rede de Alerta Fitossanitário Embrapa Milho e Sorgo",
      confianca: 91,
      acaoRecomendada: "Eliminar milho tiguera nas bordaduras e planejar aplicação de bioinseticida específico (Beauveria bassiana).",
      chatPrompt: "Aviso Fitossanitário: Aumento de 340% na pressão de cigarrinha nas fazendas a 15km da sua propriedade."
    },
    veranico: {
      titulo: "Simulação: Veranico Crítico no Enchimento de Grãos",
      tipo: "critico",
      icone: "☀️",
      descricao: "Bloqueio atmosférico com previsão de 12 dias consecutivos sem chuva e temperaturas acima de 34°C.",
      porQue: "Anomalia de alta pressão persistente no Centro-Oeste reduzindo umidade do solo para níveis de estresse hídrico.",
      fonte: "Monitor de Secas ANA / ZARC Tempo Real",
      confianca: 88,
      acaoRecomendada: "Acionar acionamento preventivo de seguro Proagro caso o estresse atinja fase crítica R5.",
      chatPrompt: "Atenção: Modelo meteorológico aponta 12 dias sem chuva durante o enchimento de grãos. Veja os impactos no seu ZARC."
    },
    janela_zarc: {
      titulo: "Simulação: Janela ZARC Fechando em 6 Dias",
      tipo: "warning",
      icone: "⏳",
      descricao: "Último decêndio com risco climático < 20% para sua cultivar de soja no solo AD3 expira em breve.",
      porQue: "Após 20 de Novembro, o risco de perda hídrica sobe para 40%, o que cancela a cobertura automática do Proagro Mais.",
      fonte: "Portaria ZARC MAPA vigente para Rio Verde/GO",
      confianca: 99,
      acaoRecomendada: "Concluir a semeadura até domingo para manter o direito à indenização integral do seguro agrícola.",
      chatPrompt: "Lembrete de Segurança ZARC: Restam 6 dias para plantar com risco classe 1 (20%). Não perca o prazo do seguro!"
    }
  }
};

if (typeof window !== "undefined") {
  window.AGRO_DATA = AGRO_DATA;
}
if (typeof global !== "undefined") {
  global.AGRO_DATA = AGRO_DATA;
}
