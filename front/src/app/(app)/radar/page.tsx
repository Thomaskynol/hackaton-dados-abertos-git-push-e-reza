"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { EvidenceCard } from "@/components/EvidenceCard";
import { precisaOnboarding, usePerfil } from "@/lib/perfil-context";
import { CULTURAS } from "@/lib/dados-locais";
import { getRadar, type RadarBloco } from "@/lib/api";
import type { Evidencia } from "@/lib/types";

/**
 * Radar: as evidências que sustentam a decisão, cada uma com fonte e um dos
 * estados honestos. Puxa dados REAIS e já estruturados de GET /api/radar
 * (janela ZARC em datas, previsão 7 dias, perdas do seguro rural).
 *
 * Três estados honestos, nunca "score 90%":
 *   - dado real (favorável/atenção/informativo)
 *   - sem_dado  → a base foi consultada e não tem o dado para o produtor
 *   - sem_conexao → o fetch falhou; o dado existe, só não carregou (com retry)
 */
export default function RadarPage() {
  const router = useRouter();
  const { perfil, carregado } = usePerfil();
  const [evidencias, setEvidencias] = useState<Evidencia[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erroRede, setErroRede] = useState(false);

  useEffect(() => {
    if (precisaOnboarding(perfil, carregado)) router.replace("/onboarding");
  }, [perfil, carregado, router]);

  const buscar = useCallback(async () => {
    setCarregando(true);
    setErroRede(false);
    const uf = perfil.uf || "SP";
    const ibge = perfil.cod_ibge || null;
    const cultura = perfil.lavouras[0]?.cultura ?? null;
    const solo = perfil.lavouras[0]?.solo ?? null;
    try {
      const r = await getRadar(uf, ibge, cultura, solo);
      // ordem: clima (o que vem aí) → ZARC (quando plantar) → PSR (o que ameaça)
      setEvidencias([
        blocoParaEvidencia(r.clima, "clima"),
        blocoParaEvidencia(r.zarc, "zarc"),
        blocoParaEvidencia(r.psr, "psr"),
      ]);
    } catch {
      // backend fora do ar ou NEXT_PUBLIC_API_URL errado: honesto, com retry
      setErroRede(true);
      setEvidencias([
        semConexao("clima", "Previsão do tempo"),
        semConexao("zarc", "Janela de plantio (ZARC)"),
        semConexao("psr", "Histórico de perdas (seguro rural)"),
      ]);
    } finally {
      setCarregando(false);
    }
  }, [perfil.uf, perfil.cod_ibge, perfil.lavouras]);

  useEffect(() => {
    if (carregado) void buscar();
  }, [carregado, buscar]);

  if (!carregado) return null;

  const cultura = CULTURAS.find((c) => c.id === perfil.lavouras[0]?.cultura);
  const intro =
    "Aqui ficam as evidências da sua safra. Cada cartão mostra o que o dado permite dizer e de onde ele vem. Toque em Ver fonte para conferir.";

  return (
    <div className="space-y-5">
      <section>
        <h1 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
          Radar da safra
        </h1>
        <p className="mt-1 text-muted">
          {cultura ? `${cultura.nome} · ` : ""}
          {perfil.municipio}/{perfil.uf}
        </p>
        <p className="mt-3 text-[1rem] text-muted">{intro}</p>
      </section>

      <section className="flex flex-wrap gap-2" aria-label="Significado das cores">
        <Legenda cor="bg-favoravel" rotulo="Favorável" />
        <Legenda cor="bg-atencao" rotulo="Atenção" />
        <Legenda cor="bg-sky-500" rotulo="Contexto" />
        <Legenda cor="bg-pendente" rotulo="Sem registro" />
      </section>

      {carregando ? (
        <div className="flex items-center justify-center gap-2 rounded-xl2 border border-line bg-surface p-8 text-muted shadow-soft">
          <Loader2 size={18} className="animate-spin" aria-hidden />
          <span className="text-[0.9rem] font-semibold">Lendo as evidências da sua safra…</span>
        </div>
      ) : (
        <section className="space-y-3">
          {evidencias.map((e, i) => (
            <EvidenceCard key={`${e.tipo}-${i}`} evidencia={e} onAcao={() => void buscar()} />
          ))}
          {erroRede ? (
            <p className="px-1 text-[0.82rem] text-muted">
              Não deu para falar com o servidor. Verifique sua internet e toque em
              “Tentar de novo”.
            </p>
          ) : null}
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* RadarBloco (backend) → Evidencia (UI). O backend já traz o estado   */
/* honesto e as frases humanizadas; aqui é só casar os campos.         */
/* ------------------------------------------------------------------ */
function blocoParaEvidencia(b: RadarBloco, tipo: Evidencia["tipo"]): Evidencia {
  return {
    tipo,
    estado: b.estado,
    titulo: b.titulo,
    detalhe: b.detalhe,
    destaques: b.destaques,
    linhas: b.linhas,
    leitura: b.leitura,
    fonte: {
      nome: b.fonte?.nome ?? "—",
      periodo: b.fonte?.periodo,
      url: b.fonte?.url,
      limitacoes: b.fonte?.limitacoes,
    },
  };
}

function semConexao(tipo: Evidencia["tipo"], titulo: string): Evidencia {
  return {
    tipo,
    estado: "sem_conexao",
    titulo,
    detalhe:
      "Não deu para carregar este dado agora. Ele existe na base oficial — a conexão com o servidor é que falhou.",
    acao: { id: "retry", rotulo: "Tentar de novo" },
    fonte: { nome: "Dados oficiais (MAPA / Open-Meteo)" },
  };
}

function Legenda({ cor, rotulo }: { cor: string; rotulo: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-[0.8rem] font-semibold text-muted">
      <span className={`h-2.5 w-2.5 rounded-full ${cor}`} aria-hidden />
      {rotulo}
    </span>
  );
}
