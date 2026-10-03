/**
 * Smoke check da humanização dos cards (não faz parte do build).
 * Uso: npx tsx scripts/check-texto-cards.ts   (a partir de front/)
 */
import {
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

div("1. Produção — o caso do usuário (feijao · 215 ha · 742 t · safra 2013–2017)");
const p = producaoEmTexto(
  {
    estado: "disponivel",
    culturaTopo: "feijao",
    areaHa: 215,
    producaoT: 742,
    safraRef: "2013–2017",
  },
  "São Paulo",
);
console.log("frase   :", p.detalhe);
console.log("fichas  :", p.destaques.map((d) => `${d.rotulo}=${d.valor} (${d.dica})`).join(" | "));
console.log("leitura :", p.leitura);

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
const tudo = JSON.stringify([p, s]);
console.log(tudo.includes(" · ") ? "FALHOU: ainda junta com ·" : "OK — sem join(' · ')");
