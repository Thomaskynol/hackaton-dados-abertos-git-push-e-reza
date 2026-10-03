"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Phone, ArrowRight, Lock, User, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/Button";
import { LogoCompleta } from "@/components/Logo";
import { usePerfil } from "@/lib/perfil-context";
import {
  ApiError,
  getConta,
  getMe,
  login,
  signup,
  onboardingChat,
  type Conta,
} from "@/lib/api";

/**
 * Tela única de entrada: abas Entrar / Cadastrar (inspirada no protótipo
 * hackathon/login, mas no layout atual — Tailwind, tokens do tema, Logo real).
 *
 * - Entrar: telefone + PIN → login (token de sessão guardado no perfil-context).
 * - Cadastrar: nome + telefone + PIN → cria conta (entra logada) → cadastro por
 *   CHAT (cidade→cod_ibge real, culturas→canônicas, área), salvando a cada passo.
 */
type Aba = "entrar" | "cadastrar";

function formatarTel(v: string) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}
function soDigitosPin(v: string) {
  return v.replace(/\D/g, "").slice(0, 6);
}

export default function Entrada() {
  const [aba, setAba] = useState<Aba>("entrar");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 py-10">
      <div className="mb-6 flex flex-col items-center">
        <span className="grid place-items-center overflow-hidden rounded-3xl bg-[#142F24] p-4 shadow-soft">
          <LogoCompleta width={150} />
        </span>
      </div>

      <div className="w-full max-w-md rounded-2xl border border-line bg-surface/90 p-6 shadow-card backdrop-blur-md sm:p-8">
        {/* Abas */}
        <div
          role="tablist"
          aria-label="Entrar ou cadastrar"
          className="relative mb-6 grid grid-cols-2 rounded-full border border-line bg-canvas p-1"
        >
          <span
            aria-hidden
            className={`absolute inset-y-1 w-[calc(50%-0.25rem)] rounded-full bg-terra shadow-soft transition-transform duration-300 ${
              aba === "cadastrar" ? "translate-x-[calc(100%+0.5rem)]" : "translate-x-0"
            }`}
          />
          {(["entrar", "cadastrar"] as Aba[]).map((a) => (
            <button
              key={a}
              role="tab"
              aria-selected={aba === a}
              onClick={() => setAba(a)}
              className={`relative z-10 rounded-full py-2.5 text-[0.92rem] font-bold transition-colors ${
                aba === a ? "text-white" : "text-muted hover:text-ink"
              }`}
            >
              {a === "entrar" ? "Entrar" : "Cadastrar"}
            </button>
          ))}
        </div>

        {aba === "entrar" ? (
          <PainelEntrar irParaCadastro={() => setAba("cadastrar")} />
        ) : (
          <PainelCadastrar />
        )}
      </div>

      <p className="mt-6 max-w-md text-center text-[0.8rem] leading-relaxed text-muted">
        🔒 Dados protegidos e alimentados por fontes públicas oficiais:
        <br />
        <strong>ZARC · MAPA · Embrapa · Agrofit · CONAB · ANA</strong>
      </p>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Aba ENTRAR                                                          */
/* ------------------------------------------------------------------ */
function PainelEntrar({ irParaCadastro }: { irParaCadastro: () => void }) {
  const router = useRouter();
  const { perfil, atualizar, aplicarConta } = usePerfil();
  const [tel, setTel] = useState(perfil.telefone);
  const [pin, setPin] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [naoEncontrada, setNaoEncontrada] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    if (tel.replace(/\D/g, "").length < 10 || carregando) return;
    setCarregando(true);
    setErro(null);
    setNaoEncontrada(false);
    const telefone = tel;
    atualizar({ telefone });
    try {
      const conta = await login(telefone, pin || undefined);
      let completa = conta;
      try {
        completa = await getConta(conta.id);
      } catch {
        /* login já trouxe a conta cheia */
      }
      aplicarConta(completa, telefone);
      let destino = completa.onboardingConcluido ? "/mapa" : "/onboarding";
      if (completa.onboardingConcluido && typeof window !== "undefined") {
        const next = new URLSearchParams(window.location.search).get("next");
        if (next && next.startsWith("/") && !next.startsWith("//")) destino = next;
      }
      router.push(destino);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNaoEncontrada(true);
      } else if (err instanceof ApiError && err.status === 401) {
        setErro("PIN incorreto. Tente de novo.");
      } else if (err instanceof ApiError && err.status === 422) {
        setErro("Essa conta tem PIN. Digite seu PIN para entrar.");
      } else {
        setErro("Sem conexão — tente de novo quando tiver internet.");
      }
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-[1.5rem] font-extrabold leading-tight text-ink">
        Bem-vindo de volta
      </h1>
      <p className="mt-1.5 text-[0.98rem] text-muted">
        Entre com seu telefone e o seu PIN.
      </p>

      <form onSubmit={entrar} className="mt-6 space-y-4">
        <CampoTelefone id="login-tel" value={tel} onChange={(v) => setTel(formatarTel(v))} />
        <CampoPin
          id="login-pin"
          value={pin}
          onChange={(v) => setPin(soDigitosPin(v))}
          dica="Seu PIN de 4 a 6 números."
        />
        <Button
          type="submit"
          bloco
          className="shadow-soft"
          disabled={tel.replace(/\D/g, "").length < 10 || carregando}
        >
          {carregando ? "Entrando…" : "Entrar no AgroPilot"} <ArrowRight size={20} />
        </Button>
      </form>

      {naoEncontrada ? (
        <div className="mt-5 rounded-xl2 border border-terra bg-terra-soft p-4" role="status">
          <p className="font-bold text-terra-ink">
            Não encontrei esse telefone. Vamos criar sua conta?
          </p>
          <button
            onClick={irParaCadastro}
            className="mt-3 inline-flex min-h-[48px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft"
          >
            Criar conta grátis <ArrowRight size={18} aria-hidden />
          </button>
        </div>
      ) : null}

      {erro ? (
        <p className="mt-4 text-[0.95rem] font-semibold text-red-600" role="status">
          {erro}
        </p>
      ) : null}

      <p className="mt-6 text-center text-[0.95rem] text-muted">
        Ainda não tem conta?{" "}
        <button onClick={irParaCadastro} className="font-bold text-terra-ink underline">
          Cadastre-se grátis
        </button>
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Aba CADASTRAR: dados básicos -> cadastro por chat                    */
/* ------------------------------------------------------------------ */
function PainelCadastrar() {
  const { perfil, atualizar, aplicarConta } = usePerfil();
  const [fase, setFase] = useState<"dados" | "chat">("dados");
  const [nome, setNome] = useState(perfil.nome);
  const [tel, setTel] = useState(perfil.telefone);
  const [pin, setPin] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [conta, setConta] = useState<Conta | null>(null);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    if (nome.trim().length < 2 || tel.replace(/\D/g, "").length < 10 || carregando) return;
    if (pin.length < 4) {
      setErro("Crie um PIN de 4 a 6 números — é o que vai proteger sua conta.");
      return;
    }
    setCarregando(true);
    setErro(null);
    const telefone = tel;
    atualizar({ nome: nome.trim(), telefone });
    try {
      const c = await signup(telefone, nome.trim(), pin);
      aplicarConta(c, telefone); // guarda token + perfil
      setConta(c);
      setFase("chat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setErro("Esse telefone já tem conta. Use a aba Entrar.");
      } else if (err instanceof ApiError && err.status === 422) {
        setErro("Confira o nome, o telefone e o PIN (4 a 6 números).");
      } else {
        setErro("Sem conexão — tente de novo quando tiver internet. Nada foi criado.");
      }
    } finally {
      setCarregando(false);
    }
  }

  if (fase === "chat" && conta) {
    return <ChatCadastro conta={conta} />;
  }

  return (
    <div>
      <h1 className="font-display text-[1.5rem] font-extrabold leading-tight text-ink">
        Começar é simples
      </h1>
      <p className="mt-1.5 text-[0.98rem] text-muted">
        Só o seu nome, telefone e um PIN. Depois a gente conversa pra montar sua safra.
      </p>

      <form onSubmit={criar} className="mt-6 space-y-4">
        <div>
          <label htmlFor="reg-nome" className="mb-2 block text-sm font-bold text-ink">
            Como você se chama?
          </label>
          <div className="flex items-center gap-3 rounded-xl2 border border-line bg-canvas px-4 shadow-soft transition-all focus-within:border-terra focus-within:ring-2 focus-within:ring-terra/20">
            <User size={20} className="text-muted" aria-hidden />
            <input
              id="reg-nome"
              type="text"
              autoComplete="given-name"
              required
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Ex.: Antônio"
              className="min-h-[54px] w-full bg-transparent text-[1.05rem] font-semibold text-ink outline-none placeholder:text-muted"
            />
          </div>
        </div>

        <CampoTelefone id="reg-tel" value={tel} onChange={(v) => setTel(formatarTel(v))} />
        <CampoPin
          id="reg-pin"
          value={pin}
          onChange={(v) => setPin(soDigitosPin(v))}
          dica="Crie um PIN de 4 a 6 números — fácil de lembrar, difícil de adivinhar."
        />

        <Button
          type="submit"
          bloco
          className="shadow-soft"
          disabled={nome.trim().length < 2 || tel.replace(/\D/g, "").length < 10 || pin.length < 4 || carregando}
        >
          {carregando ? "Criando…" : "Continuar"} <ArrowRight size={20} />
        </Button>
      </form>

      {erro ? (
        <p className="mt-4 text-[0.95rem] font-semibold text-red-600" role="status">
          {erro}
        </p>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Cadastro por CHAT — extração real no backend, salva a cada passo    */
/* ------------------------------------------------------------------ */
type Bolha = { autor: "bot" | "voce"; texto: string };

function ChatCadastro({ conta }: { conta: Conta }) {
  const router = useRouter();
  const { aplicarConta } = usePerfil();
  const [bolhas, setBolhas] = useState<Bolha[]>([
    {
      autor: "bot",
      texto: `Prazer, ${conta.nome?.split(" ")[0] || "produtor"}! Em qual cidade fica a sua terra? Me diga a cidade e o estado — ex.: Araraquara - SP.`,
    },
  ]);
  const [etapa, setEtapa] = useState(2); // etapa 1 (nome) já veio do cadastro
  const [resposta, setResposta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [concluido, setConcluido] = useState(false);
  const fimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [bolhas, enviando]);

  const total = 4;
  const passoAtual = Math.min(Math.max(etapa - 1, 1), total);
  const pct = Math.round((passoAtual / total) * 100);

  async function enviar() {
    const txt = resposta.trim();
    if (!txt || enviando) return;
    setResposta("");
    setBolhas((b) => [...b, { autor: "voce", texto: txt }]);
    setEnviando(true);
    try {
      const r = await onboardingChat({
        etapa,
        resposta: txt,
        produtor_id: conta.id,
        telefone: conta.telefone,
      });
      setBolhas((b) => [...b, { autor: "bot", texto: r.pergunta }]);
      // só avança a etapa quando o backend confirma (erro => repete a mesma)
      setEtapa(r.proximo_passo);
      if (r.proximo_passo >= 5) {
        setConcluido(true);
        // atualiza o perfil com o que foi salvo e segue pro app
        try {
          const atual = await getMe();
          aplicarConta(atual, conta.telefone);
        } catch {
          /* segue com o cache local */
        }
        setTimeout(() => router.push("/mapa"), 1800);
      }
    } catch {
      setBolhas((b) => [
        ...b,
        { autor: "bot", texto: "Deu um probleminha de conexão. Pode repetir sua resposta?" },
      ]);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <h1 className="font-display text-[1.3rem] font-extrabold text-ink">
          Vamos montar sua safra
        </h1>
        <span className="text-[0.78rem] font-bold text-muted">
          Passo {passoAtual} de {total}
        </span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-canvas">
        <div
          className="h-full rounded-full bg-terra transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div
        role="log"
        aria-live="polite"
        className="flex max-h-[46vh] min-h-[220px] flex-col gap-2.5 overflow-y-auto rounded-xl2 border border-line bg-canvas p-3"
      >
        {bolhas.map((b, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[0.92rem] leading-relaxed ${
              b.autor === "bot"
                ? "self-start bg-surface text-ink shadow-soft"
                : "self-end bg-terra text-white"
            }`}
          >
            {b.texto}
          </div>
        ))}
        {enviando ? (
          <div className="self-start inline-flex items-center gap-2 rounded-2xl bg-surface px-3.5 py-2.5 text-muted shadow-soft">
            <Loader2 size={15} className="animate-spin" aria-hidden /> digitando…
          </div>
        ) : null}
        <div ref={fimRef} />
      </div>

      {!concluido ? (
        <div className="mt-3 flex items-center gap-2">
          <input
            value={resposta}
            onChange={(e) => setResposta(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") enviar();
            }}
            disabled={enviando}
            placeholder="Digite sua resposta…"
            aria-label="Sua resposta"
            className="min-h-[52px] w-full rounded-xl2 border border-line bg-canvas px-4 text-[1rem] font-semibold text-ink outline-none transition-all focus:border-terra focus:ring-2 focus:ring-terra/20 disabled:opacity-60"
          />
          <button
            onClick={enviar}
            disabled={enviando || !resposta.trim()}
            aria-label="Enviar resposta"
            className="grid min-h-[52px] min-w-[52px] place-items-center rounded-xl2 bg-terra text-white shadow-soft transition hover:brightness-105 disabled:opacity-50"
          >
            <Send size={20} />
          </button>
        </div>
      ) : (
        <p className="mt-4 flex items-center justify-center gap-2 text-[0.95rem] font-semibold text-terra-ink">
          <Loader2 size={16} className="animate-spin" aria-hidden /> Preparando seu AgroPilot…
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Campos reutilizados                                                 */
/* ------------------------------------------------------------------ */
function CampoTelefone({
  id,
  value,
  onChange,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-bold text-ink">
        Seu telefone (WhatsApp)
      </label>
      <div className="flex items-center gap-3 rounded-xl2 border border-line bg-canvas px-4 shadow-soft transition-all focus-within:border-terra focus-within:ring-2 focus-within:ring-terra/20">
        <Phone size={20} className="text-muted" aria-hidden />
        <input
          id={id}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="(16) 99999-9999"
          className="min-h-[54px] w-full bg-transparent text-[1.05rem] font-semibold text-ink outline-none placeholder:text-muted"
        />
      </div>
    </div>
  );
}

function CampoPin({
  id,
  value,
  onChange,
  dica,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  dica: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-bold text-ink">
        PIN de acesso
      </label>
      <div className="flex items-center gap-3 rounded-xl2 border border-line bg-canvas px-4 shadow-soft transition-all focus-within:border-terra focus-within:ring-2 focus-within:ring-terra/20">
        <Lock size={20} className="text-muted" aria-hidden />
        <input
          id={id}
          type="password"
          inputMode="numeric"
          autoComplete="off"
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="••••"
          className="min-h-[54px] w-full bg-transparent text-[1.3rem] font-bold tracking-[0.3em] text-ink outline-none placeholder:tracking-normal placeholder:text-muted"
        />
      </div>
      <p className="mt-2 text-[0.88rem] text-muted">{dica}</p>
    </div>
  );
}
