"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, MapPin, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/Button";
import { AudioButton } from "@/components/AudioButton";
import { MapaBrasil } from "@/components/MapaBrasil";
import { usePerfil } from "@/lib/perfil-context";
import { CULTURAS } from "@/lib/dados-locais";
import { UFS, ufDoPerfil } from "@/lib/mapa-local";
import { getConta, patchConta, type Conta, type ContaLavoura } from "@/lib/api";
import type { UFSigla } from "@/lib/types";
import { useRouter } from "next/navigation";

/**
 * Minha conta: vê e edita nome, terra (UF + município no mapa) e lavouras
 * (cultura + área). Telefone é só leitura; solo ZARC é só leitura.
 * Salva via PATCH /api/produtor/{id}. Sem rede: mostra o cache do aparelho
 * e avisa — nunca número inventado.
 */
export default function ContaPage() {
  const router = useRouter();
  const { perfil, carregado, aplicarConta } = usePerfil();
  const [conta, setConta] = useState<Conta | null>(null);
  const [nome, setNome] = useState("");
  const [uf, setUf] = useState<UFSigla>("SP");
  const [municipio, setMunicipio] = useState<{ ibge: string; nome: string } | null>(null);
  const [lavouras, setLavouras] = useState<ContaLavoura[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    if (!carregado) return;
    if (!perfil.id) {
      setCarregando(false);
      return;
    }
    if (!perfil.onboardingConcluido) {
      router.replace("/onboarding");
      return;
    }
    let vivo = true;
    // cache local primeiro (tela nunca vazia)
    setNome(perfil.nome);
    setUf(ufDoPerfil(perfil.uf));
    setMunicipio(
      perfil.cod_ibge && perfil.municipio
        ? { ibge: perfil.cod_ibge, nome: perfil.municipio }
        : null,
    );
    setLavouras(perfil.lavouras.map((l) => ({ cultura: l.cultura, area_ha: l.area_ha })));
    getConta(perfil.id)
      .then((c) => {
        if (!vivo) return;
        setConta(c);
        setNome(c.nome || "");
        setUf(ufDoPerfil(c.uf));
        setMunicipio(
          c.cod_ibge && c.municipio ? { ibge: c.cod_ibge, nome: c.municipio } : null,
        );
        setLavouras((c.lavouras ?? []).map((l) => ({ ...l })));
      })
      .catch(() => {
        if (vivo)
          setErro("Sem conexão — mostrando dados salvos no aparelho. A edição salva quando a internet voltar.");
      })
      .finally(() => {
        if (vivo) setCarregando(false);
      });
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregado, perfil.id, perfil.onboardingConcluido]);

  if (!carregado || carregando) return null;

  // sem conta (nunca logou / storage limpo): caminho honesto p/ entrar
  if (!perfil.id) {
    return (
      <div className="space-y-4">
        <Link
          href="/mapa"
          className="inline-flex min-h-[44px] items-center gap-1.5 font-bold text-terra-ink"
        >
          <ArrowLeft size={18} aria-hidden /> Voltar
        </Link>
        <section className="rounded-xl2 border border-line bg-surface p-5 shadow-card">
          <h1 className="font-display text-[1.5rem] font-extrabold text-ink">Minha conta</h1>
          <p className="mt-2 text-muted">
            Você ainda não entrou neste aparelho. Entre com seu telefone ou crie sua conta.
          </p>
          <div className="mt-4 space-y-2">
            <Link
              href="/login"
              className="inline-flex min-h-[52px] w-full items-center justify-center rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft"
            >
              Entrar
            </Link>
            <Link
              href="/signup"
              className="inline-flex min-h-[52px] w-full items-center justify-center rounded-xl2 border border-line bg-canvas px-5 font-bold text-terra-ink"
            >
              Criar conta
            </Link>
          </div>
        </section>
      </div>
    );
  }

  const telefone = perfil.telefone || conta?.telefone || "";
  const hectares = lavouras.reduce(
    (s, l) => s + (typeof l.area_ha === "number" && !Number.isNaN(l.area_ha) ? l.area_ha : 0),
    0,
  );
  const solo = conta?.solo_inferido ?? null;
  const lavouraInvalida = lavouras.some((l) => !l.cultura);

  function trocarLavoura(i: number, patch: Partial<ContaLavoura>) {
    setLavouras((lista) => lista.map((l, j) => (j === i ? { ...l, ...patch } : l)));
    setOk(null);
  }

  function tirarLavoura(i: number) {
    setLavouras((lista) => lista.filter((_, j) => j !== i));
    setOk(null);
  }

  function porArea(i: number, bruto: string) {
    if (bruto.trim() === "") {
      trocarLavoura(i, { area_ha: null });
      return;
    }
    const v = Number(bruto.replace(",", "."));
    trocarLavoura(i, { area_ha: Number.isNaN(v) || v < 0 ? null : v });
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!perfil.id || salvando || !nome.trim() || lavouraInvalida) return;
    setSalvando(true);
    setErro(null);
    setOk(null);
    try {
      const resp = await patchConta(perfil.id, {
        nome: nome.trim(),
        municipio: municipio?.nome ?? "",
        uf,
        cod_ibge: municipio?.ibge ?? "",
        codigo_ibge: municipio?.ibge ?? "",
        lavouras: lavouras.map((l) => ({ cultura: l.cultura, area_ha: l.area_ha })),
      });
      setConta(resp);
      aplicarConta(resp, telefone);
      setOk("Salvo. Sua conta está atualizada.");
    } catch {
      setErro("Sem conexão — nada foi salvo no servidor. Tente de novo com internet.");
    } finally {
      setSalvando(false);
    }
  }

  const intro = "Aqui você ajusta seu nome, sua terra e suas lavouras. O telefone e o solo são só leitura.";

  return (
    <div className="space-y-5">
      <Link
        href="/mapa"
        className="inline-flex min-h-[44px] items-center gap-1.5 font-bold text-terra-ink"
      >
        <ArrowLeft size={18} aria-hidden /> Voltar ao Mapa
      </Link>

      <section>
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
            Minha conta
          </h1>
          <AudioButton texto={intro} />
        </div>
        <p className="mt-1 text-muted">{intro}</p>
      </section>

      {erro ? (
        <p className="rounded-xl2 border border-line bg-surface px-4 py-3 text-[0.95rem] font-semibold text-muted" role="status">
          {erro}
        </p>
      ) : null}
      {ok ? (
        <p className="rounded-xl2 border border-terra bg-terra-soft px-4 py-3 text-[0.95rem] font-bold text-terra-ink" role="status">
          {ok}
        </p>
      ) : null}

      <form onSubmit={salvar} className="space-y-5">
        {/* dados */}
        <section className="space-y-3 rounded-xl2 border border-line bg-surface p-4 shadow-card">
          <h2 className="font-display text-[1.1rem] font-extrabold text-ink">Seus dados</h2>
          <div>
            <label htmlFor="conta-nome" className="mb-2 block font-semibold text-ink">
              Nome
            </label>
            <input
              id="conta-nome"
              type="text"
              autoComplete="name"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Seu nome"
              className="min-h-[52px] w-full rounded-xl2 border border-line bg-canvas px-4 text-[1.05rem] text-ink outline-none focus:border-terra"
            />
          </div>
          <div>
            <label htmlFor="conta-tel" className="mb-2 block font-semibold text-ink">
              Telefone (não muda)
            </label>
            <input
              id="conta-tel"
              type="tel"
              readOnly
              aria-readonly
              value={telefone}
              placeholder="Sem telefone no aparelho"
              className="min-h-[52px] w-full rounded-xl2 border border-line bg-canvas px-4 text-[1.05rem] text-muted outline-none"
            />
            <p className="mt-1 text-[0.85rem] text-muted">
              Para trocar de número, crie outra conta em /signup.
            </p>
          </div>
        </section>

        {/* terra */}
        <section className="space-y-3 rounded-xl2 border border-line bg-surface p-4 shadow-card">
          <h2 className="font-display text-[1.1rem] font-extrabold text-ink">Sua terra</h2>
          <div>
            <label htmlFor="uf-conta" className="mb-2 block text-[0.82rem] font-bold uppercase tracking-wide text-muted">
              Estado (UF)
            </label>
            <div className="relative">
              <MapPin size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
              <select
                id="uf-conta"
                value={uf}
                onChange={(e) => {
                  setUf(e.target.value as UFSigla);
                  setMunicipio(null);
                  setOk(null);
                }}
                className="min-h-[52px] w-full appearance-none rounded-xl2 border border-line bg-canvas pl-10 pr-4 text-[1.05rem] font-semibold text-ink"
              >
                {UFS.map((u) => (
                  <option key={u.sigla} value={u.sigla}>
                    {u.nome} ({u.sigla})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <MapaBrasil
            selecionada={uf}
            aoSelecionar={(nova) => {
              setUf(nova);
              setMunicipio(null);
              setOk(null);
            }}
            municipioIbge={municipio?.ibge ?? null}
            aoSelecionarMunicipio={(ibge, nomeMun) => {
              setMunicipio({ ibge, nome: nomeMun });
              setOk(null);
            }}
          />
          {municipio ? (
            <p className="rounded-xl2 border border-terra bg-terra-soft px-4 py-3 text-[0.95rem] font-bold text-terra-ink" role="status">
              {municipio.nome} · IBGE {municipio.ibge}
            </p>
          ) : (
            <p className="text-[0.92rem] text-muted">Toque no seu município no mapa.</p>
          )}
        </section>

        {/* lavouras */}
        <section className="space-y-3 rounded-xl2 border border-line bg-surface p-4 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-display text-[1.1rem] font-extrabold text-ink">Lavouras</h2>
            <span className="text-[0.95rem] font-bold text-terra-ink" aria-live="polite">
              Total: {lavouras.length === 0 ? "—" : `${hectares.toLocaleString("pt-BR")} ha`}
            </span>
          </div>
          {lavouras.length === 0 ? (
            <p className="text-[0.95rem] text-muted">Nenhuma lavoura ainda. Toque abaixo para adicionar.</p>
          ) : (
            <ul className="space-y-3">
              {lavouras.map((l, i) => (
                <li key={i} className="space-y-2 rounded-xl border border-line bg-canvas p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[0.82rem] font-bold uppercase tracking-wide text-muted">
                      Lavoura {i + 1}
                    </span>
                    <button
                      type="button"
                      onClick={() => tirarLavoura(i)}
                      aria-label={`Remover lavoura ${i + 1}`}
                      className="grid h-[44px] w-[44px] place-items-center rounded-full text-muted transition hover:bg-surface hover:text-ink"
                    >
                      <Trash2 size={18} aria-hidden />
                    </button>
                  </div>
                  <label className="block">
                    <span className="mb-1 block text-[0.9rem] font-semibold text-ink">Cultura</span>
                    <select
                      value={l.cultura}
                      onChange={(e) => trocarLavoura(i, { cultura: e.target.value })}
                      aria-label={`Cultura da lavoura ${i + 1}`}
                      className="min-h-[52px] w-full appearance-none rounded-xl2 border border-line bg-surface px-4 text-[1rem] font-semibold text-ink"
                    >
                      <option value="">Escolher cultura…</option>
                      {!CULTURAS.some((c) => c.id === l.cultura) && l.cultura ? (
                        <option value={l.cultura}>{l.cultura}</option>
                      ) : null}
                      {CULTURAS.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.emoji} {c.nome}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-[0.9rem] font-semibold text-ink">Área (ha)</span>
                    <input
                      type="number"
                      min={0}
                      step="any"
                      inputMode="decimal"
                      value={l.area_ha ?? ""}
                      onChange={(e) => porArea(i, e.target.value)}
                      placeholder="Ex.: 2,5"
                      aria-label={`Área em hectares da lavoura ${i + 1}`}
                      className="min-h-[52px] w-full rounded-xl2 border border-line bg-surface px-4 text-[1rem] text-ink outline-none focus:border-terra"
                    />
                  </label>
                </li>
              ))}
            </ul>
          )}
          <Button
            type="button"
            variante="secundaria"
            bloco
            onClick={() => {
              setLavouras((lista) => [...lista, { cultura: "", area_ha: null }]);
              setOk(null);
            }}
          >
            <Plus size={18} aria-hidden /> Adicionar lavoura
          </Button>
        </section>

        {/* solo */}
        <section className="rounded-xl2 border border-line bg-surface p-4 shadow-card">
          <h2 className="font-display text-[1.1rem] font-extrabold text-ink">Solo (ZARC)</h2>
          <p className="mt-1 text-[1rem] text-ink">
            {solo ? `Predominante na sua região: ${solo}.` : "Ainda sem dado — identificado pela sua região quando o ZARC ligar."}
          </p>
          <p className="mt-1 text-[0.85rem] text-muted">
            Leitura automática do servidor; não dá para editar aqui.
          </p>
        </section>

        <Button type="submit" bloco disabled={!nome.trim() || lavouraInvalida || salvando}>
          {salvando ? "Salvando…" : "Salvar"}
        </Button>
      </form>
    </div>
  );
}
