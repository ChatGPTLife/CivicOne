// 2025-02-26
"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import IncidentForm from "@/components/IncidentForm";
import LiveFeedPanel from "@/components/LiveFeedPanel";
import SimulationPanel from "@/components/SimulationPanel";
import StatusBar from "@/components/StatusBar";
import { useRadio } from "@/components/RadioProvider";
import {
  fetchActiveDispatches,
  fetchHexGrid,
  fetchIncidents,
  fetchPatrolAlerts,
  fetchTrafficSignals,
  fetchVehicles,
  postIncident,
  resetSimulation,
  runSimulation,
  updateSimulationConfig,
} from "@/lib/api";
import { disconnectSocket, getSocketClient } from "@/lib/socket";
import type {
  DispatchPayload,
  HexCell,
  Incident,
  PatrolAlert,
  SimulationConfig,
  SimulationResult,
  Vehicle,
} from "@/types";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

const DEFAULT_INCIDENT_POINT = { latitude: 13.04, longitude: 80.24 };

export default function Home() {
  const [hexCells, setHexCells] = useState<HexCell[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [alerts, setAlerts] = useState<PatrolAlert[]>([]);
  const [vehiclesById, setVehiclesById] = useState<Record<string, Vehicle>>({});
  const [routeGeometry, setRouteGeometry] = useState<[number, number][]>([]);
  const [allDispatchRoutes, setAllDispatchRoutes] = useState<
    Array<{ incidentId: string; vehicleId: string; geometry: [number, number][] }>
  >([]);
  const [greenCorridorHexes, setGreenCorridorHexes] = useState<string[]>([]);
  const [lastDispatch, setLastDispatch] = useState<DispatchPayload | null>(null);
  const [lastSimulation, setLastSimulation] = useState<SimulationResult | null>(null);
  const [showHexGrid, setShowHexGrid] = useState(true);
  const [socketConnected, setSocketConnected] = useState(false);
  const [submittingIncident, setSubmittingIncident] = useState(false);
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [loadingGrid, setLoadingGrid] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [trafficSignals, setTrafficSignals] = useState<import("@/types").TrafficSignal[]>([]);

  const { radioEnabled, playIncidentRadio } = useRadio();

  const vehicles = useMemo(() => {
    const byId = new Map<string, Vehicle>();
    for (const v of Object.values(vehiclesById)) {
      byId.set(String(v.id), v);
    }
    return Array.from(byId.values());
  }, [vehiclesById]);

  const liveIncidents = useMemo(
    () => incidents.filter((i) => !i.attended),
    [incidents],
  );

  const dispatchRoutes = useMemo(() => {
    const routes: [number, number][][] = [];
    for (const inc of liveIncidents) {
      if (inc.assigned_vehicle_id) {
        const v = vehiclesById[inc.assigned_vehicle_id];
        if (v) {
          routes.push([
            [v.latitude, v.longitude],
            [inc.latitude, inc.longitude],
          ]);
        }
      }
    }
    return routes;
  }, [liveIncidents, vehiclesById]);

  const refreshGrid = useCallback(async () => {
    setLoadingGrid(true);
    try {
      const data = await fetchHexGrid();
      setHexCells(data.cells);
    } finally {
      setLoadingGrid(false);
    }
  }, []);

  useEffect(() => {
    async function bootstrap() {
      // Load hex grid, alerts, and vehicles independently so one failure (e.g. network)
      // doesn't block the hex grid from showing
      const results = await Promise.allSettled([
        refreshGrid(),
        fetchPatrolAlerts().then((data) => setAlerts(data.alerts)),
        fetchVehicles().then((data) => {
          const byId: Record<string, Vehicle> = {};
          data.vehicles.forEach((v) => {
            byId[v.id] = v;
          });
          setVehiclesById(byId);
        }),
        fetchTrafficSignals().then((data) => setTrafficSignals(data.signals)),
        fetchIncidents().then((data) => {
          const mapped: Incident[] = data.incidents.map((i) => ({
            id: i.id,
            type: i.type as Incident["type"],
            latitude: i.latitude,
            longitude: i.longitude,
            hex_id: i.hex_id ?? "",
            assigned_vehicle_id: i.assigned_vehicle_id,
            status: i.status,
            attended: i.attended,
            created_at: i.created_at,
          }));
          setIncidents(mapped);
        }),
        fetchActiveDispatches(),
      ]);
      // If hex grid failed (e.g. backend down), try once more so grid shows when backend is up
      if (results[0].status === "rejected") {
        try {
          await refreshGrid();
        } catch {
          // ignore
        }
      }

      // Restore all active dispatch routes (so they persist across refresh)
      const dispatchResult = results[5];
      if (dispatchResult.status === "fulfilled" && dispatchResult.value.dispatches.length > 0) {
        const dispatches = dispatchResult.value.dispatches;
        const active = dispatches[0];
        setLastDispatch(active);
        const routes: Array<{ incidentId: string; vehicleId: string; geometry: [number, number][] }> = [];
        for (const d of dispatches) {
          if (d.vehicle && d.route?.geometry && d.route.geometry.length >= 2) {
            routes.push({
              incidentId: d.incident_id,
              vehicleId: String(d.vehicle.id),
              geometry: d.route.geometry,
            });
            setVehiclesById((prev) => ({ ...prev, [d.vehicle!.id]: d.vehicle! }));
          }
        }
        setAllDispatchRoutes(routes);
        if (active.route?.geometry) {
          setRouteGeometry(active.route.geometry);
          setGreenCorridorHexes(active.green_corridor_hexes ?? []);
        }
      }
    }

    bootstrap();
  }, [refreshGrid]);

  // Poll traffic signal phases every second so colors stay in sync with backend time
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const data = await fetchTrafficSignals();
        if (!cancelled) {
          setTrafficSignals(data.signals);
        }
      } catch {
        // ignore errors; next tick will try again
      }
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const socket = getSocketClient();

    const onConnect = () => setSocketConnected(true);
    const onDisconnect = () => setSocketConnected(false);

    const onNewIncident = (event: Incident) => {
      setIncidents((previous) => {
        const existing = previous.find((i) => i.id === event.id);
        if (existing) return previous;
        return [{ ...event, attended: false }, ...previous];
      });
      setHexCells((previous) =>
        previous.map((cell) =>
          cell.hex_id === event.hex_id
            ? { ...cell, incident_count: cell.incident_count + 1 }
            : cell,
        ),
      );
    };

    const onVehicleDispatched = (event: DispatchPayload) => {
      setLastDispatch(event);
      const vehicle = event.vehicle;
      if (vehicle) {
        setVehiclesById((previous) => ({ ...previous, [vehicle.id]: vehicle }));
      }
      if (event.incident_id && vehicle) {
        let incidentForRadio: Incident | null = null;
        setIncidents((prev) =>
          prev.map((i) => {
            if (i.id === event.incident_id) {
              const updated = { ...i, assigned_vehicle_id: vehicle.id };
              incidentForRadio = updated;
              return updated;
            }
            return i;
          }),
        );
        // Radio playback handled by RadioProvider via radio_comm socket events
      }
      if (event.route?.geometry) {
        setRouteGeometry(event.route.geometry);
        setAllDispatchRoutes((prev) => {
          const next = prev.filter((r) => r.incidentId !== event.incident_id);
          next.push({
            incidentId: event.incident_id,
            vehicleId: String(vehicle?.id ?? ""),
            geometry: event.route!.geometry,
          });
          return next;
        });
      }
      setGreenCorridorHexes(event.green_corridor_hexes ?? []);
    };

    const onRouteUpdate = (event: {
      route: { geometry: [number, number][] };
      green_corridor_hexes: string[];
    }) => {
      setRouteGeometry(event.route.geometry ?? []);
      setGreenCorridorHexes(event.green_corridor_hexes ?? []);
    };

    const onPatrolAlert = (event: PatrolAlert) => {
      setAlerts((previous) => [event, ...previous]);
    };

    const onSimulationUpdate = (event: SimulationResult) => {
      setLastSimulation(event);
      if (event.incidents?.length) {
        setIncidents((previous) => [
          ...event.incidents!.map((item) => ({
            id: item.id,
            type: item.type,
            latitude: item.latitude,
            longitude: item.longitude,
            hex_id: item.hex_id,
            status: item.dispatch.vehicle ? "assigned" : "new",
            assigned_vehicle_id: item.dispatch.vehicle?.id,
            created_at: new Date().toISOString(),
          })),
          ...previous,
        ]);
      }
    };

    const onVehiclePosition = (event: { vehicle: Vehicle }) => {
      const v = event.vehicle;
      if (v) setVehiclesById((prev) => ({ ...prev, [v.id]: v }));
    };

    const onVehicleRemoved = (event: { vehicle_id: string }) => {
      if (event.vehicle_id) {
        setVehiclesById((prev) => {
          const next = { ...prev };
          delete next[event.vehicle_id];
          return next;
        });
      }
    };

    const onIncidentAttended = (event: { incident_id: string }) => {
      setIncidents((prev) =>
        prev.map((i) =>
          i.id === event.incident_id ? { ...i, attended: true, status: "attended" } : i,
        ),
      );
      setAllDispatchRoutes((prev) => prev.filter((r) => r.incidentId !== event.incident_id));
    };

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("new_incident", onNewIncident);
    socket.on("vehicle_dispatched", onVehicleDispatched);
    socket.on("route_update", onRouteUpdate);
    socket.on("patrol_alert", onPatrolAlert);
    socket.on("simulation_update", onSimulationUpdate);
    socket.on("vehicle_position", onVehiclePosition);
    socket.on("vehicle_removed", onVehicleRemoved);
    socket.on("incident_attended", onIncidentAttended);

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("new_incident", onNewIncident);
      socket.off("vehicle_dispatched", onVehicleDispatched);
      socket.off("route_update", onRouteUpdate);
      socket.off("patrol_alert", onPatrolAlert);
      socket.off("simulation_update", onSimulationUpdate);
      socket.off("vehicle_position", onVehiclePosition);
      socket.off("vehicle_removed", onVehicleRemoved);
      socket.off("incident_attended", onIncidentAttended);
      disconnectSocket();
    };
  }, []);

  const handleIncidentSubmit = useCallback(
    async (payload: { type: Incident["type"]; latitude: number; longitude: number }) => {
      setSubmittingIncident(true);
      try {
        const data = await postIncident(payload);
        setIncidents((previous) => [data.incident, ...previous]);
        setLastDispatch(data.dispatch);
        setAlerts((previous) => [...data.alerts, ...previous]);
        const vehicle = data.dispatch.vehicle;
        if (vehicle) {
          setVehiclesById((previous) => ({ ...previous, [vehicle.id]: vehicle }));
        }
        const dispatchedVehicle = data.dispatch.vehicle;
        const routeGeom = data.dispatch.route?.geometry;
        if (routeGeom && dispatchedVehicle) {
          setRouteGeometry(routeGeom);
          setAllDispatchRoutes((prev) => {
            const next = prev.filter((r) => r.incidentId !== data.incident.id);
            next.push({
              incidentId: data.incident.id,
              vehicleId: String(dispatchedVehicle.id),
              geometry: routeGeom,
            });
            return next;
          });
          setGreenCorridorHexes(data.dispatch.green_corridor_hexes ?? []);
        }
        if (radioEnabled) {
          void playIncidentRadio();
        }
        await refreshGrid();
      } finally {
        setSubmittingIncident(false);
      }
    },
    [refreshGrid, radioEnabled, playIncidentRadio],
  );

  const handleSimulationConfigSave = useCallback(async (config: SimulationConfig) => {
    setSimulationBusy(true);
    try {
      await updateSimulationConfig(config);
    } finally {
      setSimulationBusy(false);
    }
  }, []);

  const handleSimulationRun = useCallback(
    async (config: SimulationConfig) => {
      setSimulationBusy(true);
      try {
        const result = await runSimulation(config);
        setLastSimulation(result);
        await refreshGrid();
      } finally {
        setSimulationBusy(false);
      }
    },
    [refreshGrid],
  );

  const handleSimulationReset = useCallback(async () => {
    setSimulationBusy(true);
    try {
      await resetSimulation();
      setIncidents([]);
      setVehiclesById({});
      setRouteGeometry([]);
      setAllDispatchRoutes([]);
      setGreenCorridorHexes([]);
      setLastSimulation(null);
      setLastDispatch(null);
      await refreshGrid();
    } finally {
      setSimulationBusy(false);
    }
  }, [refreshGrid]);

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Left sidebar: simulation, incident, status, feed */}
      <div
        className={`flex shrink-0 flex-col overflow-hidden bg-[#252a31] transition-all duration-200 ${
          panelOpen ? "w-[300px] border-r border-[#2d3238]" : "w-0"
        }`}
      >
        {panelOpen && (
          <div className="flex h-full w-[300px] flex-col overflow-y-auto p-3">
            <StatusBar
              hexCount={hexCells.length}
              incidentCount={incidents.length}
              vehicleCount={vehicles.length}
              connected={socketConnected}
              greenCorridorActive={greenCorridorHexes.length > 0}
            />
            <div className="mt-3 space-y-3">
              <IncidentForm
                defaultLat={DEFAULT_INCIDENT_POINT.latitude}
                defaultLng={DEFAULT_INCIDENT_POINT.longitude}
                onSubmit={handleIncidentSubmit}
                isSubmitting={submittingIncident}
              />
              <SimulationPanel
                hexCells={hexCells}
                onConfigSave={handleSimulationConfigSave}
                onRun={handleSimulationRun}
                onReset={handleSimulationReset}
                loading={simulationBusy}
              />
              <LiveFeedPanel
                incidents={incidents}
                alerts={alerts}
                lastDispatch={lastDispatch}
                lastSimulation={lastSimulation}
              />
            </div>
          </div>
        )}
      </div>

      {/* Map area */}
      <div className="relative flex-1 min-w-0">
        <MapView
          hexCells={hexCells}
          incidents={liveIncidents}
          vehicles={vehicles}
          routeGeometry={routeGeometry}
          routeVehicleId={lastDispatch?.vehicle?.id ?? null}
          allDispatchRoutes={allDispatchRoutes}
          greenCorridorHexes={greenCorridorHexes}
          showHexGrid={showHexGrid}
          trafficSignals={trafficSignals}
        />

        {/* Map toolbar: panel toggle, hex toggle, refresh - top-right, above zoom */}
        <div className="absolute right-3 top-3 z-[1000] flex flex-wrap items-center gap-2 rounded-lg border border-[#2d3238] bg-[#252a31] px-2 py-2 shadow-lg">
          <button
            type="button"
            onClick={() => setPanelOpen((o) => !o)}
            className="rounded border border-white/20 bg-[#1a1d21] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#2d3238]"
            title={panelOpen ? "Hide panel" : "Show panel"}
          >
            {panelOpen ? "◀ Panel" : "▶ Panel"}
          </button>
          <button
            type="button"
            onClick={() => setShowHexGrid((v) => !v)}
            className="rounded border border-white/20 bg-[#1a1d21] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#2d3238]"
            title={showHexGrid ? "Hide hex grid" : "Show hex grid"}
          >
            {showHexGrid ? "Hide hex" : "Show hex"}
          </button>
          <button
            type="button"
            onClick={() => refreshGrid()}
            className="rounded border border-white/20 bg-[#1a1d21] px-3 py-1.5 text-xs font-medium text-white hover:bg-[#2d3238] disabled:opacity-50"
            title="Refresh hex grid"
            disabled={loadingGrid}
          >
            {loadingGrid ? "Refreshing…" : "Refresh hex"}
          </button>
        </div>
      </div>
    </div>
  );
}
