// 2025-02-26
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSocketClient } from "@/lib/socket";

export interface LogEntry {
  id: string;
  ts: string;
  type: string;
  summary: string;
  payload?: unknown;
}

const MAX_LOGS = 500;
const EVENT_LABELS: Record<string, string> = {
  connect: "Socket connected",
  disconnect: "Socket disconnected",
  new_incident: "New incident",
  vehicle_dispatched: "Vehicle dispatched",
  vehicle_position: "Patrol position",
  vehicle_removed: "Vehicle removed",
  incident_attended: "Incident attended",
  patrol_alert: "Patrol alert",
  route_update: "Route updated",
  simulation_update: "Simulation update",
  radio_comm: "Radio comm",
};

function formatPayload(type: string, payload: unknown): string {
  if (payload == null) return "";
  const p = payload as Record<string, unknown>;
  switch (type) {
    case "new_incident":
      return p.type ? `Type: ${p.type}, Hex: ${p.hex_id ?? "—"}` : "";
    case "vehicle_dispatched":
      return p.vehicle
        ? `${(p.vehicle as Record<string, string>).type} → incident ${String(p.incident_id ?? "").slice(0, 8)}…`
        : p.message ?? "";
    case "vehicle_position":
      return p.vehicle
        ? `${(p.vehicle as Record<string, string>).type} → ${String((p.vehicle as Record<string, number>).latitude).slice(0, 8)}, ${String((p.vehicle as Record<string, number>).longitude).slice(0, 8)}`
        : "";
    case "vehicle_removed":
      return p.vehicle_id ? `Vehicle ${String(p.vehicle_id).slice(0, 8)}…` : "";
    case "incident_attended":
      return p.incident_id ? `Incident ${String(p.incident_id).slice(0, 8)}…` : "";
    case "patrol_alert":
      return p.alert_type ? `Alert: ${p.alert_type}` : "";
    case "route_update":
      return p.vehicle_id ? `Vehicle ${String(p.vehicle_id).slice(0, 8)}…` : "";
    case "simulation_update":
      return p.incidents ? `${(p.incidents as unknown[]).length} incidents` : "";
    case "radio_comm":
      return p.role ? `${p.role}: ${String(p.text ?? "").slice(0, 40)}…` : "";
    default:
      return "";
  }
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  const addLog = useCallback((type: string, payload?: unknown) => {
    const summary = formatPayload(type, payload);
    setLogs((prev) => {
      const next = [
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          ts: new Date().toISOString(),
          type,
          summary,
          payload,
        },
        ...prev,
      ];
      return next.slice(0, MAX_LOGS);
    });
  }, []);

  useEffect(() => {
    const socket = getSocketClient();

    const onConnect = () => {
      setConnected(true);
      addLog("connect");
    };
    const onDisconnect = () => {
      setConnected(false);
      addLog("disconnect");
    };

    const handlers: Record<string, (p?: unknown) => void> = {
      new_incident: (p) => addLog("new_incident", p),
      vehicle_dispatched: (p) => addLog("vehicle_dispatched", p),
      vehicle_position: (p) => addLog("vehicle_position", p),
      vehicle_removed: (p) => addLog("vehicle_removed", p),
      incident_attended: (p) => addLog("incident_attended", p),
      patrol_alert: (p) => addLog("patrol_alert", p),
      route_update: (p) => addLog("route_update", p),
      simulation_update: (p) => addLog("simulation_update", p),
      radio_comm: (p) => addLog("radio_comm", p),
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    if (socket.connected) {
      addLog("connect");
      setConnected(true);
    }

    for (const [event, handler] of Object.entries(handlers)) {
      socket.on(event, handler);
    }

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      for (const [event, handler] of Object.entries(handlers)) {
        socket.off(event, handler);
      }
    };
  }, [addLog]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    autoScrollRef.current = scrollTop + clientHeight >= scrollHeight - 20;
  };

  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [logs]);

  const filtered = filter.trim()
    ? logs.filter(
        (l) =>
          l.type.toLowerCase().includes(filter.toLowerCase()) ||
          l.summary.toLowerCase().includes(filter.toLowerCase()),
      )
    : logs;

  return (
    <div className="flex h-full flex-col bg-[#1a1d21]">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[#2d3238] bg-[#252a31] px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold text-white">Event Logs</h1>
          <p className="text-xs text-white/60">
            Real-time events, patrol updates, & dispatch activity
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs ${
              connected ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`}
            />
            {connected ? "Live" : "Disconnected"}
          </span>
          <input
            type="text"
            placeholder="Filter by type or summary…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded border border-white/10 bg-[#1a1d21] px-3 py-1.5 text-sm text-white placeholder-white/40 w-48"
          />
          <button
            type="button"
            onClick={() => setLogs([])}
            className="rounded border border-white/10 bg-[#1a1d21] px-3 py-1.5 text-xs text-white/80 hover:bg-white/10"
          >
            Clear
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-xs"
      >
        {filtered.length === 0 ? (
          <div className="flex h-full items-center justify-center text-white/40">
            {logs.length === 0
              ? "Waiting for events…"
              : "No logs match the filter."}
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {filtered.map((log) => (
              <div
                key={log.id}
                className="flex gap-3 px-4 py-2 hover:bg-white/5"
              >
                <span className="shrink-0 text-white/40">
                  {new Date(log.ts).toLocaleTimeString("en-IN", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
                <span
                  className={`shrink-0 rounded px-1.5 py-0.5 ${
                    log.type === "vehicle_position"
                      ? "bg-cyan-500/20 text-cyan-400"
                      : log.type === "vehicle_dispatched"
                        ? "bg-amber-500/20 text-amber-400"
                        : log.type === "new_incident"
                          ? "bg-red-500/20 text-red-400"
                          : log.type === "incident_attended"
                            ? "bg-emerald-500/20 text-emerald-400"
                            : log.type === "patrol_alert"
                              ? "bg-orange-500/20 text-orange-400"
                              : "bg-white/10 text-white/70"
                  }`}
                >
                  {EVENT_LABELS[log.type] ?? log.type}
                </span>
                <span className="min-w-0 flex-1 truncate text-white/80">
                  {log.summary || "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
