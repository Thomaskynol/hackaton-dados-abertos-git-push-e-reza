import { forwardRef, type ButtonHTMLAttributes } from "react";

type Variante = "primaria" | "secundaria" | "fantasma";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  bloco?: boolean;
}

/**
 * Botão com alvo de toque grande (min 52px de altura) para uso no campo.
 * Primária = terracota (ação principal da tela).
 */
const estilos: Record<Variante, string> = {
  primaria:
    "bg-terra text-white shadow-soft hover:brightness-95 active:brightness-90",
  secundaria:
    "bg-surface text-ink border border-line hover:border-terra active:bg-terra-soft",
  fantasma: "bg-transparent text-terra-ink hover:bg-terra-soft",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variante = "primaria", bloco, className = "", children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={`inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl2 px-5 text-[1.05rem] font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${
        estilos[variante]
      } ${bloco ? "w-full" : ""} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
});
