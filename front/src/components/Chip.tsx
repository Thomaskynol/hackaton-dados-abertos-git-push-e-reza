import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  emoji?: string;
  ativo?: boolean;
}

/** Pílula tocável (sugestões de pergunta, atalhos). Reconhecer, não lembrar. */
export function Chip({ emoji, ativo, className = "", children, ...rest }: Props) {
  return (
    <button
      className={`inline-flex min-h-[44px] items-center gap-2 whitespace-nowrap rounded-full border px-4 text-[0.95rem] font-semibold transition ${
        ativo
          ? "border-terra bg-terra-soft text-terra-ink"
          : "border-line bg-surface text-ink hover:border-terra"
      } ${className}`}
      {...rest}
    >
      {emoji && <span aria-hidden>{emoji}</span>}
      {children}
    </button>
  );
}
