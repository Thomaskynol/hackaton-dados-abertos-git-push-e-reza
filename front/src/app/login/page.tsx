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
    <main className="flex min-h-screen flex-col bg-canvas px-6 pb-10 pt-16">
      <div className="mx-auto w-full max-w-md">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-terra text-2xl text-white" aria-hidden>
            🌱
          </span>
          <div>
            <h1 className="font-display text-2xl font-extrabold text-ink">AgroPilot</h1>
            <p className="text-muted">Seu copiloto da roça</p>
          </div>
        </div>

        <div className="mt-12">
          <div className="flex items-start justify-between gap-3">
            <h2 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
              Vamos começar?
            </h2>
            <AudioButton texto={pergunta} />
          </div>
          <p className="mt-2 text-[1.05rem] text-muted">{pergunta}</p>
        </div>

        <form onSubmit={entrar} className="mt-8">
          <label htmlFor="tel" className="mb-2 block font-semibold text-ink">
            Seu telefone (WhatsApp)
          </label>
          <div className="flex items-center gap-3 rounded-xl2 border border-line bg-surface px-4 shadow-soft focus-within:border-terra">
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
              className="min-h-[56px] w-full bg-transparent text-[1.1rem] text-ink outline-none placeholder:text-muted"
            />
          </div>

          <Button type="submit" bloco className="mt-6" disabled={tel.replace(/\D/g, "").length < 10}>
            Continuar <ArrowRight size={20} />
          </Button>
        </form>

        <p className="mt-8 text-center text-[0.9rem] text-muted">
          Dados de fontes públicas: ZARC/MAPA · Embrapa · Agrofit · ANA
        </p>
      </div>
    </main>
  );
}
