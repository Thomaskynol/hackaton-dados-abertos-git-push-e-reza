"use client";

/**
 * Estado do perfil do produtor, persistido em localStorage.
 * ZERO integração com backend: tudo vive no dispositivo por enquanto.
 * Quando a API entrar, trocamos salvar()/carregar() por chamadas HTTP.
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

const CHAVE = "agropilot:perfil";

/** Perfil inicial honesto: vazio, cidade sugerida da região do piloto. */
const PERFIL_VAZIO: Perfil = {
  id: null,
  nome: "",
  telefone: "",
  municipio: "Araraquara",
  uf: "SP",
  cod_ibge: "3503208",
  lavouras: [],
  onboardingConcluido: false,
};

interface PerfilCtx {
  perfil: Perfil;
  carregado: boolean;
  atualizar: (patch: Partial<Perfil>) => void;
  reset: () => void;
}

const Ctx = createContext<PerfilCtx | null>(null);

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
