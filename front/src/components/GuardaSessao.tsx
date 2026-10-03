"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { usePerfil } from "@/lib/perfil-context";

/**
 * Guarda de rota client-side das telas internas (grupo (app)).
 *
 * Sem sessão (perfil.id null depois do storage carregar) → manda para /login,
 * guardando a rota pedida em ?next= para voltar depois do login.
 *
 * IMPORTANTE: isto é guarda de NAVEGAÇÃO (UX), não segurança. A API ainda não
 * exige token — os dados só ficam de fato protegidos quando houver auth no
 * backend. Enquanto carrega o storage, não decide nada (evita flash de login).
 */
export function GuardaSessao({ children }: { children: React.ReactNode }) {
  const { perfil, carregado } = usePerfil();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!carregado) return;
    if (!perfil.id) {
      const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
    }
  }, [carregado, perfil.id, pathname, router]);

  // enquanto o storage não carregou, ou já sabemos que não há sessão, não
  // pisca o conteúdo interno — o redirect assume.
  if (!carregado || !perfil.id) return null;
  return <>{children}</>;
}
