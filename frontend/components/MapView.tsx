// 2025-02-26
"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useMemo, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  TileLayer,
  Tooltip,
  ZoomControl,
} from "react-leaflet";

import type { HexCell, Incident, TrafficSignal, Vehicle } from "@/types";
import { useInterpolatedPosition } from "@/hooks/useInterpolatedPosition";
import { buildHexLabelMap } from "@/lib/hexLabels";

function SmoothVehicleMarker({ v, icon }: { v: Vehicle; icon: L.Icon | L.DivIcon }) {
  const [lat, lng] = useInterpolatedPosition(v.latitude, v.longitude);
  const label =
    v.type === "police"
      ? "Pink Patrol (police)"
      : v.type === "ambulance"
        ? "Ambulance"
        : v.type === "fire"
          ? "Fire Service"
          : "Municipal";
  return (
    <Marker key={`vehicle-${String(v.id)}`} position={[lat, lng]} icon={icon}>
      <Tooltip direction="top" offset={[0, -10]} className="vehicle-tooltip">
        <div className="font-semibold">{label}</div>
        <div>Status: {v.status}</div>
        <div className="text-white/70">ID: {String(v.id).slice(0, 8)}…</div>
      </Tooltip>
    </Marker>
  );
}

interface MapViewProps {
  hexCells: HexCell[];
  incidents: Incident[];
  vehicles: Vehicle[];
  routeGeometry: [number, number][];
  routeVehicleId?: string | null;
  allDispatchRoutes?: Array<{ incidentId: string; vehicleId: string; geometry: [number, number][] }>;
  greenCorridorHexes: string[];
  showHexGrid: boolean;
  trafficSignals?: TrafficSignal[];
}

const CHENNAI_CENTER: [number, number] = [13.0827, 80.2707];
// Chennai bounds: [south, west], [north, east] – restricts pan/zoom to city only
const CHENNAI_BOUNDS: [[number, number], [number, number]] = [
  [12.7, 79.9],
  [13.3, 80.4],
];

// Chennai hospitals (matches backend + additional major hospitals)
const CHENNAI_HOSPITALS: { id: string; name: string; lat: number; lng: number }[] = [
  { id: "H1", name: "Rajiv Gandhi Govt Hospital", lat: 13.0826, lng: 80.275 },
  { id: "H2", name: "Stanley Medical College", lat: 13.1009, lng: 80.2937 },
  { id: "H3", name: "Govt General Hospital", lat: 13.0809, lng: 80.2668 },
  { id: "H4", name: "Apollo Hospitals Greams Rd", lat: 13.0658, lng: 80.2585 },
  { id: "H5", name: "MIOT International", lat: 13.0288, lng: 80.2078 },
  { id: "H6", name: "Fortis Malar", lat: 13.0128, lng: 80.2578 },
  { id: "H7", name: "OMR Private Hospital", lat: 12.9684, lng: 80.2414 },
];

// Set NEXT_PUBLIC_USE_OFFLINE_TILES=true and add tiles to public/tiles/{z}/{x}/{y}.png for offline use
const USE_OFFLINE_TILES =
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_USE_OFFLINE_TILES === "true";

const policeIcon = L.icon({
  iconUrl: "/police_patrolcar.png",
  iconSize: [64, 32],
  iconAnchor: [32, 16],
  tooltipAnchor: [0, -20],
});

const ambulanceIcon = L.icon({
  iconUrl: "/ambulance.png",
  iconSize: [72, 32],
  iconAnchor: [36, 16],
  tooltipAnchor: [0, -20],
});

const fireIcon = L.icon({
  iconUrl: "/fire_truck.png",
  iconSize: [80, 32],
  iconAnchor: [40, 16],
  tooltipAnchor: [0, -20],
});

