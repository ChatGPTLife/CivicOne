// 2025-02-26
import axios from "axios";

import type {
  DispatchPayload,
  HexCell,
  Incident,
  PatrolAlert,
  SimulationConfig,
  SimulationResult,
  TrafficSignal,
} from "@/types";

const apiBaseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

export async function fetchHexGrid() {
  const { data } = await api.get<{ resolution: number; inserted: number; cells: HexCell[] }>("/api/hex-grid");
  return data;
}

export interface HexIncidentSummary {
  hex_id: string;
  polygon: number[][];
  center: [number, number];
  incident_count: number;
  patrol_priority_score: number;
  incident_types: Record<string, number>;
}

export async function fetchHexIncidentsSummary() {
  const { data } = await api.get<{ cells: HexIncidentSummary[] }>("/api/hex-grid/incidents-summary");
  return data;
}

export async function postIncident(payload: {
  type: Incident["type"];
  latitude: number;
  longitude: number;
}) {
  const { data } = await api.post<{
    incident: Incident;
    dispatch: DispatchPayload;
    alerts: PatrolAlert[];
  }>("/api/incidents", payload);
  return data;
}

export async function fetchPatrolAlerts() {
  const { data } = await api.get<{ alerts: PatrolAlert[] }>("/api/patrol-alerts");
  return data;
}

export async function updateSimulationConfig(payload: SimulationConfig) {
  const { data } = await api.post<{ config: SimulationConfig }>("/api/simulation/config", payload);
  return data;
}

export async function runSimulation(payload: SimulationConfig) {
  const { data } = await api.post<SimulationResult>("/api/simulation/run", payload);
  return data;
}

export async function resetSimulation() {
  const { data } = await api.post<{ status: string }>("/api/simulation/reset", {});
  return data;
}

export async function fetchVehicles() {
  const { data } = await api.get<{ vehicles: import("@/types").Vehicle[] }>("/api/vehicles");
  return data;
}

export async function deployVehicles(payload: {
  type: "police" | "ambulance" | "fire" | "municipal";
  hex_id?: string;
  latitude?: number;
  longitude?: number;
  count?: number;
  status?: string;
}) {
  const { data } = await api.post<{
    deployed: number;
    vehicles: import("@/types").Vehicle[];
  }>("/api/vehicles/deploy", payload);
  return data;
}

export async function deleteVehicle(vehicleId: string) {
  const { data } = await api.delete<{ ok: boolean; deleted: string }>(
    `/api/vehicles/${vehicleId}`,
  );
  return data;
}

export async function fetchTrafficSignals() {
  const { data } = await api.get<{ signals: TrafficSignal[] }>("/api/traffic-signals");
  return data;
}

export interface IncidentListItem {
  id: string;
  type: string;
  latitude: number;
  longitude: number;
  hex_id: string | null;
  assigned_vehicle_id: string | null;
  status: string;
  attended: boolean;
  report_id: string | null;
  photo_url: string | null;
  video_url: string | null;
  voice_url: string | null;
  source: string;
  created_at: string;
}

export async function fetchIncidents() {
  const { data } = await api.get<{ incidents: IncidentListItem[] }>("/api/incidents");
  return data;
}

export async function markIncidentAttended(incidentId: string) {
  const { data } = await api.patch<{ ok: boolean }>(`/api/incidents/${incidentId}/attended`);
  return data;
}

export interface DispatchItem {
  incident: IncidentListItem;
  vehicle: import("@/types").Vehicle | null;
  route?: { geometry: [number, number][]; distance_m?: number; duration_s?: number };
}

export async function fetchActiveDispatches() {
  const { data } = await api.get<{ dispatches: DispatchPayload[] }>("/api/dispatches/active");
  return data;
}

export async function fetchDispatches(): Promise<{ dispatches: DispatchItem[] }> {
  const [incRes, vehRes] = await Promise.all([
    api.get<{ incidents: IncidentListItem[] }>("/api/incidents"),
    api.get<{ vehicles: import("@/types").Vehicle[] }>("/api/vehicles"),
  ]);
  const incidents = incRes.data.incidents;
  const vehicles = vehRes.data.vehicles;
  const active = incidents.filter(
    (i) => !i.attended && i.assigned_vehicle_id && ["assigned", "dispatched", "new"].includes(i.status),
  );
  const byId = Object.fromEntries(vehicles.map((v) => [v.id, v]));
  const dispatches: DispatchItem[] = active.map((inc) => ({
    incident: inc,
    vehicle: inc.assigned_vehicle_id ? byId[inc.assigned_vehicle_id] ?? null : null,
  }));
  return { dispatches };
}
