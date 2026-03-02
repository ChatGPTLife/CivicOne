// 2025-02-26
export type IncidentType = "crime" | "fire" | "medical" | "accident" | "civic";

export interface Incident {
  id: string;
  type: IncidentType;
  latitude: number;
  longitude: number;
  hex_id: string;
  assigned_vehicle_id?: string | null;
  status: string;
  attended?: boolean;
  created_at: string;
}

export interface Vehicle {
  id: string;
  type: "police" | "ambulance" | "fire" | "municipal";
  latitude: number;
  longitude: number;
  status: "available" | "busy" | "patrolling" | string;
  current_hex_id?: string | null;
}

export interface HexCell {
  hex_id: string;
  polygon: number[][];
  center: [number, number];
  incident_count: number;
  patrol_priority_score: number;
}

export type SignalPhase = "GREEN" | "YELLOW" | "RED";

export interface TrafficSignal {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  phase: SignalPhase;
}

export interface PatrolAlert {
  id: string;
  hex_id: string;
  alert_type: string;
  message: string;
  created_at: string;
}

export interface RoutePayload {
  distance_m: number | null;
  duration_s: number | null;
  geometry: [number, number][];
  source: "osrm" | "fallback";
}

export interface DispatchPayload {
  incident_id: string;
  vehicle: Vehicle | null;
  route?: RoutePayload;
  green_corridor_hexes?: string[];
  message?: string;
}

export interface SimulationConfig {
  hex_id?: string;
  incident_type?: IncidentType;
  count?: number;
  time_window?: number;
  scenario?: "surge" | "congestion" | "vehicle_unavailability";
}

export interface SimulationResult {
  scenario: string;
  count?: number;
  message?: string;
  incidents?: Array<{
    id: string;
    type: IncidentType;
    latitude: number;
    longitude: number;
    hex_id: string;
    dispatch: DispatchPayload;
  }>;
}
