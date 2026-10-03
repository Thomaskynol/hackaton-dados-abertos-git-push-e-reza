"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Sun, Moon, Map, Tag, Home, MessagesSquare, User, ChevronDown, LogOut, UserCog } from "lucide-react";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";
import { LogoMarca } from "@/components/Logo";

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
  const router = useRouter();
  const { perfil, carregado, sair } = usePerfil();
  const [dark, setDark] = useState(false);
  const [menuAberto, setMenuAberto] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // fecha o menu do perfil ao clicar fora ou apertar Escape
  useEffect(() => {
    if (!menuAberto) return;
    function onClique(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuAberto(false);
      }
    }
    function onTecla(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuAberto(false);
    }
    document.addEventListener("mousedown", onClique);
    document.addEventListener("keydown", onTecla);
    return () => {
      document.removeEventListener("mousedown", onClique);
      document.removeEventListener("keydown", onTecla);
    };
  }, [menuAberto]);

  function logout() {
    setMenuAberto(false);
    sair();
    router.replace("/login");
  }

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
            className="grid h-9 w-9 place-items-center overflow-hidden rounded-xl bg-[#142F24] shadow-soft"
            aria-hidden
          >
            <LogoMarca size={30} />
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
          <div ref={menuRef} className="relative hidden lg:block">
            <button
              type="button"
              onClick={() => setMenuAberto((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={menuAberto}
              aria-label="Abrir menu da conta"
              className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 shadow-soft transition hover:border-terra"
            >
              <span className="grid h-6 w-6 place-items-center rounded-full bg-terra-soft text-terra-ink text-xs font-bold">
                <User size={14} />
              </span>
              <span className="text-left text-[0.82rem] leading-tight">
                <span className="block font-bold text-ink">{pn}</span>
                <span className="block text-[0.72rem] text-muted">
                  {cultura ? `${cultura} · ` : ""}{perfil.municipio || perfil.uf}
                </span>
              </span>
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-dot" title="Online" />
              <ChevronDown
                size={15}
                className={`text-muted transition-transform ${menuAberto ? "rotate-180" : ""}`}
                aria-hidden
              />
            </button>

            {menuAberto ? (
              <div
                role="menu"
                aria-label="Menu da conta"
                className="absolute right-0 mt-2 w-52 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-lift animate-fade-up"
              >
                <Link
                  href="/conta"
                  role="menuitem"
                  onClick={() => setMenuAberto(false)}
                  className="flex items-center gap-2.5 px-3.5 py-2.5 text-[0.9rem] font-semibold text-ink transition hover:bg-canvas"
                >
                  <UserCog size={16} className="text-terra-ink" aria-hidden />
                  Meu perfil
                </Link>
                <button
                  type="button"
                  role="menuitem"
                  onClick={logout}
                  className="flex w-full items-center gap-2.5 border-t border-line px-3.5 py-2.5 text-left text-[0.9rem] font-semibold text-red-600 transition hover:bg-red-50"
                >
                  <LogOut size={16} aria-hidden />
                  Sair da conta
                </button>
              </div>
            ) : null}
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

