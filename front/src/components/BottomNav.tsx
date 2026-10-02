"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Map, Tag, Home, MessagesSquare } from "lucide-react";

const ABAS = [
  { href: "/mapa", rotulo: "Mapa", Icone: Map },
  { href: "/precos", rotulo: "Preços", Icone: Tag },
  { href: "/safra", rotulo: "Minha Safra", Icone: Home },
  { href: "/assistente", rotulo: "Assistente", Icone: MessagesSquare },
] as const;

/** Navegação principal — Mapa primeiro (carro-chefe), Assistente por último (apoio). */
export function BottomNav() {
  const path = usePathname();

  return (
    <nav
      aria-label="Navegação móvel"
      className="md:hidden safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 backdrop-blur-lg shadow-lift transition-colors"
    >
      <ul className="mx-auto flex max-w-md items-stretch justify-around px-2 py-1">
        {ABAS.map(({ href, rotulo, Icone }) => {
          const ativo = path === href || path.startsWith(href + "/");
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={ativo ? "page" : undefined}
                className={`flex min-h-[58px] min-w-[44px] flex-col items-center justify-center gap-1 rounded-xl px-1 text-[0.72rem] font-bold transition-all ${
                  ativo ? "text-terra-ink bg-terra-soft/60 scale-[1.02]" : "text-muted hover:text-ink"
                }`}
              >
                <Icone size={22} strokeWidth={ativo ? 2.5 : 2} aria-hidden />
                <span>{rotulo}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

