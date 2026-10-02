"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowLeft, MapPin } from "lucide-react";
import { Button } from "@/components/Button";
import { AudioButton } from "@/components/AudioButton";
import { MapaBrasil } from "@/components/MapaBrasil";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";
import { CULTURAS } from "@/lib/dados-locais";
import { UFS, ufDoPerfil } from "@/lib/mapa-local";
import { patchConta, postProdutor } from "@/lib/api";
import type { UFSigla } from "@/lib/types";

type Passo = "nome" | "local" | "cultura" | "fim";
const ORDEM: Passo[] = ["nome", "local", "cultura", "fim"];

/**
 * Onboarding conversacional: UMA pergunta por tela. Barra de progresso,
 * botão voltar, "ouvir" em cada pergunta, escolhas visuais quando dá.
 * Local = MapaBrasil (compacto) + UF: define {municipio, uf, cod_ibge}.
 * Solo NUNCA perguntado — inferido no servidor via ZARC.
 */
export default function Onboarding() {
  const router = useRouter();
  const { perfil, atualizar } = usePerfil();

  const [passo, setPasso] = useState<Passo>("nome");
  const [nome, setNome] = useState(perfil.nome);
  const [uf, setUf] = useState<UFSigla>(ufDoPerfil(perfil.uf));
  const [municipio, setMunicipio] = useState<{ ibge: string; nome: string } | null>(
    perfil.cod_ibge && perfil.municipio ? { ibge: perfil.cod_ibge, nome: perfil.municipio } : null,
  );
  const [cultura, setCultura] = useState(perfil.lavouras[0]?.cultura ?? "");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

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

  /** Persiste no backend e marca onboardingConcluido (local + PATCH quando há id). */
  async function concluir() {
    if (!municipio || salvando) return;
    setSalvando(true);
    setErro(null);
    const base = {
      nome,
      telefone: perfil.telefone,
      municipio: municipio.nome,
      uf,
      cod_ibge: municipio.ibge,
      lavouras: [{ cultura, area_ha: null, solo: null, irrigacao: null }],
      onboardingConcluido: true,
    };
    try {
      if (perfil.id) {
        const c = await patchConta(perfil.id, {
          nome,
          municipio: municipio.nome,
          uf,
          cod_ibge: municipio.ibge,
          codigo_ibge: municipio.ibge,
          lavouras: [{ cultura, area_ha: null }],
          onboardingConcluido: true,
        });
        atualizar({
          ...base,
          id: c.id,
          telefone: perfil.telefone || c.telefone,
          cod_ibge: c.cod_ibge || municipio.ibge,
        });
      } else {
        const criado = await postProdutor({
          nome,
          telefone: perfil.telefone,
          municipio: municipio.nome,
          uf,
          cod_ibge: municipio.ibge,
          cultura,
        });
        atualizar({ ...base, id: criado.id });
      }
    } catch {
      // sem backend: segue local; sincroniza depois. Nada é inventado.
      setErro("Sem conexão — salvamos no aparelho e sincronizamos depois.");
      atualizar(base);
    } finally {
      setSalvando(false);
      router.push("/mapa");
    }
  }

  const perguntas: Record<Passo, string> = {
    nome: "Como posso te chamar?",
    local: `Prazer, ${pn}! Onde fica sua terra?`,
    cultura: "O que você planta ou quer plantar?",
    fim: `Tudo certo, ${pn}! Já posso te acompanhar.`,
  };
  const subtitulos: Record<Passo, string> = {
    nome: "Uma coisa de cada vez. Sem pressa.",
    local: "Escolha o estado e toque no seu município no mapa.",
    cultura: "Toque na que mais combina. Dá para mudar depois.",
    fim: "Você pode ajustar tudo isso quando quiser no seu perfil.",
  };

  const podeAvancar =
    (passo === "nome" && nome.trim().length >= 2) ||
    (passo === "local" && municipio != null) ||
    (passo === "cultura" && !!cultura);

  return (
    <main className="flex min-h-screen flex-col bg-canvas px-4 sm:px-6 pb-10 pt-10">
      <div className={`mx-auto flex w-full ${passo === "local" ? "max-w-2xl" : "max-w-md"} flex-1 flex-col transition-all duration-300`}>
        {/* progresso */}
        <div className="flex items-center gap-3">
          <button
            onClick={voltar}
            aria-label="Voltar"
            className="grid h-10 w-10 place-items-center rounded-full border border-line bg-surface text-muted transition hover:border-terra shadow-soft"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-terra transition-all duration-300"
              style={{ width: `${progresso}%` }}
            />
          </div>
          <span className="text-[0.85rem] font-bold text-muted">
            {Math.min(indice + 1, ORDEM.length)}/{ORDEM.length}
          </span>
        </div>

        {/* pergunta */}
        <div className="mt-8 sm:mt-10">
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

          {passo === "local" && (
            <div className="space-y-3">
              <label htmlFor="uf-onboarding" className="text-[0.82rem] font-bold uppercase tracking-wide text-muted">
                Estado (UF)
              </label>
              <div className="relative">
                <MapPin size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
                <select
                  id="uf-onboarding"
                  value={uf}
                  onChange={(e) => {
                    setUf(e.target.value as UFSigla);
                    setMunicipio(null);
                  }}
                  className="min-h-[52px] w-full appearance-none rounded-xl2 border border-line bg-surface pl-10 pr-4 text-[1.05rem] font-semibold text-ink"
                >
                  {UFS.map((u) => (
                    <option key={u.sigla} value={u.sigla}>
                      {u.nome} ({u.sigla})
                    </option>
                  ))}
                </select>
              </div>
              <MapaBrasil
                selecionada={uf}
                aoSelecionar={(nova) => {
                  setUf(nova);
                  setMunicipio(null);
                }}
                municipioIbge={municipio?.ibge ?? null}
                aoSelecionarMunicipio={(ibge, nomeMun) => setMunicipio({ ibge, nome: nomeMun })}
              />
              {municipio ? (
                <p className="rounded-xl2 border border-terra bg-terra-soft px-4 py-3 text-[0.95rem] font-bold text-terra-ink" role="status">
                  {municipio.nome} · IBGE {municipio.ibge}
                </p>
              ) : (
                <p className="text-[0.92rem] text-muted">Toque no estado para ver os municípios, depois toque no seu município.</p>
              )}
            </div>
          )}

          {passo === "cultura" && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {CULTURAS.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCultura(c.id)}
                  aria-pressed={cultura === c.id}
                  className={`flex min-h-[96px] flex-col items-center justify-center gap-1 rounded-xl2 border-2 bg-surface shadow-soft transition card-hover ${
                    cultura === c.id ? "border-terra bg-terra-soft/80" : "border-line hover:border-terra"
                  }`}
                >
                  <span className="text-3xl" aria-hidden>{c.emoji}</span>
                  <span className="font-bold text-ink">{c.nome}</span>
                </button>
              ))}
            </div>
          )}

          {passo === "fim" && (
            <div className="rounded-xl2 border border-line bg-surface p-5 shadow-soft">
              <Resumo rotulo="Nome" valor={nome} />
              <Resumo rotulo="Cidade" valor={municipio ? `${municipio.nome} - ${uf}` : "—"} />
              <Resumo
                rotulo="Cultura"
                valor={CULTURAS.find((c) => c.id === cultura)?.nome ?? "—"}
              />
              <Resumo
                rotulo="Solo da sua região (ZARC)"
                valor="Identificado pela sua região — sem pergunta"
                ultimo
              />
            </div>
          )}
        </div>

        {erro && passo === "fim" ? (
          <p className="pt-3 text-[0.9rem] font-semibold text-muted" role="status">{erro}</p>
        ) : null}

        {/* ação */}
        <div className="pt-6">
          {passo === "fim" ? (
            <Button bloco onClick={concluir} disabled={!municipio || salvando}>
              {salvando ? "Salvando…" : "Começar a usar"} <ArrowRight size={20} />
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
