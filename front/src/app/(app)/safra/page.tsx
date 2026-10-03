"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MessageCircle, Bell, ChevronRight, Sprout, CloudSun, Sparkles, Loader2 } from "lucide-react";
import { precisaOnboarding, usePerfil, primeiroNome } from "@/lib/perfil-context";
import { CULTURAS } from "@/lib/dados-locais";
import { getAlertas, getDecisaoDia, type AlertaReal, type DecisaoDia } from "@/lib/api";

/** Minha Safra (início): o produtor vê o essencial do dia em um relance. */
export default function Safra() {
  const router = useRouter();
  const { perfil, carregado } = usePerfil();
  const [alertas, setAlertas] = useState<AlertaReal[]>([]);
  const [carregandoAlertas, setCarregandoAlertas] = useState(true);
  const [decisao, setDecisao] = useState<DecisaoDia | null>(null);
  const [carregandoDecisao, setCarregandoDecisao] = useState(true);

  useEffect(() => {
    if (precisaOnboarding(perfil, carregado)) router.replace("/onboarding");
  }, [perfil, carregado, router]);

  useEffect(() => {
    if (!carregado) return;
    let vivo = true;
    const cultura = perfil.lavouras[0]?.cultura ?? null;

    getAlertas(perfil.uf || "SP", perfil.cod_ibge || null, cultura)
      .then((r) => { if (vivo) setAlertas(r.alertas ?? []); })
      .catch(() => { if (vivo) setAlertas([]); })
      .finally(() => { if (vivo) setCarregandoAlertas(false); });

    setCarregandoDecisao(true);
    getDecisaoDia({
      produtor_id: perfil.id,
      uf: perfil.uf || "SP",
      ibge: perfil.cod_ibge || null,
      cultura,
    })
      .then((d) => { if (vivo) setDecisao(d); })
      .catch(() => { if (vivo) setDecisao(null); })
      .finally(() => { if (vivo) setCarregandoDecisao(false); });

    return () => { vivo = false; };
  }, [carregado, perfil.id, perfil.uf, perfil.cod_ibge, perfil.lavouras]);

  if (!carregado) return null;

  const pn = primeiroNome(perfil.nome);
  const lav = perfil.lavouras[0];
  const cultura = CULTURAS.find((c) => c.id === lav?.cultura);

  const saudacao = saudar();
  const resumoDia =
    "Assim que o motor de dados estiver ligado, aqui aparece a decisão do dia: se dá para plantar, o risco da janela e o próximo passo — sempre com a fonte.";

  return (
    <div className="space-y-6">
      {/* Saudação e Perfil do Produtor */}
      <section className="rounded-2xl border border-line bg-surface/60 p-4 sm:p-6 backdrop-blur shadow-soft">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-muted font-medium">{saudacao},</span>
              <span className="rounded-full bg-terra-soft px-2.5 py-0.5 text-xs font-bold text-terra-ink">
                Produtor Ativo
              </span>
            </div>
            <h1 className="mt-1 font-display text-2xl sm:text-3xl font-extrabold text-ink">
              {pn}
            </h1>
            <p className="mt-1.5 flex items-center gap-2 text-sm text-muted">
              <Sprout size={16} className="text-terra" aria-hidden />
              <span>Cultura: <strong className="text-ink">{cultura ? cultura.nome : "Não definida"}</strong></span>
              <span>·</span>
              <span>{perfil.municipio}/{perfil.uf}</span>
            </p>
          </div>
          <Link
            href="/mapa"
            className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-sm font-bold text-terra-ink shadow-soft hover:bg-terra-soft transition shrink-0"
          >
            <span>Ver no Mapa</span>
            <ChevronRight size={16} />
          </Link>
        </div>
      </section>

      {/* Grid Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Coluna 1: Decisão do Dia & Próximo Passo */}
        <div className="lg:col-span-7 space-y-5">
          {/* Decisão do dia — real, por IA (clima + ZARC + preço + memória) */}
          <section className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-5 sm:p-6 shadow-card card-hover">
            <span
              className={`absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b ${
                decisao?.severidade === "alta" ? "from-red-400 to-red-600"
                : decisao?.severidade === "media" ? "from-amber-400 to-amber-600"
                : "from-terra to-terra-ink"
              }`}
              aria-hidden
            />
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 rounded-full bg-amber-50 border border-amber-200 px-3.5 py-1 text-[0.78rem] font-extrabold uppercase tracking-wide text-amber-800">
                <CloudSun size={17} /> Decisão do dia
              </span>
              {decisao?.origem === "ia" && (
                <span className="inline-flex items-center gap-1 rounded-full bg-terra px-2 py-0.5 text-[0.68rem] font-bold text-white">
                  <Sparkles size={11} aria-hidden /> por IA
                </span>
              )}
            </div>

            {carregandoDecisao ? (
              <p className="mt-3.5 flex items-center gap-2 text-[0.95rem] text-muted">
                <Loader2 size={16} className="animate-spin" aria-hidden /> Lendo o clima e os dados da sua safra…
              </p>
            ) : decisao ? (
              <>
                <p className="mt-3.5 text-[1.05rem] leading-relaxed text-ink font-medium">{decisao.resposta}</p>

                {decisao.acoes.length > 0 && (
                  <ul className="mt-3.5 space-y-1.5">
                    {decisao.acoes.map((a, i) => (
                      <li key={i} className="flex items-start gap-2 text-[0.92rem] text-ink">
                        <span className="mt-1 grid h-4 w-4 shrink-0 place-items-center rounded-full bg-terra-soft text-[0.6rem] font-bold text-terra-ink">
                          {i + 1}
                        </span>
                        <span>{a}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {decisao.fontes.length > 0 && (
                  <p className="mt-3 text-[0.72rem] text-muted">
                    Fontes: {decisao.fontes.join(" · ")}
                    {decisao.local?.nome ? ` · ${decisao.local.nome}/${decisao.local.uf}` : ""}
                  </p>
                )}
              </>
            ) : (
              <p className="mt-3.5 text-[1.05rem] leading-relaxed text-ink font-medium">{resumoDia}</p>
            )}

            <Link
              href="/assistente"
              className="mt-5 inline-flex min-h-[50px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft transition hover:brightness-105 active:scale-[0.99]"
            >
              <MessageCircle size={20} /> O que eu faço agora?
            </Link>
          </section>

          {/* Próximo passo */}
          <section>
            <h2 className="mb-2.5 text-[0.8rem] font-bold uppercase tracking-wide text-muted">
              Próximo passo recomendado
            </h2>
            <Link
              href="/radar"
              className="flex items-center gap-3.5 rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-soft card-hover"
            >
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-terra-soft text-2xl shadow-soft" aria-hidden>
                🌦️
              </span>
              <span className="flex-1">
                <span className="block font-bold text-ink text-base">Conferir o Radar da sua safra</span>
                <span className="block text-[0.88rem] text-muted">
                  Ver evidências, clima e fontes oficiais · 1 min
                </span>
              </span>
              <ChevronRight className="text-muted" aria-hidden />
            </Link>
          </section>
        </div>

        {/* Coluna 2: Avisos & Alertas proativos */}
        <div className="lg:col-span-5 space-y-4">
          <section>
            <div className="flex items-center justify-between mb-2.5">
              <h2 className="flex items-center gap-1.5 text-[0.8rem] font-bold uppercase tracking-wide text-muted">
                <Bell size={15} /> Avisos & Monitoramento
              </h2>
              {!carregandoAlertas && (
                <span className="text-xs font-semibold text-terra-ink">
                  {alertas.length === 0
                    ? "tudo tranquilo"
                    : `${alertas.length} ${alertas.length === 1 ? "aviso" : "avisos"}`}
                </span>
              )}
            </div>

            {carregandoAlertas ? (
              <div className="rounded-xl2 border border-line bg-surface p-4 text-[0.9rem] text-muted shadow-soft">
                Vendo se há algo pedindo sua atenção…
              </div>
            ) : alertas.length === 0 ? (
              <div className="rounded-xl2 border border-emerald-200 bg-emerald-50/60 p-4 shadow-soft">
                <p className="font-bold text-emerald-900">Nada urgente por agora.</p>
                <p className="mt-1 text-[0.9rem] leading-relaxed text-emerald-800">
                  Não há janela de plantio fechando nem risco em destaque para a sua cultura.
                  Assim que algo mudar, aviso você aqui.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {alertas.map((a) => {
                  const cor =
                    a.severidade === "alta"
                      ? "from-red-400 to-red-600"
                      : a.severidade === "media"
                        ? "from-amber-400 to-amber-600"
                        : "from-emerald-400 to-emerald-600";
                  const titulo =
                    a.titulo // clima traz título próprio (ex: "Risco de geada")
                    ?? (a.tipo === "janela_zarc"
                      ? "Época de plantio"
                      : a.tipo === "risco_historico"
                        ? "Fique de olho"
                        : "Aviso");
                  return (
                    <article
                      key={a.id}
                      className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 shadow-soft card-hover"
                    >
                      <span className={`absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b ${cor}`} aria-hidden />
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-bold text-ink text-[0.98rem]">{titulo}</h3>
                        {a.severidade === "alta" && (
                          <span className="shrink-0 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-[0.7rem] font-bold text-red-700">
                            atenção
                          </span>
                        )}
                      </div>
                      <p className="mt-1.5 text-[0.9rem] leading-relaxed text-muted">{a.mensagem}</p>
                      <div className="mt-3 flex items-center justify-between pt-2 border-t border-line/60">
                        <span className="text-[0.78rem] text-muted">Fonte: <strong>{a.fonte}</strong></span>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function saudar() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}
