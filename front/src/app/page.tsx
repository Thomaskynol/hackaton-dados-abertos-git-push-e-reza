"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePerfil } from "@/lib/perfil-context";

/** Porta de entrada: Mapa (consultor comercial) se já cadastrou, senão login. */
export default function Raiz() {
  const router = useRouter();
  const { perfil, carregado } = usePerfil();

  useEffect(() => {
    if (!carregado) return;
    router.replace(perfil.onboardingConcluido ? "/mapa" : "/login");
  }, [carregado, perfil.onboardingConcluido, router]);

  // Segurança: se o carregamento do perfil travar (ex.: storage bloqueado),
  // não deixa o produtor preso no splash — manda para o login após 2,5s.
  useEffect(() => {
    if (carregado) return;
    const t = setTimeout(() => router.replace("/login"), 2500);
    return () => clearTimeout(t);
  }, [carregado, router]);

  return (
    <main className="grid min-h-screen place-items-center bg-canvas px-6">
      <div className="flex flex-col items-center gap-3 text-muted">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-terra text-2xl text-white">
          🌱
        </span>
        <p className="font-display text-lg font-bold text-ink">AgroPilot</p>
        <p className="text-[0.9rem]">Abrindo seu consultor comercial…</p>
        {/* Saída manual: se o redirecionamento automático falhar, ninguém fica preso aqui. */}
        <a
          href="/login"
          className="mt-2 inline-flex min-h-[52px] items-center justify-center rounded-xl2 bg-terra px-6 font-bold text-white shadow-soft"
        >
          Entrar
        </a>
      </div>
    </main>
  );
}
