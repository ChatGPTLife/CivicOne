// 2025-02-26
"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getSocketClient } from "@/lib/socket";

const RadioContext = createContext<{
  radioEnabled: boolean;
  enableRadio: () => void;
  playIncidentRadio: () => void;
} | null>(null);

export function useRadio() {
  const ctx = useContext(RadioContext);
  return ctx ?? { radioEnabled: false, enableRadio: () => {}, playIncidentRadio: () => {} };
}

const RADIO_STORAGE_KEY = "civic1_radio_enabled";

export function RadioProvider({ children }: { children: React.ReactNode }) {
  const [radioEnabled, setRadioEnabled] = useState(false);
  const enabledRef = useRef(false);
  const queueRef = useRef<Array<{ role: string; text: string; audio_filename?: string }>>([]);
  const ignoreSocketRef = useRef(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(RADIO_STORAGE_KEY) === "1";
      setRadioEnabled(saved);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    enabledRef.current = radioEnabled;
  }, [radioEnabled]);

  const playStaticClip = useCallback(async (role: "controller" | "dispatch") => {
    const url = role === "controller" ? "/audio/Controller_Radio.mp3" : "/audio/Dispatch_Radio.mp3";
    const audio = new Audio(url);
    return new Promise<void>((resolve) => {
      const timeout = setTimeout(() => resolve(), 30000);
      audio.onended = () => {
        clearTimeout(timeout);
        resolve();
      };
      audio.onerror = () => {
        clearTimeout(timeout);
        resolve();
      };
      audio.play().catch(() => resolve());
    });
  }, []);

  const processingRef = useRef(false);

  const processQueue = useCallback(async () => {
    if (processingRef.current || queueRef.current.length === 0) return;
    processingRef.current = true;
    try {
      while (queueRef.current.length > 0) {
        const event = queueRef.current.shift()!;
        const role = (event.role || "").toLowerCase();
        if (role === "control" || role === "controller") {
          await playStaticClip("controller");
          await new Promise((r) => setTimeout(r, 2000));
        }
        if (role === "dispatch") {
          await playStaticClip("dispatch");
        }
      }
    } finally {
      processingRef.current = false;
    }
  }, [playStaticClip]);

  const enableRadio = useCallback(() => {
    setRadioEnabled(true);
    enabledRef.current = true;
    if (typeof window !== "undefined") {
      localStorage.setItem(RADIO_STORAGE_KEY, "1");
    }
    void processQueue();
  }, [processQueue]);

  const playIncidentRadio = useCallback(() => {
    if (!enabledRef.current) return;
    ignoreSocketRef.current = true;
    setTimeout(() => {
      ignoreSocketRef.current = false;
    }, 5000);
    queueRef.current.push({ role: "control", text: "" });
    queueRef.current.push({ role: "dispatch", text: "" });
    void processQueue();
  }, [processQueue]);

  useEffect(() => {
    const socket = getSocketClient();
    const onRadioComm = (event: { role: string; text: string; audio_filename?: string }) => {
      if (ignoreSocketRef.current) return;
      if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
        console.log("[Radio] received:", event.role, event.text);
      }
      if (!enabledRef.current) {
        queueRef.current.push(event);
        return;
      }
      queueRef.current.push(event);
      void processQueue();
    };
    socket.on("radio_comm", onRadioComm);
    return () => {
      socket.off("radio_comm", onRadioComm);
    };
  }, [processQueue]);

  return (
    <RadioContext.Provider value={{ radioEnabled, enableRadio, playIncidentRadio }}>
      {children}
    </RadioContext.Provider>
  );
}
