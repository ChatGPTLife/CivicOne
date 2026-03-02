// 2025-02-26
"use client";

import { useState } from "react";

import type { HexCell, IncidentType, SimulationConfig } from "@/types";

interface SimulationPanelProps {
  hexCells: HexCell[];
  onConfigSave: (config: SimulationConfig) => Promise<void>;
  onRun: (config: SimulationConfig) => Promise<void>;
  onReset: () => Promise<void>;
  loading: boolean;
}

const INCIDENT_TYPES: IncidentType[] = ["crime", "fire", "medical", "accident", "civic"];

export default function SimulationPanel({
  hexCells,
  onConfigSave,
  onRun,
  onReset,
  loading,
}: SimulationPanelProps) {
  const [expanded, setExpanded] = useState(true);
  const [hexId, setHexId] = useState<string>("");
  const [incidentType, setIncidentType] = useState<IncidentType>("crime");
  const [count, setCount] = useState<number>(10);
  const [timeWindow, setTimeWindow] = useState<number>(15);
  const [scenario, setScenario] = useState<SimulationConfig["scenario"]>("surge");

  const payload: SimulationConfig = {
    hex_id: hexId || undefined,
    incident_type: incidentType,
    count,
    time_window: timeWindow,
    scenario,
  };

  return (
    <section className="rounded-lg border border-white/10 bg-[#1a1d21]/80 p-3">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-center justify-between text-left"
      >
        <h2 className="text-xs font-semibold text-white">Simulation Engine</h2>
        <span className="text-white/60">{expanded ? "▼" : "▶"}</span>
      </button>
      <p className="mt-0.5 text-[10px] text-white/50">/api/simulation/config | /run | /reset</p>

      {expanded && (
      <div className="mt-2 grid gap-2">
        <label className="grid gap-1 text-[10px] text-white/70">
          Scenario
          <select
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
            value={scenario}
            onChange={(event) => setScenario(event.target.value as SimulationConfig["scenario"])}
          >
            <option value="surge">surge</option>
            <option value="congestion">congestion</option>
            <option value="vehicle_unavailability">vehicle_unavailability</option>
          </select>
        </label>

        <label className="grid gap-1 text-[10px] text-white/70">
          Hex ID (optional)
          <select
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
            value={hexId}
            onChange={(event) => setHexId(event.target.value)}
          >
            <option value="">Random across Chennai</option>
            {hexCells.slice(0, 500).map((cell) => (
              <option key={cell.hex_id} value={cell.hex_id}>
                {cell.hex_id}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1 text-[10px] text-white/70">
          Incident Type
          <select
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
            value={incidentType}
            onChange={(event) => setIncidentType(event.target.value as IncidentType)}
          >
            {INCIDENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[10px] text-white/70">
            Count
            <input
              className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
              type="number"
              min={1}
              max={200}
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
            />
          </label>
          <label className="grid gap-1 text-[10px] text-white/70">
            Time Window (min)
            <input
              className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
              type="number"
              min={1}
              max={120}
              value={timeWindow}
              onChange={(event) => setTimeWindow(Number(event.target.value))}
            />
          </label>
        </div>

        <div className="grid grid-cols-3 gap-1.5">
          <button
            type="button"
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-[10px] font-medium text-white hover:bg-white/10 disabled:opacity-50"
            disabled={loading}
            onClick={() => onConfigSave(payload)}
          >
            Save
          </button>
          <button
            type="button"
            className="rounded bg-amber-500 px-2 py-1.5 text-[10px] font-medium text-[#1a1d21] hover:bg-amber-400 disabled:opacity-50"
            disabled={loading}
            onClick={() => onRun(payload)}
          >
            Run
          </button>
          <button
            type="button"
            className="rounded border border-red-400/50 bg-red-500/20 px-2 py-1.5 text-[10px] font-medium text-red-300 hover:bg-red-500/30 disabled:opacity-50"
            disabled={loading}
            onClick={() => onReset()}
          >
            Reset
          </button>
        </div>
      </div>
      )}
    </section>
  );
}
