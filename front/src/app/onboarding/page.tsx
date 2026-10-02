"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowLeft, Check } from "lucide-react";
import { Button } from "@/components/Button";
import { AudioButton } from "@/components/AudioButton";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";
import { CULTURAS, SOLOS } from "@/lib/dados-locais";

type Passo = "nome" | "cidade" | "cultura" | "solo" | "fim";
const ORDEM: Passo[] = ["nome", "cidade", "cultura", "solo", "fim"];

/**
 * Onboarding conversacional: UMA pergunta por tela. Barra de progresso,
 * botão voltar, "ouvir" em cada pergunta, escolhas visuais quando dá.
 */
export default function Onboarding() {
  const router = useRouter();
  const { perfil, atualizar } = usePerfil();

  const [passo, setPasso] = useState<Passo>("nome");
  const [nome, setNome] = useState(perfil.nome);
  const [cidade, setCidade] = useState(
    perfil.municipio ? `${perfil.municipio} - ${perfil.uf}` : "",
  );
  const [cultura, setCultura] = useState(perfil.lavouras[0]?.cultura ?? "");
  const [solo, setSolo] = useState(perfil.lavouras[0]?.solo ?? "");

  const indice = ORDEM.indexOf(passo);
  const progresso = useMemo(() => ((indice + 1) / ORDEM.length) * 100, [indice]);
  const pn = primeiroNome(nome || "produtor");

  function avancar() {
    const prox = ORDEM[Math.min(indice + 1, ORDEM.length - 1)];
    setPasso(prox);
  }
  function voltar() {
    if (indice === 0) {
      router.push("/login");
      return;
    }
    setPasso(ORDEM[indice - 1]);
  }

  function concluir() {
    const [mun, uf] = cidade.split("-").map((s) => s.trim());
    atualizar({
      nome,
      municipio: mun || "Araraquara",
      uf: (uf || "SP").toUpperCase(),
      lavouras: [{ cultura, area_ha: null, solo, irrigacao: null }],
      onboardingConcluido: true,
    });
    router.push("/mapa");
  }

  const perguntas: Record<Passo, string> = {
    nome: "Como posso te chamar?",
    cidade: `Prazer, ${pn}! Em qual cidade fica sua terra?`,
    cultura: "O que você planta ou quer plantar?",
    solo: "Como é a terra do seu lote?",
    fim: `Tudo certo, ${pn}! Já posso te acompanhar.`,
  };
  const subtitulos: Record<Passo, string> = {
    nome: "Uma coisa de cada vez. Sem pressa.",
    cidade: "Pode escrever cidade e estado, ex.: Araraquara - SP.",
    cultura: "Toque na que mais combina. Dá para mudar depois.",
    solo: "Se não souber, escolha pela dica.",
    fim: "Você pode ajustar tudo isso quando quiser no seu perfil.",
  };

  const podeAvancar =
    (passo === "nome" && nome.trim().length >= 2) ||
    (passo === "cidade" && cidade.trim().length >= 2) ||
    (passo === "cultura" && !!cultura) ||
    (passo === "solo" && !!solo);

  return (
    <main className="flex min-h-screen flex-col bg-canvas px-6 pb-10 pt-10">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col">
        {/* progresso */}
        <div className="flex items-center gap-3">
          <button
            onClick={voltar}
            aria-label="Voltar"
            className="grid h-10 w-10 place-items-center rounded-full border border-line text-muted transition hover:border-terra"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-terra transition-all duration-300"
              style={{ width: `${progresso}%` }}
            />
          </div>
          <span className="text-[0.85rem] font-semibold text-muted">
            {Math.min(indice + 1, ORDEM.length)}/{ORDEM.length}
          </span>
        </div>

        {/* pergunta */}
        <div className="mt-10">
          <div className="flex items-start justify-between gap-3">
            <h1 className="font-display text-[1.7rem] font-extrabold leading-tight text-ink">
              {perguntas[passo]}
            </h1>
            <AudioButton texto={`${perguntas[passo]} ${subtitulos[passo]}`} />
          </div>
          <p className="mt-2 text-[1.05rem] text-muted">{subtitulos[passo]}</p>
        </div>

        {/* corpo do passo */}
        <div className="mt-8 flex-1">
          {passo === "nome" && (
            <input
              autoFocus
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Ex.: Antônio"
              className="min-h-[60px] w-full rounded-xl2 border border-line bg-surface px-5 text-[1.2rem] text-ink shadow-soft outline-none focus:border-terra"
            />
          )}

          {passo === "cidade" && (
            <input
              autoFocus
              value={cidade}
              onChange={(e) => setCidade(e.target.value)}
              placeholder="Ex.: Araraquara - SP"
              className="min-h-[60px] w-full rounded-xl2 border border-line bg-surface px-5 text-[1.2rem] text-ink shadow-soft outline-none focus:border-terra"
            />
          )}

          {passo === "cultura" && (
            <div className="grid grid-cols-2 gap-3">
              {CULTURAS.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCultura(c.id)}
                  aria-pressed={cultura === c.id}
                  className={`flex min-h-[96px] flex-col items-center justify-center gap-1 rounded-xl2 border-2 bg-surface shadow-soft transition ${
                    cultura === c.id ? "border-terra bg-terra-soft" : "border-line hover:border-terra"
                  }`}
                >
                  <span className="text-3xl" aria-hidden>{c.emoji}</span>
                  <span className="font-bold text-ink">{c.nome}</span>
                </button>
              ))}
            </div>
          )}

          {passo === "solo" && (
            <div className="space-y-3">
              {SOLOS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSolo(s.id)}
                  aria-pressed={solo === s.id}
                  className={`flex w-full items-center gap-4 rounded-xl2 border-2 bg-surface p-4 text-left shadow-soft transition ${
                    solo === s.id ? "border-terra bg-terra-soft" : "border-line hover:border-terra"
                  }`}
                >
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-canvas text-xl" aria-hidden>
                    🪨
                  </span>
                  <span>
                    <span className="block font-bold text-ink">{s.nome}</span>
                    <span className="block text-[0.92rem] text-muted">{s.dica}</span>
                  </span>
                  {solo === s.id && <Check size={22} className="ml-auto text-terra" />}
                </button>
              ))}
            </div>
          )}

          {passo === "fim" && (
            <div className="rounded-xl2 border border-line bg-surface p-5 shadow-soft">
              <Resumo rotulo="Nome" valor={nome} />
              <Resumo rotulo="Cidade" valor={cidade} />
              <Resumo
                rotulo="Cultura"
                valor={CULTURAS.find((c) => c.id === cultura)?.nome ?? "—"}
              />
              <Resumo
                rotulo="Terra"
                valor={SOLOS.find((s) => s.id === solo)?.nome ?? "—"}
                ultimo
              />
            </div>
          )}
        </div>

        {/* ação */}
        <div className="pt-6">
          {passo === "fim" ? (
            <Button bloco onClick={concluir}>
              Começar a usar <ArrowRight size={20} />
            </Button>
          ) : (
            <Button bloco onClick={avancar} disabled={!podeAvancar}>
              Continuar <ArrowRight size={20} />
            </Button>
          )}
        </div>
      </div>
    </main>
  );
}

function Resumo({ rotulo, valor, ultimo }: { rotulo: string; valor: string; ultimo?: boolean }) {
  return (
    <div className={`flex items-center justify-between py-2.5 ${ultimo ? "" : "border-b border-line"}`}>
      <span className="text-muted">{rotulo}</span>
      <span className="font-bold text-ink">{valor || "—"}</span>
    </div>
  );
}
