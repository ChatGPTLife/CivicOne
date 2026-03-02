// 2025-02-26
"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";

import { deployVehicles, deleteVehicle, fetchHexGrid, fetchTrafficSignals, fetchVehicles } from "@/lib/api";
import { buildHexLabelMap } from "@/lib/hexLabels";
import { getSocketClient } from "@/lib/socket";
import type { HexCell, Vehicle } from "@/types";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const VEHICLE_TYPES: Array<"police" | "ambulance" | "fire" | "municipal"> = [
  "police",
  "ambulance",
  "fire",
  "municipal",
];

export default function SimulationPage() {
  const [hexCells, setHexCells] = useState<HexCell[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [deployType, setDeployType] = useState<Vehicle["type"]>("police");
  const [deployHexId, setDeployHexId] = useState("");
  const [deployCount, setDeployCount] = useState(3);
  const [deploying, setDeploying] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [socketConnected, setSocketConnected] = useState(false);
  const [trafficSignals, setTrafficSignals] = useState<import("@/types").TrafficSignal[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [gridResult, vehiclesResult, signalsResult] = await Promise.allSettled([
        fetchHexGrid(),
        fetchVehicles(),
        fetchTrafficSignals(),
      ]);
      if (gridResult.status === "fulfilled") setHexCells(gridResult.value.cells);
      if (vehiclesResult.status === "fulfilled") setVehicles(vehiclesResult.value.vehicles);
      if (signalsResult.status === "fulfilled") setTrafficSignals(signalsResult.value.signals);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll traffic signal phases every second for the simulation view as well
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const data = await fetchTrafficSignals();
        if (!cancelled) {
          setTrafficSignals(data.signals);
        }
      } catch {
        // ignore
      }
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Listen for real-time vehicle position updates (from patrol simulator)
  useEffect(() => {
    const socket = getSocketClient();
    const onConnect = () => setSocketConnected(true);
    const onDisconnect = () => setSocketConnected(false);
    const onVehiclePosition = (event: { vehicle: Vehicle }) => {
      const v = event.vehicle;
      if (v) {
        setVehicles((prev) => {
          const idx = prev.findIndex((x) => x.id === v.id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = v;
            return next;
          }
          return [...prev, v];
        });
      }
    };
    const onVehicleRemoved = (event: { vehicle_id: string }) => {
      if (event.vehicle_id) {
        setVehicles((prev) => prev.filter((v) => v.id !== event.vehicle_id));
      }
    };
    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("vehicle_position", onVehiclePosition);
    socket.on("vehicle_removed", onVehicleRemoved);
    setSocketConnected(socket.connected);
    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("vehicle_position", onVehiclePosition);
      socket.off("vehicle_removed", onVehicleRemoved);
    };
  }, []);

  const handleDeploy = useCallback(async () => {
    setDeploying(true);
    try {
      await deployVehicles({
        type: deployType,
        hex_id: deployHexId || undefined,
        count: deployCount,
        status: "patrolling",
      });
      await loadData();
    } finally {
      setDeploying(false);
    }
  }, [deployType, deployHexId, deployCount, loadData]);

  const handleDelete = useCallback(
    async (vehicleId: string) => {
      setDeletingId(vehicleId);
      try {
        await deleteVehicle(vehicleId);
        setVehicles((prev) => prev.filter((v) => v.id !== vehicleId));
      } finally {
        setDeletingId(null);
      }
    },
    [],
  );

  const hexLabelById = buildHexLabelMap(hexCells);

  return (
    <div className="flex h-full flex-col md:flex-row">
      <div className="flex w-full flex-col border-b border-[#2d3238] bg-[#1e2228] p-5 md:w-80 md:border-b-0 md:border-r">
        <div className="rounded-lg border border-white/10 bg-[#252a31] p-4 shadow-sm">
          <h2 className="text-base font-semibold tracking-tight text-white">Deploy Emergency Vehicles</h2>
          <p className="mt-1.5 text-xs text-white/60 leading-relaxed">
            Deploy vehicles on the Chennai hex grid. Run the Python patrol simulator to move them.
          </p>

          <div className="mt-5 space-y-4">
          <label className="block text-xs font-medium text-white/80">
            Vehicle type
            <select
              value={deployType}
              onChange={(e) => setDeployType(e.target.value as Vehicle["type"])}
              className="mt-1.5 w-full rounded-md border border-white/20 bg-[#1a1d21] px-3 py-2.5 text-sm text-white outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30"
            >
              {VEHICLE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs font-medium text-white/80">
            Hex (optional – random if empty)
            <select
              value={deployHexId}
              onChange={(e) => setDeployHexId(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-white/20 bg-[#1a1d21] px-3 py-2.5 text-sm text-white outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30"
            >
              <option value="">Random in Chennai</option>
              {hexCells.slice(0, 400).map((c) => (
                <option key={c.hex_id} value={c.hex_id}>
                  {hexLabelById[c.hex_id] ?? "?"} — {c.hex_id}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-xs font-medium text-white/80">
            Count
            <input
              type="number"
              min={1}
              max={20}
              value={deployCount}
              onChange={(e) => setDeployCount(Number(e.target.value))}
              className="mt-1.5 w-full rounded-md border border-white/20 bg-[#1a1d21] px-3 py-2.5 text-sm text-white outline-none transition focus:border-amber-500 focus:ring-1 focus:ring-amber-500/30"
            />
          </label>

          <button
            type="button"
            disabled={deploying}
            onClick={handleDeploy}
            className="w-full rounded-md bg-amber-500 py-2.5 text-sm font-medium text-[#1a1d21] shadow-sm transition hover:bg-amber-400 disabled:opacity-50"
          >
            {deploying ? "Deploying…" : "Deploy vehicles"}
          </button>
        </div>
        </div>

        <div className="mt-5 rounded-lg border border-white/10 bg-[#252a31] p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white/70">Deployed vehicles ({vehicles.length})</h3>
          <div className="mt-2 max-h-48 space-y-1 overflow-auto rounded-md border border-white/10 bg-[#1a1d21] p-2.5 text-xs text-white/80">
            {vehicles.length === 0 ? (
              <p className="text-white/50">None. Deploy from above.</p>
            ) : (
              vehicles.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between gap-2 rounded border border-white/10 bg-[#252a31] px-2 py-1"
                >
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <span className="font-medium capitalize">{v.type}</span>
                    <span className="text-white/60">{v.status}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(v.id)}
                    disabled={deletingId === v.id}
                    className="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-red-400 hover:bg-red-500/20 disabled:opacity-50"
                    title="Remove vehicle"
                  >
                    {deletingId === v.id ? "…" : "✕"}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-5 rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
          <p className="text-sm font-semibold text-amber-200">Run patrol simulator to see movement</p>
          <p className="mt-2 text-xs text-white/70 leading-relaxed">
            In a terminal: <code className="rounded bg-black/30 px-1.5 py-0.5 font-mono text-[11px]">cd backend && python scripts/patrol_simulator.py</code>
          </p>
          <p className="mt-1.5 text-xs text-white/60">
            Vehicles move along roads (OSRM). Keep this page open to see them move.
          </p>
          <p className="mt-2.5 flex items-center gap-1.5 text-xs">
            {socketConnected ? (
              <span className="inline-flex items-center gap-1.5 text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Live updates connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-amber-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" /> Connecting…
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Right: Map */}
      <div className="relative flex-1">
        {loading ? (
          <div className="flex h-full items-center justify-center text-white/60">Loading map…</div>
        ) : (
          <MapView
            hexCells={hexCells}
            incidents={[]}
            vehicles={vehicles}
            routeGeometry={[]}
            greenCorridorHexes={[]}
            showHexGrid={true}
            trafficSignals={trafficSignals}
          />
        )}
      </div>
    </div>
  );
}