const municipalIcon = L.divIcon({
  html: `<span style="font-size:24px;line-height:1">🚜</span>`,
  className: "vehicle-marker",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const defaultIcon = L.divIcon({
  html: `<span style="font-size:24px;line-height:1">🚗</span>`,
  className: "vehicle-marker",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

function getVehicleIcon(type: Vehicle["type"]) {
  switch (type) {
    case "police":
      return policeIcon;
    case "ambulance":
      return ambulanceIcon;
    case "fire":
      return fireIcon;
    case "municipal":
      return municipalIcon;
    default:
      return defaultIcon;
  }
}

function HexGridLayer({
  hexCells,
  hexLabelById,
  greenCorridorHexes,
  showHexGrid,
}: {
  hexCells: HexCell[];
  hexLabelById: Record<string, string>;
  greenCorridorHexes: string[];
  showHexGrid: boolean;
}) {
  if (!showHexGrid) return null;

  return (
    <>
      {hexCells.map((cell) => {
        const isCorridor = greenCorridorHexes.includes(cell.hex_id);
        const count = cell.incident_count ?? 0;
        const label = hexLabelById[cell.hex_id] ?? "?";
        const priority = cell.patrol_priority_score ?? 0;

        // Green corridor: cyan-teal border, subtle fill
        // High incident count: warmer fill (amber tint)
        // Default: cool grey border, very subtle fill
        const strokeColor = isCorridor
          ? "#0d9488"
          : count >= 3
            ? "#f59e0b"
            : "#475569";
        const fillOpacity = isCorridor
          ? 0.12
          : count >= 5
            ? 0.14
            : count >= 2
              ? 0.1
              : 0.05;
        const fillColor = isCorridor ? "#0d9488" : count >= 3 ? "#f59e0b" : "#334155";

        const positions = (cell.polygon || []).map(([lat, lng]) => [lat, lng] as [number, number]);
        if (positions.length < 3) return null;

        return (
          <Polygon
            key={cell.hex_id}
            positions={positions}
            pathOptions={{
              color: strokeColor,
              weight: isCorridor ? 2.2 : count >= 2 ? 1.8 : 1.2,
              opacity: isCorridor ? 0.95 : 0.75,
              fillColor,
              fillOpacity,
              dashArray: isCorridor ? undefined : "2,4",
            }}
            eventHandlers={{}}
          >
            <Tooltip direction="top" offset={[0, -8]} className="hex-tooltip">
              <div className="font-semibold text-amber-400">Hex {label}</div>
              <div className="text-white/80">ID: {cell.hex_id.slice(0, 12)}…</div>
              <div>Incidents: {count}</div>
              {priority > 0 && <div className="text-amber-400/90">Priority: {priority.toFixed(1)}</div>}
            </Tooltip>
          </Polygon>
        );
      })}
    </>
  );
}

function MapContent({
  hexCells,
  incidents,
  vehicles,
  routedPath,
  allRoutedPaths,
  greenCorridorHexes,
  showHexGrid,
  trafficSignals,
  hexLabelById,
}: {
  hexCells: HexCell[];
  incidents: Incident[];
  vehicles: Vehicle[];
  routedPath: [number, number][];
  allRoutedPaths: Array<{ key: string; path: [number, number][] }>;
  greenCorridorHexes: string[];
  showHexGrid: boolean;
  trafficSignals: TrafficSignal[];
  hexLabelById: Record<string, string>;
}) {
  return (
    <>
      <HexGridLayer
        hexCells={hexCells}
        hexLabelById={hexLabelById}
        greenCorridorHexes={greenCorridorHexes}
        showHexGrid={showHexGrid}
      />

      {incidents.map((inc) => (
        <CircleMarker
          key={inc.id}
          center={[inc.latitude, inc.longitude]}
          radius={5}
          pathOptions={{
            color: "#dc2626",
            fillColor: "#dc2626",
            fillOpacity: 1,
            weight: 2,
          }}
        >
          <Tooltip direction="top" offset={[0, -6]} className="incident-tooltip">
            <div className="font-semibold">Incident</div>
            <div>Type: {inc.type}</div>
            <div>Status: {inc.status}</div>
          </Tooltip>
        </CircleMarker>
      ))}

      {vehicles.map((v) => (
        <SmoothVehicleMarker key={String(v.id)} v={v} icon={getVehicleIcon(v.type)} />
      ))}

      {trafficSignals.map((s) => {
        const r = s.phase === "RED" ? "#dc2626" : "#4b5563";
        const y = s.phase === "YELLOW" ? "#facc15" : "#4b5563";
        const g = s.phase === "GREEN" ? "#22c55e" : "#4b5563";
        const icon = L.divIcon({
          html: `
            <div class="traffic-signal-marker" style="
              width:14px;height:24px;background:#1f2937;border-radius:4px;
              border:1px solid #374151;display:flex;flex-direction:column;
              align-items:center;justify-content:space-around;padding:2px;
            ">
              <div style="width:8px;height:6px;border-radius:50%;background:${r};box-shadow:0 0 4px ${r}"></div>
              <div style="width:8px;height:6px;border-radius:50%;background:${y};box-shadow:0 0 4px ${y}"></div>
              <div style="width:8px;height:6px;border-radius:50%;background:${g};box-shadow:0 0 4px ${g}"></div>
            </div>
          `,
          className: "traffic-signal-icon",
          iconSize: [14, 24],
          iconAnchor: [7, 12],
        });
        return (
          <Marker key={s.id} position={[s.latitude, s.longitude]} icon={icon}>
            <Tooltip direction="top" offset={[0, -12]} className="incident-tooltip">
              <div className="font-semibold">🚦 {s.name}</div>
              <div>Phase: <span style={s.phase === "GREEN" ? { color: "#22c55e" } : s.phase === "YELLOW" ? { color: "#facc15" } : { color: "#dc2626" }}>{s.phase}</span></div>
            </Tooltip>
          </Marker>
        );
      })}

      {CHENNAI_HOSPITALS.map((h) => {
        const icon = L.divIcon({
          html: `<span style="font-size:20px;line-height:1">🏥</span>`,
          className: "hospital-marker",
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        });
        return (
          <Marker key={h.id} position={[h.lat, h.lng]} icon={icon}>
            <Tooltip direction="top" offset={[0, -10]}>
              {h.name}
            </Tooltip>
          </Marker>
        );
      })}

      {routedPath.length > 1 && (
        <Polyline
          positions={routedPath}
          pathOptions={{
            color: "#22d3ee",
            weight: 5,
            opacity: 0.95,
          }}
        />
      )}
      {allRoutedPaths.map(({ key, path }) => (
        <Polyline
          key={key}
          positions={path}
          pathOptions={{
            color: "#22d3ee",
            weight: 4,
            opacity: 0.9,
          }}
        />
      ))}
    </>
  );
}

function trimRouteFromVehicle(
  geometry: [number, number][],
  vehicle: { latitude: number; longitude: number } | undefined,
): [number, number][] {
  if (!geometry || geometry.length < 2 || !vehicle) return geometry;
  let bestIndex = 0;
  let bestD2 = Number.POSITIVE_INFINITY;
  geometry.forEach(([lat, lng], idx) => {
    const dx = lat - vehicle.latitude;
    const dy = lng - vehicle.longitude;
    const d2 = dx * dx + dy * dy;
    if (d2 < bestD2) {
      bestD2 = d2;
      bestIndex = idx;
    }
  });
  return geometry.slice(bestIndex);
}

export default function MapView({
  hexCells,
  incidents,
  vehicles,
  routeGeometry,
  routeVehicleId,
  allDispatchRoutes = [],
  greenCorridorHexes,
  showHexGrid,
  trafficSignals = [],
}: MapViewProps) {
  const hexLabelById = buildHexLabelMap(hexCells);

  const routedPath = useMemo(() => {
    if (routeGeometry.length < 2 || !routeVehicleId) return routeGeometry;
    const v = vehicles.find((veh) => String(veh.id) === String(routeVehicleId));
    return trimRouteFromVehicle(routeGeometry, v);
  }, [routeGeometry, routeVehicleId, vehicles]);

  const allRoutedPaths = useMemo(() => {
    const seen = new Set<string>();
    return allDispatchRoutes
      .filter((r) => String(r.vehicleId) !== String(routeVehicleId))
      .map((r) => {
        const v = vehicles.find((veh) => String(veh.id) === String(r.vehicleId));
        const path = trimRouteFromVehicle(r.geometry, v);
        return { key: `${r.incidentId}-${r.vehicleId}`, path };
      })
      .filter((d) => d.path.length >= 2)
      .filter((d) => {
        if (seen.has(d.key)) return false;
        seen.add(d.key);
        return true;
      });
  }, [allDispatchRoutes, vehicles, routeVehicleId]);

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={CHENNAI_CENTER}
        zoom={11}
        minZoom={10}
        maxZoom={18}
        maxBounds={CHENNAI_BOUNDS}
        maxBoundsViscosity={1}
        className="h-full w-full"
        zoomControl={false}
        preferCanvas={true}
        inertia={true}
        inertiaDeceleration={3000}
        inertiaMaxSpeed={Infinity}
        easeLinearity={0.2}
      >
        <TileLayer
          attribution={
            USE_OFFLINE_TILES
              ? "Chennai tiles (offline)"
              : '&copy; OSM &copy; CARTO'
          }
          url={
            USE_OFFLINE_TILES
              ? "/tiles/{z}/{x}/{y}.png"
              : "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          }
          maxZoom={18}
          maxNativeZoom={18}
          keepBuffer={6}
          updateWhenIdle={true}
          updateWhenZooming={false}
          errorTileUrl="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        />
        <ZoomControl position="topleft" />
        <MapContent
          hexCells={hexCells}
          incidents={incidents}
          vehicles={vehicles}
          routedPath={routedPath}
          allRoutedPaths={allRoutedPaths}
          greenCorridorHexes={greenCorridorHexes}
          showHexGrid={showHexGrid}
          trafficSignals={trafficSignals}
          hexLabelById={hexLabelById}
        />
      </MapContainer>
    </div>
  );
}
