"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Phone, ArrowRight } from "lucide-react";
import { Button } from "@/components/Button";
import { AudioButton } from "@/components/AudioButton";
import { usePerfil } from "@/lib/perfil-context";

/**
 * Entrada só com telefone (sem senha para decorar).
 * Se o perfil já existe no aparelho, entra direto; senão, segue p/ onboarding.
 */
export default function Login() {
  const router = useRouter();
  const { perfil, atualizar } = usePerfil();
  const [tel, setTel] = useState(perfil.telefone);

  function formatar(v: string) {
    const d = v.replace(/\D/g, "").slice(0, 11);
    if (d.length <= 2) return d;
    if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }

  function entrar(e: React.FormEvent) {
    e.preventDefault();
    atualizar({ telefone: tel });
    router.push(perfil.onboardingConcluido ? "/mapa" : "/onboarding");
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
            <AudioButton texto={pergunta} />
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

          <Button type="submit" bloco className="mt-6 shadow-soft" disabled={tel.replace(/\D/g, "").length < 10}>
            <span>Acessar Copiloto</span>
            <ArrowRight size={19} />
          </Button>
        </form>

        <p className="mt-6 text-center text-[0.8rem] text-muted leading-relaxed">
          🔒 Dados protegidos e alimentados por fontes públicas oficiais:<br />
          <strong>ZARC · MAPA · Embrapa · CONAB · ANA</strong>
        </p>
      </div>
    </main>
  );
}
