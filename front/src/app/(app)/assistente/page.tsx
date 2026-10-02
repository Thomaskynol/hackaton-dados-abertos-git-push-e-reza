"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Plus, History } from "lucide-react";
import { ChatBubble } from "@/components/ChatBubble";
import { ChatInput } from "@/components/ChatInput";
import { Chip } from "@/components/Chip";
import { usePerfil, precisaOnboarding, primeiroNome } from "@/lib/perfil-context";
import { SUGESTOES_CHAT, responderLocal } from "@/lib/dados-locais";
import { infoDaUF } from "@/lib/mapa-local";
import {
  createSessao,
  getMensagens,
  listSessoes,
  postChat,
  postChatStream,
  type ChatMeta,
  type Sessao,
} from "@/lib/api";
import type { Intencao, Mensagem } from "@/lib/types";

/** Mensagem + ferramentas consultadas (render da página, sem mexer no ChatBubble). */
type Msg = Mensagem & { ferramentas?: string[] };

const INTENCOES: ReadonlySet<string> = new Set([
  "PLANEJAMENTO",
  "PRAGA",
  "CLIMA",
  "VENDA",
  "PERFIL",
  "SAUDACAO",
  "NAO_ENTENDI",
]);

function validarIntencao(v: unknown): Intencao | undefined {
  return typeof v === "string" && INTENCOES.has(v) ? (v as Intencao) : undefined;
}

