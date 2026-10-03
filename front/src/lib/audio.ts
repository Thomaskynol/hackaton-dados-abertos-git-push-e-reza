"use client";

/**
 * Hooks de áudio — tudo no navegador, sem backend.
 *
 * - useGravacao: captura o microfone (MediaRecorder) e devolve o blob. A
 *   TRANSCRIÇÃO real virá do backend depois; aqui só gravamos e sinalizamos.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export type EstadoGravacao = "ocioso" | "gravando" | "processando" | "erro";

export function useGravacao(onConcluido?: (blob: Blob) => void) {
  const [estado, setEstado] = useState<EstadoGravacao>("ocioso");
  // Suporte detectado SÓ após montar (evita mismatch de hidratação SSR/CSR).
  const [suportado, setSuportado] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    setSuportado(
      typeof window !== "undefined" &&
        typeof navigator !== "undefined" &&
        !!navigator.mediaDevices &&
        typeof window.MediaRecorder !== "undefined",
    );
  }, []);

  const iniciar = useCallback(async () => {
    if (!suportado) {
      setEstado("erro");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        setEstado("processando");
        onConcluido?.(blob);
        setEstado("ocioso");
      };
      recorderRef.current = rec;
      rec.start();
      setEstado("gravando");
    } catch {
      setEstado("erro");
    }
  }, [suportado, onConcluido]);

  const parar = useCallback(() => {
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }, []);

  return { estado, iniciar, parar, suportado };
}
