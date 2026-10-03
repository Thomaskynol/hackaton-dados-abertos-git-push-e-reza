/**
 * Dados LOCAIS para navegação sem backend.
 *
 * Princípio (documento mestre §9/§10): nada de número inventado apresentado
 * como fato. Tudo que aparece como "dado" vem marcado com fonte e, quando é só
 * demonstração de navegação, o estado é "pendente"/"sem_dado" — honesto sobre
 * o fato de o backend ainda não estar ligado.
 *
 * Quando o backend entrar, estas funções são substituídas por chamadas a
 * /api/* mantendo a MESMA assinatura.
 */
import type { Alerta, Evidencia, Intencao, Mensagem } from "./types";

/** Culturas do escopo congelado + hortaliças comuns na região de Araraquara. */
export const CULTURAS = [
  { id: "milho", nome: "Milho", emoji: "🌽" },
  { id: "soja", nome: "Soja", emoji: "🌱" },
  { id: "feijao", nome: "Feijão", emoji: "🫘" },
  { id: "arroz", nome: "Arroz", emoji: "🌾" },
  { id: "trigo", nome: "Trigo", emoji: "🌾" },
] as const;

export const SOLOS = [
  { id: "arenoso", nome: "Arenoso", dica: "Água escorre rápido, seca logo" },
  { id: "media", nome: "Médio", dica: "Entre o arenoso e o argiloso" },
  { id: "argiloso", nome: "Argiloso", dica: "Segura água, fica encharcado na chuva" },
] as const;

/** Perguntas que o produtor pode tocar em vez de digitar (reconhecer, não lembrar). */
export const SUGESTOES_CHAT = [
  { emoji: "💰", texto: "Compensa vender agora ou esperar?" },
  { emoji: "🤝", texto: "Qual canal paga mais pra agricultura familiar?" },
  { emoji: "🏛️", texto: "Como funciona o PAA/PNAE?" },
  { emoji: "🌾", texto: "Posso plantar agora?" },
  { emoji: "🐛", texto: "Vi um bicho na folha" },
  { emoji: "🌧️", texto: "Vai chover forte nos próximos dias?" },
] as const;

/**
 * Classificador de intenção LOCAL (regras simples), espelhando o
 * router_intencao do backend. Só para a navegação reagir ao texto.
 */
export function classificarLocal(texto: string): Intencao {
  const m = texto.toLowerCase();
  if (/\b(oi|ol[aá]|bom dia|boa tarde|boa noite|opa)\b/.test(m)) return "SAUDACAO";
  if (/(praga|bicho|lagarta|fungo|doen|inseto|mancha|ferrugem)/.test(m)) return "PRAGA";
  if (/(plantar|plantio|planto|semear|janela|época|epoca|colher|colheita)/.test(m))
    return "PLANEJAMENTO";
  if (/(chuva|chover|gear|geada|clima|tempo|frio|seca|calor)/.test(m)) return "CLIMA";
  if (/(vender|venda|pre[cç]o|mercado|paa|pnae)/.test(m)) return "VENDA";
  if (/(meu perfil|minha terra|cadastro|minha lavoura)/.test(m)) return "PERFIL";
  return "NAO_ENTENDI";
}

/**
 * Resposta LOCAL do copiloto. Deixa claro que a análise real virá do backend.
 * Não afirma risco/percentual algum — cumpre "não inventar número".
 */
