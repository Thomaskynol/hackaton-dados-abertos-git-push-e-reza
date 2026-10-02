"use client";

/**
 * Estado do perfil do produtor, persistido em localStorage como cache.
 * `id` vem do backend (POST /api/produtor, upsert por telefone).
 * `cod_ibge` SEMPRE vem da escolha no mapa (onboarding local step) —
 * nunca default silencioso: vazio até o produtor tocar no município.
 */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Perfil } from "./types";
import type { Conta } from "./api";

const CHAVE = "agropilot:perfil";

/** Perfil inicial honesto: vazio, sem município silencioso. */
const PERFIL_VAZIO: Perfil = {
  id: null,
  nome: "",
  telefone: "",
  municipio: "",
  uf: "SP",
  cod_ibge: "",
  lavouras: [],
  onboardingConcluido: false,
};

interface PerfilCtx {
  perfil: Perfil;
  carregado: boolean;
  atualizar: (patch: Partial<Perfil>) => void;
  aplicarConta: (conta: Conta, telefoneDigitado?: string) => void;
  reset: () => void;
}

const Ctx = createContext<PerfilCtx | null>(null);

/** Conta do backend -> Perfil local (telefone digitado vence; GET sem telefone preserva). */
export function contaParaPerfil(conta: Conta, telefoneDigitado?: string): Perfil {
  return {
    id: conta.id,
    nome: conta.nome || "",
    telefone: telefoneDigitado || conta.telefone || "",
    municipio: conta.municipio || "",
    uf: conta.uf || "SP",
    cod_ibge: conta.cod_ibge || String(conta.codigo_ibge ?? "") || "",
    lavouras: (conta.lavouras ?? []).map((l) => ({
      cultura: l.cultura,
      area_ha: typeof l.area_ha === "number" ? l.area_ha : null,
      solo: typeof l.solo === "string" ? l.solo : null,
      irrigacao: typeof l.irrigacao === "boolean" ? l.irrigacao : null,
    })),
    onboardingConcluido: Boolean(conta.onboardingConcluido),
  };
}

export function PerfilProvider({ children }: { children: ReactNode }) {
  const [perfil, setPerfil] = useState<Perfil>(PERFIL_VAZIO);
  const [carregado, setCarregado] = useState(false);

  useEffect(() => {
    try {
      const bruto = localStorage.getItem(CHAVE);
      if (bruto) setPerfil({ ...PERFIL_VAZIO, ...JSON.parse(bruto) });
    } catch {
      /* ignora leitura inválida */
    }
    setCarregado(true);
  }, []);

  function persistir(p: Perfil) {
    setPerfil(p);
    try {
      localStorage.setItem(CHAVE, JSON.stringify(p));
    } catch {
      /* storage indisponível: segue só em memória */
    }
  }

  const valor = useMemo<PerfilCtx>(
    () => ({
      perfil,
      carregado,
      atualizar: (patch) => persistir({ ...perfil, ...patch }),
      aplicarConta: (conta, tel) =>
        persistir(contaParaPerfil(conta, tel ?? perfil.telefone)),
      reset: () => persistir(PERFIL_VAZIO),
    }),
    [perfil, carregado],
  );

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function usePerfil() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("usePerfil deve ser usado dentro de <PerfilProvider>");
  return ctx;
}

/**
 * Conta carregada mas onboarding pendente -> força /onboarding.
 * Sem id (offline/sem conta) não força: segue offline honesto.
 */
export function precisaOnboarding(perfil: Perfil, carregado: boolean): boolean {
  return carregado && !!perfil.id && !perfil.onboardingConcluido;
}

/** "Antônio da Silva" -> "Antônio". Preserva "Seu/Dona Fulano". */
export function primeiroNome(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  if (partes.length === 0) return "produtor";
  const p0 = partes[0].toLowerCase();
  if ((p0 === "seu" || p0 === "dona" || p0 === "dona") && partes[1]) {
    return `${partes[0]} ${partes[1]}`;
  }
  return partes[0];
}
