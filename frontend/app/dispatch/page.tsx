// 2025-02-26
"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchDispatches } from "@/lib/api";
import type { DispatchItem } from "@/lib/api";

const VEHICLE_ICONS: Record<string, string> = {
  police: "🚓",
  ambulance: "🚑",
  fire: "🚒",
  municipal: "🚚",
};

export default function DispatchPage() {
  const [dispatches, setDispatches] = useState<DispatchItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDispatches();
      setDispatches(data.dispatches);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#1a1d21]">
      <div className="border-b border-[#2d3238] px-4 py-3">
        <h1 className="text-lg font-semibold text-white">Active Dispatch</h1>
        <p className="text-sm text-white/60">Vehicles currently dispatched to incidents</p>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <p className="text-white/60">Loading…</p>
        ) : dispatches.length === 0 ? (
          <p className="text-white/60">No active dispatches.</p>
        ) : (
          <div className="space-y-4">
            {dispatches.map((d) => (
              <div
                key={d.incident.id}
                className="rounded-lg border border-[#2d3238] bg-[#252a31] p-4"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-[#2d3238] text-2xl">
                    {d.vehicle ? VEHICLE_ICONS[d.vehicle.type] ?? "🚗" : "🚗"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-white">
                      {d.vehicle?.type ?? "Unknown"} → {d.incident.type}
                    </div>
                    <p className="mt-1 text-sm text-white/70">
                      Incident: {d.incident.latitude.toFixed(5)}, {d.incident.longitude.toFixed(5)}
                    </p>
                    {d.vehicle && (
                      <p className="mt-1 text-sm text-white/60">
                        Vehicle: {d.vehicle.latitude.toFixed(5)}, {d.vehicle.longitude.toFixed(5)} ·{" "}
                        {d.vehicle.status}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-white/50">
                      {new Date(d.incident.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
