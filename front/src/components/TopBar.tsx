"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sun, Moon, Map, Tag, Home, MessagesSquare, User } from "lucide-react";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";

const ABAS = [
  { href: "/mapa", rotulo: "Mapa", Icone: Map },
  { href: "/precos", rotulo: "Preços", Icone: Tag },
  { href: "/safra", rotulo: "Minha Safra", Icone: Home },
  { href: "/assistente", rotulo: "Assistente", Icone: MessagesSquare },
] as const;

/**
 * Barra superior moderna e responsiva:
 * - Em telas médias/grandes: exibe links de navegação e pílula do produtor.
 * - Em celulares: enxuta com logo e alternância do Modo Campo.
 */
export function TopBar({ titulo }: { titulo?: string }) {
  const pathname = usePathname();
  const { perfil, carregado } = usePerfil();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const salvo = localStorage.getItem("agropilot:tema");
    const prefereDark = typeof window !== "undefined" && window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const isDark = salvo ? salvo === "dark" : prefereDark;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function alternarTema() {
    const novo = !dark;
    setDark(novo);
    document.documentElement.classList.toggle("dark", novo);
    localStorage.setItem("agropilot:tema", novo ? "dark" : "light");
  }

  const pn = carregado && perfil.nome ? primeiroNome(perfil.nome) : null;
  const cultura = perfil.lavouras?.[0]?.cultura;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-surface/90 px-4 sm:px-6 lg:px-8 backdrop-blur-md transition-colors">
      {/* Brand / Logo */}
      <div className="flex items-center gap-3">
        <Link href="/mapa" className="flex items-center gap-2.5 transition hover:opacity-90">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-amber-600 to-terra text-base text-white shadow-soft"
            aria-hidden
          >
            🌱
          </span>
          <div className="flex flex-col">
            <span className="font-display text-[1.18rem] font-extrabold tracking-tight text-ink leading-none">
              {titulo ?? "AgroPilot"}
            </span>
            <span className="text-[0.68rem] font-bold uppercase tracking-wider text-terra-ink">
              Copiloto 24/7
            </span>
          </div>
        </Link>
      </div>

      {/* Desktop Navigation */}
      <nav aria-label="Navegação desktop" className="hidden md:flex items-center gap-1 rounded-full border border-line bg-canvas/80 p-1 shadow-soft">
        {ABAS.map(({ href, rotulo, Icone }) => {
          const ativo = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 rounded-full px-4 py-2 text-[0.88rem] font-bold transition-all ${
                ativo
                  ? "bg-surface text-terra-ink shadow-soft"
                  : "text-muted hover:text-ink hover:bg-surface/50"
              }`}
            >
              <Icone size={17} strokeWidth={ativo ? 2.5 : 2} aria-hidden />
              <span>{rotulo}</span>
            </Link>
          );
        })}
      </nav>

      {/* Produtor Info + Modo Dark Toggle */}
      <div className="flex items-center gap-2.5">
        {pn ? (
          <div className="hidden lg:flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 shadow-soft">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-terra-soft text-terra-ink text-xs font-bold">
              <User size={14} />
            </span>
            <div className="text-left text-[0.82rem] leading-tight">
              <p className="font-bold text-ink">{pn}</p>
              <p className="text-[0.72rem] text-muted">
                {cultura ? `${cultura} · ` : ""}{perfil.municipio || perfil.uf}
              </p>
            </div>
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-dot" title="Online" />
          </div>
        ) : null}

        <button
          onClick={alternarTema}
          aria-pressed={dark}
          aria-label={dark ? "Alternar para modo normal (claro)" : "Alternar para modo dark (escuro)"}
          className="inline-flex min-h-[42px] items-center justify-center gap-1.5 rounded-full border border-line bg-surface px-3.5 text-[0.82rem] font-bold text-muted transition hover:border-terra hover:text-ink shadow-soft active:scale-95"
        >
          {dark ? (
            <>
              <Sun size={16} className="text-amber-400" />
              <span className="hidden sm:inline">Modo Normal</span>
            </>
          ) : (
            <>
              <Moon size={16} className="text-terra-ink" />
              <span className="hidden sm:inline">Modo Dark</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
}

