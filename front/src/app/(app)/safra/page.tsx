"use client";

import Link from "next/link";
import { MessageCircle, Bell, ChevronRight, Sprout, CloudSun } from "lucide-react";
import { AudioButton } from "@/components/AudioButton";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";
import { CULTURAS, alertasDemo } from "@/lib/dados-locais";

/** Minha Safra (início): o produtor vê o essencial do dia em um relance. */
export default function Safra() {
  const { perfil, carregado } = usePerfil();
  if (!carregado) return null;

  const pn = primeiroNome(perfil.nome);
  const lav = perfil.lavouras[0];
  const cultura = CULTURAS.find((c) => c.id === lav?.cultura);
  const alertas = alertasDemo();

  const saudacao = saudar();
  const resumoDia =
    "Assim que o motor de dados estiver ligado, aqui aparece a decisão do dia: se dá para plantar, o risco da janela e o próximo passo — sempre com a fonte.";

  return (
    <div className="space-y-5">
      {/* saudação */}
      <section>
        <p className="text-muted">{saudacao},</p>
        <h1 className="font-display text-[1.8rem] font-extrabold leading-tight text-ink">
          {pn}
        </h1>
        <p className="mt-1 flex items-center gap-1.5 text-muted">
          <Sprout size={16} aria-hidden />
          {cultura ? cultura.nome : "cultura não definida"} · {perfil.municipio}/{perfil.uf}
        </p>
      </section>

      {/* decisão do dia — estado honesto (ainda sem backend) */}
      <section className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-5 shadow-card">
        <span className="absolute left-0 top-0 h-full w-1.5 bg-atencao" aria-hidden />
        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-canvas px-3 py-1 text-[0.78rem] font-bold uppercase tracking-wide text-atencao">
            <CloudSun size={16} /> Decisão do dia
          </span>
          <AudioButton texto={resumoDia} />
        </div>
        <p className="mt-3 text-[1.05rem] text-ink">{resumoDia}</p>
        <Link
          href="/assistente"
          className="mt-4 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft transition hover:brightness-95"
        >
          <MessageCircle size={20} /> O que eu faço agora?
        </Link>
      </section>

      {/* próximo passo */}
      <section>
        <h2 className="mb-2 text-[0.82rem] font-bold uppercase tracking-wide text-muted">
          Próximo passo
        </h2>
        <Link
          href="/radar"
          className="flex items-center gap-3 rounded-xl2 border border-line bg-surface p-4 shadow-soft transition hover:border-terra"
        >
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-terra-soft text-xl" aria-hidden>
            🌦️
          </span>
          <span className="flex-1">
            <span className="block font-bold text-ink">Conferir o Radar da sua safra</span>
            <span className="block text-[0.92rem] text-muted">
              Ver evidências e fontes · 1 min
            </span>
          </span>
          <ChevronRight className="text-muted" aria-hidden />
        </Link>
      </section>

      {/* alertas proativos */}
      <section>
        <h2 className="mb-2 flex items-center gap-1.5 text-[0.82rem] font-bold uppercase tracking-wide text-muted">
          <Bell size={14} /> Avisos
        </h2>
        <div className="space-y-2.5">
          {alertas.map((a) => (
            <article
              key={a.id}
              className="rounded-xl2 border border-line bg-surface p-4 shadow-soft"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-bold text-ink">{a.titulo}</h3>
                <span className="shrink-0 rounded-full bg-canvas px-2 py-0.5 text-[0.72rem] font-semibold text-muted">
                  exemplo
                </span>
              </div>
              <p className="mt-1 text-[0.95rem] text-muted">{a.mensagem}</p>
              <div className="mt-2 flex items-center gap-2">
                <AudioButton texto={`${a.titulo}. ${a.mensagem}`} />
                <span className="text-[0.78rem] text-muted">Fonte: {a.fonte}</span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function saudar() {
  const h = new Date().getHours();
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}
