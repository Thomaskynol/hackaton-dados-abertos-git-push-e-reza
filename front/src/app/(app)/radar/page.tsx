"use client";

import { EvidenceCard } from "@/components/EvidenceCard";
import { AudioButton } from "@/components/AudioButton";
import { usePerfil } from "@/lib/perfil-context";
import { CULTURAS, evidenciasDemo } from "@/lib/dados-locais";

/**
 * Radar: as evidências que sustentam a decisão, cada uma com fonte e um dos
 * 4 estados honestos. Nunca "score 90%".
 */
export default function RadarPage() {
  const { perfil, carregado } = usePerfil();
  if (!carregado) return null;

  const cultura = CULTURAS.find((c) => c.id === perfil.lavouras[0]?.cultura);
  const evidencias = evidenciasDemo();
  const intro =
    "Aqui ficam as evidências da sua safra. Cada cartão mostra o que o dado permite dizer e de onde ele vem. Toque em Ver fonte para conferir.";

  return (
    <div className="space-y-5">
      <section>
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
            Radar da safra
          </h1>
          <AudioButton texto={intro} />
        </div>
        <p className="mt-1 text-muted">
          {cultura ? `${cultura.nome} · ` : ""}
          {perfil.municipio}/{perfil.uf}
        </p>
        <p className="mt-3 text-[1rem] text-muted">{intro}</p>
      </section>

      {/* legenda dos 4 estados */}
      <section className="flex flex-wrap gap-2" aria-label="Significado das cores">
        <Legenda cor="bg-favoravel" rotulo="Favorável" />
        <Legenda cor="bg-atencao" rotulo="Atenção" />
        <Legenda cor="bg-terra" rotulo="Falta dado" />
        <Legenda cor="bg-pendente" rotulo="Sem dado" />
      </section>

      <section className="space-y-3">
        {evidencias.map((e, i) => (
          <EvidenceCard key={`${e.tipo}-${i}`} evidencia={e} />
        ))}
      </section>
    </div>
  );
}

function Legenda({ cor, rotulo }: { cor: string; rotulo: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-[0.8rem] font-semibold text-muted">
      <span className={`h-2.5 w-2.5 rounded-full ${cor}`} aria-hidden />
      {rotulo}
    </span>
  );
}
