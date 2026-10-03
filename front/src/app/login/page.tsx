"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Phone, ArrowRight } from "lucide-react";
import { Button } from "@/components/Button";
import { usePerfil } from "@/lib/perfil-context";
import { ApiError, getConta, login } from "@/lib/api";

/**
 * Entrada com telefone (sem senha para decorar).
 * Tenta login no backend; 404 -> oferece criar conta em /signup.
 */
export default function Login() {
  const router = useRouter();
  const { perfil, atualizar, aplicarConta } = usePerfil();
  const [tel, setTel] = useState(perfil.telefone);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [naoEncontrada, setNaoEncontrada] = useState(false);

  function formatar(v: string) {
    const d = v.replace(/\D/g, "").slice(0, 11);
    if (d.length <= 2) return d;
    if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    if (tel.replace(/\D/g, "").length < 10 || carregando) return;
    setCarregando(true);
    setErro(null);
    setNaoEncontrada(false);
    const telefone = tel;
    atualizar({ telefone });
    try {
      const conta = await login(telefone);
      let completa = conta;
      try {
        completa = await getConta(conta.id);
      } catch {
        /* login já trouxe a conta cheia; segue com ela */
      }
      aplicarConta(completa, telefone);
      router.push(completa.onboardingConcluido ? "/mapa" : "/onboarding");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNaoEncontrada(true);
      } else {
        setErro("Sem conexão — tente de novo quando tiver internet. Seu telefone ficou salvo no aparelho.");
      }
    } finally {
      setCarregando(false);
    }
  }

  const pergunta = "Entre com seu telefone. É rápido e sem senha para decorar.";

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-line bg-surface/90 backdrop-blur-md p-6 sm:p-8 shadow-card card-hover">
        <div className="flex items-center gap-3">
          <span
            className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-amber-600 to-terra text-2xl text-white shadow-soft"
            aria-hidden
          >
            🌱
          </span>
          <div>
            <h1 className="font-display text-2xl font-extrabold text-ink">AgroPilot</h1>
            <p className="text-sm font-medium text-muted">Copiloto Inteligente 24/7</p>
          </div>
        </div>

        <div className="mt-8">
          <div className="flex items-start justify-between gap-3">
            <h2 className="font-display text-[1.5rem] font-extrabold leading-tight text-ink">
              Bem-vindo ao campo
            </h2>
          </div>
          <p className="mt-1.5 text-[0.98rem] text-muted">{pergunta}</p>
        </div>

        <form onSubmit={entrar} className="mt-6">
          <label htmlFor="tel" className="mb-2 block text-sm font-bold text-ink">
            Seu telefone (WhatsApp)
          </label>
          <div className="flex items-center gap-3 rounded-xl2 border border-line bg-canvas px-4 shadow-soft transition-all focus-within:border-terra focus-within:ring-2 focus-within:ring-terra/20">
            <Phone size={20} className="text-muted" aria-hidden />
            <input
              id="tel"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              required
              value={tel}
              onChange={(e) => setTel(formatar(e.target.value))}
              placeholder="(16) 99999-9999"
              className="min-h-[54px] w-full bg-transparent text-[1.05rem] font-semibold text-ink outline-none placeholder:text-muted"
            />
          </div>
          <p className="mt-2 text-[0.9rem] text-muted">
            Novo por aqui? Depois de entrar você informa seu nome no cadastro.
          </p>

          <Button type="submit" bloco className="mt-6 shadow-soft" disabled={tel.replace(/\D/g, "").length < 10 || carregando}>
            {carregando ? "Entrando…" : "Continuar"} <ArrowRight size={20} />
          </Button>
        </form>

        {naoEncontrada ? (
          <div className="mt-6 rounded-xl2 border border-terra bg-terra-soft p-4" role="status">
            <p className="font-bold text-terra-ink">Conta não encontrada, crie sua conta.</p>
            <Link
              href="/signup"
              className="mt-3 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft"
            >
              Criar conta <ArrowRight size={20} aria-hidden />
            </Link>
          </div>
        ) : null}

        {erro ? (
          <p className="mt-4 text-[0.95rem] font-semibold text-muted" role="status">{erro}</p>
        ) : null}

        <p className="mt-6 text-center text-[0.95rem] text-muted">
          Ainda não tem conta?{" "}
          <Link href="/signup" className="font-bold text-terra-ink underline">
            Criar conta
          </Link>
        </p>

        <p className="mt-6 text-center text-[0.8rem] text-muted leading-relaxed">
          🔒 Dados protegidos e alimentados por fontes públicas oficiais:<br />
          <strong>ZARC · MAPA · Embrapa · Agrofit · CONAB · ANA</strong>
        </p>
      </div>
    </main>
  );
}
