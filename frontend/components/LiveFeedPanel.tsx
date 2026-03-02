// 2025-02-26
"use client";

import type { DispatchPayload, Incident, PatrolAlert, SimulationResult } from "@/types";

interface LiveFeedPanelProps {
  incidents: Incident[];
  alerts: PatrolAlert[];
  lastDispatch: DispatchPayload | null;
  lastSimulation: SimulationResult | null;
}

export default function LiveFeedPanel({
  incidents,
  alerts,
  lastDispatch,
  lastSimulation,
}: LiveFeedPanelProps) {
  return (
    <section className="rounded-lg border border-white/10 bg-[#1a1d21]/80 p-3">
      <h2 className="text-xs font-semibold text-white">Live Operations Feed</h2>

      <div className="mt-2 space-y-3 text-[10px]">
        <div>
          <p className="font-medium text-white/80">Latest Dispatch</p>
          {lastDispatch ? (
            <div className="mt-1 rounded border border-white/10 bg-[#252a31] p-2 text-white/90">
              <p>Incident: {lastDispatch.incident_id}</p>
              <p>Vehicle: {lastDispatch.vehicle?.id ?? "none"}</p>
              <p>Green corridor hexes: {lastDispatch.green_corridor_hexes?.length ?? 0}</p>
            </div>
          ) : (
            <p className="mt-1 text-white/50">No dispatch events yet.</p>
          )}
        </div>

        <div>
          <p className="font-medium text-white/80">Patrol Alerts ({alerts.length})</p>
          <div className="mt-1 max-h-28 space-y-1 overflow-auto rounded border border-white/10 p-2">
            {alerts.length === 0 ? (
              <p className="text-white/50">No alerts yet.</p>
            ) : (
              alerts.slice(0, 8).map((alert, idx) => (
                <div key={`${alert.id}-${alert.hex_id}-${idx}`} className="rounded border border-white/10 bg-[#252a31] p-1.5 text-white/90">
                  <p className="font-medium">{alert.alert_type}</p>
                  <p className="text-white/70">{alert.message}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div>
          <p className="font-medium text-white/80">Recent Incidents ({incidents.length})</p>
          <div className="mt-1 max-h-36 space-y-1 overflow-auto rounded border border-white/10 p-2">
            {incidents.length === 0 ? (
              <p className="text-white/50">No incidents yet.</p>
            ) : (
              incidents.slice(0, 10).map((incident) => (
                <div key={incident.id} className="rounded border border-white/10 bg-[#252a31] p-1.5 text-white/90">
                  <p className="font-medium">{incident.type.toUpperCase()}</p>
                  <p className="text-white/70">Hex: {incident.hex_id} · {incident.status}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div>
          <p className="font-medium text-white/80">Last Simulation</p>
          {lastSimulation ? (
            <div className="mt-1 rounded border border-white/10 bg-[#252a31] p-2 text-white/90">
              <p>Scenario: {lastSimulation.scenario} · Count: {lastSimulation.count ?? 0}</p>
              {lastSimulation.message ? <p>{lastSimulation.message}</p> : null}
            </div>
          ) : (
            <p className="mt-1 text-white/50">No simulation run yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}