/** dados.ferramentas_usadas pode vir [{name,args}] ou ["nome"] — normaliza p/ nomes. */
function extrairFerramentas(meta: ChatMeta | { dados?: unknown }): string[] {
  const dados = (meta as { dados?: unknown })?.dados as
    | { ferramentas_usadas?: unknown }
    | undefined;
  const lista = dados?.ferramentas_usadas;
  if (!Array.isArray(lista)) return [];
  const nomes = lista
    .map((f) =>
      typeof f === "string"
        ? f
        : f && typeof f === "object"
          ? String((f as Record<string, unknown>)["name"] ?? "")
          : "",
    )
    .filter(Boolean);
  const unicos: string[] = [];
  for (const n of nomes) if (!unicos.includes(n)) unicos.push(n);
  return unicos;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapearMensagens(bruto: any[]): Msg[] {
  return (bruto ?? []).map((m, i) => {
    const r = (m ?? {}) as Record<string, unknown>;
    return {
      id: String(r["id"] ?? `h-${i}`),
      autor: r["autor"] === "copiloto" ? "copiloto" : "usuario",
      texto: String(r["texto"] ?? ""),
      intencao: validarIntencao(r["intencao"]),
      fonte: typeof r["fonte"] === "string" ? r["fonte"] : undefined,
      ferramentas: extrairFerramentas({ dados: r["dados"] }),
      horario: formatarHora(r["criado_em"]),
    } satisfies Msg;
  });
}

function formatarHora(v: unknown): string {
  if (typeof v === "string" && v) {
    const d = new Date(v);
    if (!Number.isNaN(d.getTime()))
      return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  }
  return agora();
}

/**
 * Assistente: apoio para interpretar o Mapa e os preços. Voz, texto e chips.
 * Resposta REAL via POST /api/chat/stream (fallback POST /api/chat);
 * responderLocal só quando o fetch falha (modo offline honesto).
 */
export default function Assistente() {
  return (
    <Suspense>
      <ConteudoAssistente />
    </Suspense>
  );
}

function ConteudoAssistente() {
  const params = useSearchParams();
  const router = useRouter();
  const ufCtx = (params.get("uf") ?? "").toUpperCase();
  const { perfil, carregado } = usePerfil();
  const nome = perfil.nome || "produtor";
  const pn = primeiroNome(nome);
  const local = perfil.municipio ? `${perfil.municipio}/${perfil.uf}` : null;
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [pensando, setPensando] = useState(false);
  const [sessoes, setSessoes] = useState<Sessao[]>([]);
  const [sessaoId, setSessaoId] = useState<string | null>(null);
  const [mostrarHist, setMostrarHist] = useState(false);
  const fimRef = useRef<HTMLDivElement>(null);

  const produtorId = perfil.id || perfil.telefone || "";

  useEffect(() => {
    if (precisaOnboarding(perfil, carregado)) router.replace("/onboarding");
  }, [perfil, carregado, router]);

  function saudacao(): Msg {
    const info = infoDaUF(ufCtx);
    const base = local
      ? `Oi, ${pn} de ${local}!`
      : `Oi, ${pn}!`;
    return {
      id: "boas-vindas",
      autor: "copiloto",
      texto: info
        ? `${base} Vi que você estava olhando ${info.nome} (${info.sigla}) no Mapa. Posso ajudar a interpretar o cenário comercial de lá — preço, piso e canais. O que quer entender?`
        : `${base} Sou o apoio do Mapa: ajudo a interpretar preço, piso e canais da sua região. Toque numa sugestão abaixo ou mande a sua dúvida.`,
      fonte: "AgroPilot",
      horario: agora(),
    };
  }

  // mensagem inicial do copiloto (nome + município reais do perfil)
  useEffect(() => {
    if (!carregado) return;
    setMsgs([saudacao()]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregado]);

  // lista sessões existentes (só com identidade; sem id/telefone = só local)
  useEffect(() => {
    if (!carregado || !produtorId) return;
    listSessoes(produtorId)
      .then(setSessoes)
      .catch(() => {
        /* sem backend: sem histórico, segue local */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregado, produtorId]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msgs.length, pensando]);

  async function garantirSessao(): Promise<string | null> {
    if (sessaoId) return sessaoId;
    if (!produtorId) return null;
    try {
      const s = await createSessao({
        produtor_id: produtorId,
        uf: perfil.uf || undefined,
        cod_ibge: perfil.cod_ibge || undefined,
      });
      setSessaoId(s.id);
      setSessoes((l) => [{ ...s }, ...l]);
      return s.id;
    } catch {
      return null; // envia sem sessao_id; back auto-cria quando ligar
    }
  }

  function novaConversa() {
    setSessaoId(null);
    setMsgs([saudacao()]);
  }

  async function abrirSessao(id: string) {
    setSessaoId(id);
    try {
      const bruto = await getMensagens(id);
      const hist = mapearMensagens(bruto);
      setMsgs(hist.length > 0 ? hist : [saudacao()]);
    } catch {
      /* fetch falhou: mantém conversa atual */
    }
  }

  async function enviar(texto: string) {
    const minha: Msg = {
      id: `u-${Date.now()}`,
      autor: "usuario",
      texto,
      horario: agora(),
    };
    setMsgs((m) => [...m, minha]);
    setPensando(true);

    // sem identidade (nem id do back, nem telefone): só fallback local honesto
    if (!produtorId) {
      const r = responderLocal(texto, pn);
      setMsgs((m) => [...m, { ...r, id: `c-${Date.now()}`, horario: agora() }]);
      setPensando(false);
      return;
    }

    const sid = await garantirSessao();
    const idC = `c-${Date.now()}`;
    setMsgs((m) => [...m, { id: idC, autor: "copiloto", texto: "", horario: agora() }]);

    let meta: ChatMeta = {};
    let acumulado = "";
    const aplicarDelta = (d: string) => {
      // progresso de ferramenta ("🔍 consultando …") é transitório: mostra
      // enquanto não há conteúdo real, nunca entra na resposta final
      if (d.startsWith("🔍")) {
        if (!acumulado) setMsgs((prev) => prev.map((x) => (x.id === idC ? { ...x, texto: d } : x)));
        return;
      }
      acumulado += d;
      const snap = acumulado;
      setPensando(false);
      setMsgs((prev) => prev.map((x) => (x.id === idC ? { ...x, texto: snap } : x)));
    };

    try {
      await postChatStream(
        { produtor_id: produtorId, mensagem: texto, sessao_id: sid ?? undefined },
        {
          onMeta: (m) => {
            meta = m;
          },
          onDelta: aplicarDelta,
          onDone: () => {},
        },
      );
      if (!acumulado.trim()) throw new Error("stream vazio");
      const ferramentas = extrairFerramentas(meta);
      setMsgs((prev) =>
        prev.map((x) =>
          x.id === idC
            ? {
                ...x,
                texto: acumulado,
                fonte: meta.fonte ?? "AgroPilot",
                intencao: validarIntencao(meta.intencao),
                ferramentas: ferramentas.length > 0 ? ferramentas : undefined,
              }
            : x,
        ),
      );
      listSessoes(produtorId)
        .then(setSessoes)
        .catch(() => {});
    } catch {
      // fallback: POST simples; último recurso: responderLocal (offline honesto)
      try {
        const r = await postChat(produtorId, texto, sid ?? undefined);
        const ferramentas = extrairFerramentas(r);
        setMsgs((prev) =>
          prev.map((x) =>
            x.id === idC
              ? {
                  ...x,
                  texto: r.resposta,
                  fonte: r.fonte ?? "AgroPilot",
                  intencao: validarIntencao(r.intencao),
                  ferramentas: ferramentas.length > 0 ? ferramentas : undefined,
                }
              : x,
          ),
        );
      } catch {
        const r = responderLocal(texto, pn);
        setMsgs((prev) =>
          prev.map((x) => (x.id === idC ? { ...r, id: idC, horario: agora() } : x)),
        );
      }
    } finally {
      setPensando(false);
    }
  }

  function enviarAudio() {
    // o áudio foi captado; a transcrição real virá do backend.
    const aviso: Msg = {
      id: `u-audio-${Date.now()}`,
      autor: "usuario",
      texto: "🎙️ Áudio enviado",
      horario: agora(),
    };
    const resposta: Msg = {
      id: `c-audio-${Date.now()}`,
      autor: "copiloto",
      texto: `Recebi seu áudio, ${pn}. A transcrição da sua fala vai ser feita no servidor na próxima etapa. Por enquanto, pode tocar numa sugestão ou escrever sua pergunta.`,
      fonte: "AgroPilot",
      horario: agora(),
    };
    setMsgs((m) => [...m, aviso, resposta]);
  }

  if (!carregado) return null;

  return (
    <div className="flex min-h-[calc(100vh-8rem)] max-w-4xl mx-auto flex-col">
      {/* sessões estilo ChatGPT: nova conversa + histórico */}
      <div className="mb-3 flex items-center gap-2">
        <button
          onClick={novaConversa}
          className="inline-flex min-h-[44px] flex-1 items-center justify-center gap-1.5 rounded-xl2 border border-line bg-surface px-4 font-bold text-terra-ink shadow-soft transition hover:border-terra active:scale-[0.99]"
        >
          <Plus size={18} aria-hidden /> Nova conversa
        </button>
        {sessoes.length > 0 ? (
          <button
            onClick={() => setMostrarHist((v) => !v)}
            aria-expanded={mostrarHist}
            aria-label="Ver conversas anteriores"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-xl2 border border-line bg-surface px-4 font-bold text-muted transition hover:border-terra hover:text-ink shadow-soft"
          >
            <History size={18} aria-hidden />
            <span className="text-xs bg-terra-soft px-2 py-0.5 rounded-full text-terra-ink font-extrabold">{sessoes.length}</span>
          </button>
        ) : null}
      </div>
      {mostrarHist && sessoes.length > 0 ? (
        <ul className="mb-3 max-h-52 space-y-1 overflow-y-auto rounded-xl2 border border-line bg-surface p-2 shadow-card animate-fade-up" aria-label="Conversas anteriores">
          {sessoes.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => {
                  void abrirSessao(s.id);
                  setMostrarHist(false);
                }}
                aria-current={sessaoId === s.id}
                className={`block min-h-[44px] w-full truncate rounded-xl px-3 py-2 text-left text-[0.92rem] font-semibold transition ${
                  sessaoId === s.id ? "bg-terra-soft text-terra-ink font-bold" : "text-ink hover:bg-canvas"
                }`}
              >
                {typeof s.titulo === "string" && s.titulo ? s.titulo : "Conversa"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="flex-1 space-y-3.5 pb-4">
        {msgs.map((m) => (
          <div key={m.id}>
            <ChatBubble msg={m} />
            {m.autor === "copiloto" && m.ferramentas?.length ? (
              <p className="ml-2 mt-1 text-[0.76rem] font-semibold text-muted flex items-center gap-1">
                <span>🔍 Fontes consultadas:</span>
                <span className="text-terra-ink">{m.ferramentas.join(", ")}</span>
              </p>
            ) : null}
          </div>
        ))}
        {pensando && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-xl2 rounded-bl-md border border-line bg-surface px-4 py-3 shadow-soft">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-2 w-2 animate-wave rounded-full bg-terra"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
              <span className="text-xs text-muted font-medium ml-1">Analisando dados agronômicos…</span>
            </div>
          </div>
        )}
        <div ref={fimRef} />
      </div>

      {/* sugestões + input fixos acima da bottom-nav */}
      <div className="sticky bottom-20 md:bottom-2 mt-4 space-y-2.5 z-20 bg-canvas/80 backdrop-blur-md pt-2">
        <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
          {SUGESTOES_CHAT.map((s) => (
            <Chip key={s.texto} emoji={s.emoji} onClick={() => enviar(s.texto)}>
              {s.texto}
            </Chip>
          ))}
        </div>
        <ChatInput onEnviar={enviar} onAudio={enviarAudio} />
      </div>
    </div>
  );
}

function agora() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
