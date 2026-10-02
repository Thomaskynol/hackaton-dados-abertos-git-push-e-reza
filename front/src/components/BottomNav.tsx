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
      aria-label="Navegação principal"
      className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 backdrop-blur"
    >
      <ul className="mx-auto flex max-w-md items-stretch justify-around">
        {ABAS.map(({ href, rotulo, Icone }) => {
          const ativo = path === href || path.startsWith(href + "/");
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={ativo ? "page" : undefined}
                className={`flex min-h-[60px] min-w-[44px] flex-col items-center justify-center gap-0.5 px-1 text-[0.7rem] font-semibold transition ${
                  ativo ? "text-terra-ink" : "text-muted"
                }`}
              >
                <Icone size={24} strokeWidth={ativo ? 2.6 : 2} aria-hidden />
                {rotulo}
                <span
                  className={`mt-0.5 h-1 w-1 rounded-full ${ativo ? "bg-terra" : "bg-transparent"}`}
                  aria-hidden
                />
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

