"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePerfil } from "@/lib/perfil-context";
import { LogoCompleta } from "@/components/Logo";

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
        <span className="grid place-items-center overflow-hidden rounded-3xl bg-[#142F24] p-5 shadow-soft">
          <LogoCompleta width={176} />
        </span>
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
