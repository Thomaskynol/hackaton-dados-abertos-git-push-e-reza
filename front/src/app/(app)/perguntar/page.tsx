"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Compat: rota antiga /perguntar agora é /assistente (apoio). */
export default function PerguntarCompat() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/assistente");
  }, [router]);
  return null;
}
