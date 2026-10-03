"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Phone, User, ArrowRight } from "lucide-react";
import { Button } from "@/components/Button";
import { usePerfil } from "@/lib/perfil-context";
import { ApiError, signup } from "@/lib/api";

/**
 * Criar conta: nome + telefone -> POST /api/produtor/signup.
 * Conta nova sempre passa pelo onboarding inicial.
 * 409 (telefone existe) -> link para /login.
 */
export default function Signup() {
  const router = useRouter();
  const { perfil, atualizar, aplicarConta } = usePerfil();
  const [nome, setNome] = useState(perfil.nome);
  const [tel, setTel] = useState(perfil.telefone);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [jaExiste, setJaExiste] = useState(false);

  function formatar(v: string) {
    const d = v.replace(/\D/g, "").slice(0, 11);
    if (d.length <= 2) return d;
    if (d.length <= 7) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
    return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
  }

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    if (nome.trim().length < 2 || tel.replace(/\D/g, "").length < 10 || carregando) return;
    setCarregando(true);
    setErro(null);
    setJaExiste(false);
    const telefone = tel;
    atualizar({ nome: nome.trim(), telefone });
    try {
      const conta = await signup(telefone, nome.trim());
      aplicarConta(conta, telefone);
      router.push("/onboarding");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setJaExiste(true);
      } else {
        setErro("Sem conexão — tente de novo quando tiver internet. Nada foi criado.");
      }
    } finally {
      setCarregando(false);
    }
  }

  const pergunta = "Crie sua conta com nome e telefone. Depois você informa sua terra no passo seguinte.";

  return (
    <main className="flex min-h-screen flex-col bg-canvas px-6 pb-10 pt-16">
      <div className="mx-auto w-full max-w-md">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-terra text-2xl text-white" aria-hidden>
            🌱
          </span>
          <div>
            <h1 className="font-display text-2xl font-extrabold text-ink">AgroPilot</h1>
            <p className="text-muted">Seu copiloto da roça</p>
          </div>
        </div>

        <div className="mt-12">
          <div className="flex items-start justify-between gap-3">
            <h2 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
              Criar conta
            </h2>
          </div>
          <p className="mt-2 text-[1.05rem] text-muted">{pergunta}</p>
        </div>

        <form onSubmit={criar} className="mt-8 space-y-4">
          <div>
            <label htmlFor="nome" className="mb-2 block font-semibold text-ink">
              Seu nome
            </label>
            <div className="flex items-center gap-3 rounded-xl2 border border-line bg-surface px-4 shadow-soft focus-within:border-terra">
              <User size={20} className="text-muted" aria-hidden />
              <input
                id="nome"
                type="text"
                autoComplete="name"
                required
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Antônio"
                className="min-h-[56px] w-full bg-transparent text-[1.1rem] text-ink outline-none placeholder:text-muted"
              />
            </div>
          </div>

          <div>
            <label htmlFor="tel" className="mb-2 block font-semibold text-ink">
              Seu telefone (WhatsApp)
            </label>
            <div className="flex items-center gap-3 rounded-xl2 border border-line bg-surface px-4 shadow-soft focus-within:border-terra">
              <Phone size={20} className="text-muted" aria-hidden />
              <input
                id="tel"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                required
                value={tel}
                onChange={(e) => setTel(formatar(e.target.value))}
                placeholder="(16) 99999-9999"
                className="min-h-[56px] w-full bg-transparent text-[1.1rem] text-ink outline-none placeholder:text-muted"
              />
            </div>
          </div>

          <Button
            type="submit"
            bloco
            disabled={nome.trim().length < 2 || tel.replace(/\D/g, "").length < 10 || carregando}
          >
            {carregando ? "Criando…" : "Criar conta"} <ArrowRight size={20} />
          </Button>
        </form>

        {jaExiste ? (
          <div className="mt-6 rounded-xl2 border border-terra bg-terra-soft p-4" role="status">
            <p className="font-bold text-terra-ink">Esse telefone já tem conta. Entre com ele.</p>
            <Link
              href="/login"
              className="mt-3 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft"
            >
              Ir para o login <ArrowRight size={20} aria-hidden />
            </Link>
          </div>
        ) : null}

        {erro ? (
          <p className="mt-4 text-[0.95rem] font-semibold text-muted" role="status">{erro}</p>
        ) : null}

        <p className="mt-6 text-center text-[0.95rem] text-muted">
          Já tem conta?{" "}
          <Link href="/login" className="font-bold text-terra-ink underline">
            Entrar
          </Link>
        </p>
      </div>
    </main>
  );
}
