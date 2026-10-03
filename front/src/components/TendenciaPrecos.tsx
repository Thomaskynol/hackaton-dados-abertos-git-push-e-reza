"use client";

import { TrendingUp, TrendingDown, Minus, LineChart, Sparkles } from "lucide-react";
import type { TendenciaPreco } from "@/lib/api";

function brl(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/**
 * Card de tendência e projeção de preço, a partir da série histórica real do
 * IBGE (preço médio recebido pelo produtor por ano). Mostra para onde o preço
 * vem indo e uma estimativa para o próximo ano — sempre com faixa e o aviso de
 * que é apoio ao planejamento, não garantia. Linguagem do produtor.
 */
export function TendenciaPrecos({ tendencia }: { tendencia: TendenciaPreco }) {
  if (!tendencia || tendencia.estado !== "disponivel" || !tendencia.ultimo) return null;

  const { direcao, ultimo, media_recente, projecao, serie } = tendencia;
  const Icone = direcao === "subindo" ? TrendingUp : direcao === "caindo" ? TrendingDown : Minus;
  const cor =
    direcao === "subindo" ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : direcao === "caindo" ? "text-red-700 bg-red-50 border-red-200"
    : "text-muted bg-canvas border-line";

  // A variação do ÚLTIMO ano vem do IBGE. Sem ela, o texto só repetia o selo
  // ("vem subindo") sem dizer QUANTO — e o produtor não conseguia decidir.
  const varPct = tendencia.variacao_ultimo_ano;
  const temVar = varPct != null && Number.isFinite(varPct);
  const pct = (n: number) => `${n > 0 ? "+" : ""}${String(n).replace(".", ",")}%`;

  const cultNome = tendencia.cultura?.toLowerCase();
  const quemMove = temVar
    ? varPct! > 3
      ? `subiu ${pct(varPct!)}`
      : varPct! < -3
        ? `caiu ${pct(varPct!)}`
        : `ficou praticamente parado (${pct(varPct!)})`
    : direcao === "subindo"
      ? "vem subindo"
      : direcao === "caindo"
        ? "vem caindo"
        : "vem estável";
  // Onde o preço atual está contra a média recente: é isso que diz se o
  // produtor está vendendo acima ou abaixo da própria série.
  const acimaDaMedia =
    media_recente && ultimo ? (ultimo.valor / media_recente - 1) * 100 : null;
  const posicao =
    acimaDaMedia != null
      ? acimaDaMedia > 5
        ? `acima da média da série (${brl(media_recente!)})`
        : acimaDaMedia < -5
          ? `abaixo da média da série (${brl(media_recente!)})`
          : `na média da série (${brl(media_recente!)})`
      : null;

  // mini-gráfico de barras com os últimos pontos da série
  const ult = (serie ?? []).slice(-8);
  const max = Math.max(...ult.map((p) => p.valor), 1);
  // Último ponto destacado quando o preço caiu — é o que o produtor precisa ver.
  const ultimoCaiu = temVar && varPct! < -3;

  // Passo 5: regressão sempre visível. Se a IA responder, ela vem embutida em
  // `valor_tendencia`; senão vem no bloco próprio `projecao_tendencia`.
  const reg = tendencia.projecao_tendencia;
  const valorRegressao = projecao?.valor_tendencia ?? reg?.valor_estimado ?? null;
  const regressaoFaixa =
    reg && reg.faixa_min != null && reg.faixa_max != null
      ? { min: reg.faixa_min, max: reg.faixa_max }
      : null;
  // Quando a projeção JÁ É a regressão, não repete o mesmo número duas vezes.
  const regressaoVisivel =
    projecao != null &&
    valorRegressao != null &&
    projecao.origem !== "tendencia" &&
    Math.abs(valorRegressao - projecao.valor_estimado) > 0.01;

  return (
    <section
      aria-label="Tendência de preço"
      className="rounded-2xl border border-line bg-surface p-5 sm:p-6 shadow-card"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-terra-soft text-terra-ink">
            <LineChart size={18} aria-hidden />
          </span>
          <div>
            <h2 className="font-display text-[1.15rem] font-extrabold text-ink">Para onde o preço vem indo</h2>
            <p className="text-[0.78rem] text-muted">Preço médio recebido pelo produtor · IBGE</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[0.78rem] font-bold ${cor}`}>
          <Icone size={14} aria-hidden />
          {temVar ? pct(varPct!) : direcao}
        </span>
      </div>

      <p className="mt-1 text-[0.72rem] text-muted">
        {tendencia.fonte ?? "IBGE — Produção Agrícola Municipal (PAM)"}
      </p>

      <p className="mt-3 text-[0.98rem] leading-relaxed text-ink">
        Na sua região, o preço do {cultNome} <strong>{quemMove}</strong> de{" "}
        {serie && serie.length >= 2 ? serie[serie.length - 2].ano : ""} para{" "}
        <strong>{ultimo.ano}</strong>: ficou em <strong>{brl(ultimo.valor)}</strong> a saca
        {posicao ? `, ${posicao}` : ""}.
      </p>
      {tendencia.periodicidade && (
        <p className="mt-1.5 text-[0.78rem] leading-snug text-muted">
          {tendencia.periodicidade}. É o valor médio do ano, não a cotação do dia —
          para o preço de hoje veja o Cepea.
        </p>
      )}

      {ult.length >= 3 && (
        <div className="mt-4 flex items-end gap-1.5" aria-hidden>
          {ult.map((p, i) => {
            const ehUltimo = i === ult.length - 1;
            return (
              <div key={p.ano} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t ${
                    ehUltimo
                      ? ultimoCaiu
                        ? "bg-red-500/80"
                        : "bg-emerald-500/80"
                      : "bg-terra/70"
                  }`}
                  style={{ height: `${Math.max(6, (p.valor / max) * 64)}px` }}
                  title={`${p.ano}: ${brl(p.valor)}`}
                />
                <span className={`text-[0.6rem] ${ehUltimo ? "font-bold text-ink" : "text-muted"}`}>
                  {String(p.ano).slice(2)}
                </span>
              </div>
            );
          })}
        </div>
      )}
      {ultimoCaiu && (
        <p className="mt-2 text-[0.8rem] leading-snug text-ink">
          A barra vermelha é o último ano oficial: o preço caiu frente a {ultimo.ano - 1}.
          {/* selo nominal, para não confundir com alta real */}
          {tendencia.variacao_media_anual != null && (
            <span className="text-muted">
              {" "}Nos últimos 8 anos a linha vem subindo cerca de{" "}
              {pct(tendencia.variacao_media_anual)} ao ano, mas isso é preço nominal
              (inflação); não quer dizer que o produtor esteja recebendo mais.
            </span>
          )}
        </p>
      )}

      {projecao && (
        <div className="mt-4 rounded-xl border border-dashed border-terra/40 bg-terra-soft/40 p-3.5">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[0.82rem] font-bold uppercase tracking-wide text-terra-ink">
              Estimativa para a próxima safra ({projecao.ano})
            </p>
            {projecao.origem === "ia" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-terra px-2 py-0.5 text-[0.68rem] font-bold text-white">
                <Sparkles size={11} aria-hidden /> por IA
              </span>
            )}
          </div>
          <p className="mt-1 text-[1.05rem] font-extrabold text-ink">
            cerca de {brl(projecao.valor_estimado)}
            <span className="ml-1 text-[0.82rem] font-semibold text-muted">
              (entre {brl(projecao.faixa_min)} e {brl(projecao.faixa_max)})
            </span>
          </p>
          {projecao.racional && (
            <p className="mt-1.5 text-[0.86rem] leading-relaxed text-ink">{projecao.racional}</p>
          )}

          {/* Passo 5: a regressão aparece SEMPRE, mesmo com a IA ligada.
              É o número determinístico: não muda de um carregamento para o
              outro, dá para conferir na conta, e sobrevive a desligar a IA. */}
          {regressaoVisivel && (
            <p className="mt-2 rounded-lg bg-surface/70 px-2.5 py-2 text-[0.8rem] leading-snug text-ink">
              <strong>Pela reta da série:</strong> {brl(valorRegressao)}
              {regressaoFaixa && (
                <span className="text-muted">
                  {" "}(entre {brl(regressaoFaixa.min)} e {brl(regressaoFaixa.max)})
                </span>
              )}
              <span className="mt-1 block text-muted">
                É o cálculo da linha de tendência dos últimos anos — o mesmo número
                sempre, dá para conferir. {projecao.origem === "ia"
                  ? "A diferença para o valor da IA mostra o quanto a leitura do modelo se afasta da série."
                  : ""}
              </span>
            </p>
          )}

          <p className="mt-1 text-[0.8rem] leading-relaxed text-muted">
            {tendencia.aviso}
          </p>
        </div>
      )}
    </section>
  );
}
