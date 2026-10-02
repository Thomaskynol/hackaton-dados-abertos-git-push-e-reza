"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

/**
 * Barra superior enxuta: marca + "Modo Campo" (alto contraste para sol forte).
 * O modo é lembrado em localStorage e aplicado na raiz do documento.
 */
export function TopBar({ titulo }: { titulo?: string }) {
  const [campo, setCampo] = useState(false);

  useEffect(() => {
    const salvo = localStorage.getItem("agropilot:modo-campo") === "1";
    setCampo(salvo);
    document.documentElement.classList.toggle("modo-campo", salvo);
  }, []);

  function alternar() {
    const novo = !campo;
    setCampo(novo);
    document.documentElement.classList.toggle("modo-campo", novo);
    localStorage.setItem("agropilot:modo-campo", novo ? "1" : "0");
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-surface/95 px-4 backdrop-blur">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-terra text-base text-white" aria-hidden>
          🌱
        </span>
        <span className="font-display text-[1.1rem] font-extrabold text-ink">
          {titulo ?? "AgroPilot"}
        </span>
      </div>
      <button
        onClick={alternar}
        aria-pressed={campo}
        aria-label="Alternar Modo Campo (alto contraste para o sol)"
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-full border border-line px-3 text-[0.8rem] font-semibold text-muted transition hover:border-terra"
      >
        {campo ? <Moon size={18} /> : <Sun size={18} />}
        <span className="hidden sm:inline">Modo Campo</span>
      </button>
    </header>
  );
}
