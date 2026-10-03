/**
 * Smoke check da humanização dos cards (não faz parte do build).
 * Uso: npx tsx scripts/check-texto-cards.ts   (a partir de front/)
 */
import {
  formatarMilhar,
  hectares,
  numeroBR,
  producaoEmTexto,
  rotuloCulturaAmigavel,
  safraAmigavel,
  seguroEmTexto,
  irrigacaoEmTexto,
  toneladas,
} from "../src/lib/texto-cards";

const div = (t: string) => console.log(`\n=== ${t} ===`);

div("1. Produção — PAM/IBGE (produção REAL, ano recente)");
const pam = producaoEmTexto(
  {
    estado: "disponivel",
    culturaTopo: "soja",
    culturaLabel: "Soja",
    areaHa: null,
    producaoT: 4_731_554,
    producaoTotalT: 9_751_917,
    ano: 2025,
    safraRef: null,
    natureza: "agricultura",
    culturas: [
      { cultura: "soja", label: "Soja", quantidade_t: 4_731_554, valor_ton: 2057.93 },
      { cultura: "milho", label: "Milho", quantidade_t: 4_231_182, valor_ton: 1085.89 },
      { cultura: "feijao", label: "Feijão", quantidade_t: 159_635, valor_ton: 4014.94 },
    ],
  },
  "São Paulo",
);
console.log("frase   :", pam.detalhe);
console.log("fichas  :", pam.destaques.map((d) => `${d.rotulo}=${d.valor}`).join(" | "));
console.log("leitura :", pam.leitura);

div("1b. Formatação de números grandes");
console.log("4731554 ->", formatarMilhar(4731554));
console.log("159635  ->", formatarMilhar(159635));
console.log("742     ->", formatarMilhar(742));

div("1c. Produção — fallback SIGEF (semente, declarado como tal)");
const sigef = producaoEmTexto(
  {
    estado: "disponivel",
    culturaTopo: "feijao",
    areaHa: 215,
    producaoT: 742,
    safraRef: "2013–2017",
    natureza: "sementes",
  },
  "São Paulo",
);
console.log("frase   :", sigef.detalhe);
console.log("leitura :", sigef.leitura);

div("1d. Perfil com feijão — varias grafias tem que casar no ranking");
const PAM = {
  estado: "disponivel" as const,
  culturaTopo: "soja",
  culturaLabel: "Soja",
  areaHa: null,
  producaoT: 4_731_554,
  producaoTotalT: 9_751_917,
  ano: 2025,
  safraRef: null,
  natureza: "agricultura" as const,
  culturas: [
    { cultura: "soja", label: "Soja", quantidade_t: 4_731_554, valor_ton: 2057.93 },
    { cultura: "milho", label: "Milho", quantidade_t: 4_231_182, valor_ton: 1085.89 },
    { cultura: "feijao", label: "Feijão", quantidade_t: 159_635, valor_ton: 4014.94 },
  ],
};
// BUG CORRIGIDO: o perfil grava "feijao" (id do onboarding) mas o backend
// devolve "feijão" (com acento). A comparação literal caía no ramo de
// "é pouco produzida por aqui" e escondia a ficha do produtor.
for (const grafia of ["feijao", "feijão", "FEIJÃO", " feijao ", "Feijão", "  FÉIJÃO  "]) {
  const r = producaoEmTexto(PAM, "São Paulo", grafia);
  const achou = r.detalhe.includes("é pouco produzida");
  console.log(
    `${JSON.stringify(grafia).padEnd(12)} -> ${achou ? "FALHOU: 'pouco produzida'" : r.detalhe.split("A sua cultura,")[1]?.trim()}`,
  );
}
// Cultura fora da PAM continua honesta: não pode inventar posição.
const fora = producaoEmTexto(PAM, "São Paulo", "cafe");
console.log("cafe (fora da PAM):", fora.detalhe.split("A sua cultura,")[1]?.trim());

div("2. Números e unidades");
console.log("hectares(215)   :", hectares(215));
console.log("hectares(1)     :", hectares(1));
console.log("hectares(1.5)   :", hectares(1.5));
console.log("toneladas(742)  :", toneladas(742));
console.log("toneladas(1)    :", toneladas(1));
console.log("numeroBR(12345) :", numeroBR(12345));
console.log("safraAmigavel   :", safraAmigavel("2013–2017"), "|", safraAmigavel("2026/27"), "|", safraAmigavel(null));

div("3. Culturas: slug → nome com acento correto");
for (const c of ["feijao", "soja", "milho", "cafe", "cana", "Feijão Cores", "Milho 1a Safra", "", null])
  console.log(`${JSON.stringify(c).padEnd(18)} -> ${rotuloCulturaAmigavel(c as string | null)}`);

div("4. Sem dado (estado honesto, nunca número inventado)");
console.log("produção :", producaoEmTexto({ estado: "sem_dado", culturaTopo: null, areaHa: null, producaoT: null, safraRef: null }, "São Paulo").detalhe);
console.log("seguro   :", seguroEmTexto({ estado: "pendente", apolices: null, valorSegurado: null, culturaTopo: "feijao" }, "São Paulo").detalhe);

div("5. Seguro com dado");
const s = seguroEmTexto({ estado: "disponivel", apolices: 7, valorSegurado: null, culturaTopo: "feijao" }, "São Paulo");
console.log("frase   :", s.detalhe);
console.log("fichas  :", s.destaques.map((d) => `${d.rotulo}=${d.valor}`).join(" | "));

div("6. Irrigação");
console.log("com área :", irrigacaoEmTexto({ estado: "disponivel", areaIrrigadaHa: 1 }, "São Paulo").detalhe);
console.log("detalhe  :", irrigacaoEmTexto({ estado: "disponivel", areaIrrigadaHa: null, detalhe: "Grupo 3, sistema pivô (Atlas Irrigação ANA)." }, "São Paulo").detalhe);
console.log("sem dado :", irrigacaoEmTexto({ estado: "sem_dado", areaIrrigadaHa: null }, "São Paulo").detalhe);

div("7. Sem regressão: nenhum '·' solto");
const tudo = JSON.stringify([pam, s]);
console.log(tudo.includes(" · ") ? "FALHOU: ainda junta com ·" : "OK — sem join(' · ')");
