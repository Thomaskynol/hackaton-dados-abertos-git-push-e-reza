"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * /signup foi unificado na tela de entrada (/login) com abas Entrar/Cadastrar.
 * Mantemos a rota só como redirecionamento, para links antigos não quebrarem.
 */
export default function SignupRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/login");
  }, [router]);
  return null;
}