export function responderLocal(texto: string, primeiroNome: string): Omit<Mensagem, "id" | "horario"> {
  const intencao = classificarLocal(texto);

  const base = (resposta: string, fonte: string, evid: Evidencia[] = []) => ({
    autor: "copiloto" as const,
    texto: resposta,
    intencao,
    fonte,
    evidencias: evid,
  });

  switch (intencao) {
    case "SAUDACAO":
      return base(
        `Oi, ${primeiroNome}! Pode perguntar do seu jeito: "posso plantar agora?", "vi um bicho na folha", "vai chover?".`,
        "AgroPilot",
      );
    case "PLANEJAMENTO":
      return base(
        `Boa, ${primeiroNome}. Eu respondo com a janela do ZARC para a sua cultura e solo, decêndio a decêndio, e mostro a fonte. Abra a aba Radar para ver a janela de plantio da sua região.`,
        "ZARC/MAPA",
        [
          {
            tipo: "zarc",
            estado: "pendente",
            titulo: "Janela de plantio (ZARC)",
            detalhe:
              "Preciso confirmar sua cultura e tipo de solo para buscar a janela recomendada.",
            fonte: {
              nome: "MAPA — ZARC Tábua de Risco 2026/2027",
              periodo: "2026/2027",
              limitacoes: ["ZARC é zoneamento municipal; não considera microclima."],
            },
          },
        ],
      );
    case "PRAGA":
      return base(
        `Entendi, ${primeiroNome}. Com o backend ligado, eu busco no Agrofit os produtos registrados para a sua cultura e o alvo, sempre lembrando que a aplicação exige receituário agronômico.`,
        "Agrofit/MAPA",
        [
          {
            tipo: "agrofit",
            estado: "pendente",
            titulo: "Produtos registrados (Agrofit)",
            detalhe:
              "Me diga a cultura e o que você viu na planta para eu buscar o catálogo oficial.",
            fonte: {
              nome: "MAPA — Agrofit",
              limitacoes: [
                "Catálogo de registro, não vigilância de pragas.",
                "Uso de defensivo exige receituário agronômico (Lei 14.785/2023).",
              ],
            },
          },
        ],
      );
    case "CLIMA":
      return base(
        `${primeiroNome}, a previsão vem do Open-Meteo por município. Abra a aba Radar para ver a previsão dos próximos dias e os avisos de geada, veranico e chuva forte perto do plantio ou da colheita.`,
        "Open-Meteo",
        [
          {
            tipo: "clima",
            estado: "pendente",
            titulo: "Previsão do tempo",
            detalhe:
              "Escolha o seu município no mapa para eu mostrar a previsão dos próximos dias.",
            fonte: { nome: "Open-Meteo + IBGE", limitacoes: ["Horizonte de previsão de até 7 dias."] },
          },
        ],
      );
    case "VENDA":
      return base(
        `Boa pergunta comercial, ${primeiroNome}. Eu mostro o cenário com fonte — preço de mercado (CONAB por UF), piso PGPM e canais (cooperativas, cerealistas, PAA/PNAE) — mas não digo quando vender. Olhe a aba Mapa: lá está o consultor comercial da sua região.`,
        "CONAB/PGPM (via aba Mapa)",
        [
          {
            tipo: "sigef",
            estado: "pendente",
            titulo: "Preço e canais da sua região",
            detalhe:
              "Abra a aba Mapa para ver preço de referência e canais de venda com fonte. Sem cotação inventada: quando faltar dado, mostro “sem cotação disponível”.",
            fonte: {
              nome: "CONAB / PGPM / PAA-PNAE (via Mapa)",
              limitacoes: ["Este chat mostra o cenário; não recomenda venda."],
            },
          },
        ],
      );
    case "PERFIL":
      return base(
        `Seu cadastro fica na aba de perfil. Você pode editar nome, cidade e lavouras quando quiser.`,
        "Cadastro",
      );
    default:
      return base(
        `Não entendi bem, ${primeiroNome}. Pode reformular? Tente: "posso plantar agora?", "vi um bicho na folha" ou "vai chover?".`,
        "AgroPilot",
      );
  }
}

/**
 * Alertas de demonstração para a navegação. Marcados honestamente como
 * exemplo local (sem backend). Severidade/datas são rótulos, não medições.
 */
export function alertasDemo(): Alerta[] {
  return [
    {
      id: "demo-janela",
      tipo: "janela_zarc",
      severidade: "media",
      titulo: "Exemplo: janela de plantio fechando",
      mensagem:
        "Quando o motor estiver ligado, você verá aqui quando faltar pouco para a janela do ZARC fechar na sua cultura.",
      fonte: "ZARC/MAPA (exemplo de navegação)",
      quando: "demonstração",
      lido: false,
    },
  ];
}

/**
 * Evidências de reserva da tela Radar. Usadas só quando falta o cadastro
 * (cultura/município) — nunca para fingir que "o backend não ligou". O
 * estado "pendente" aqui significa literalmente: falta uma informação SUA.
 */
export function evidenciasDemo(): Evidencia[] {
  return [
    {
      tipo: "zarc",
      estado: "pendente",
      titulo: "Janela de plantio (ZARC)",
      detalhe:
        "Escolha a sua cultura e o seu município para eu buscar a janela de plantio que o governo recomenda, decêndio a decêndio.",
      fonte: {
        nome: "MAPA — ZARC (Zoneamento Agrícola de Risco Climático)",
        periodo: "safra vigente",
        limitacoes: ["Zoneamento municipal; não considera o microclima da sua gleba."],
      },
    },
    {
      tipo: "clima",
      estado: "pendente",
      titulo: "Previsão do tempo",
      detalhe:
        "Escolha o seu município no mapa para eu mostrar a previsão dos próximos dias (chuva, mínima e máxima).",
      fonte: { nome: "Open-Meteo + IBGE", periodo: "próximos 7 dias" },
    },
    {
      tipo: "psr",
      estado: "pendente",
      titulo: "Histórico de perdas (seguro rural)",
      detalhe:
        "Com a sua cultura e município, eu mostro os eventos que mais causaram perda na sua região, com base no seguro rural.",
      fonte: {
        nome: "MAPA — Seguro Rural (PSR/SISSER)",
        periodo: "2016–2025",
        limitacoes: ["Dados de apólice, não de produção individual."],
      },
    },
  ];
}
