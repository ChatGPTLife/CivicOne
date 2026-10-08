// 2025-02-26
"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import * as maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";

if (typeof window !== "undefined") {
  maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");
}

type GeoJSONSource = maplibregl.GeoJSONSource;
type MapLibreMap = maplibregl.Map;

import type { HexCell, Incident, TrafficSignal, Vehicle } from "@/types";
import { buildHexLabelMap } from "@/lib/hexLabels";

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
const CHENNAI_BOUNDS: [[number, number], [number, number]] = [
  [79.9, 12.7],
  [80.4, 13.3],
];

const CHENNAI_HOSPITALS: { id: string; name: string; lat: number; lng: number }[] = [
  { id: "H1", name: "Rajiv Gandhi Govt Hospital", lat: 13.0826, lng: 80.275 },
  { id: "H2", name: "Stanley Medical College", lat: 13.1009, lng: 80.2937 },
  { id: "H3", name: "Govt General Hospital", lat: 13.0809, lng: 80.2668 },
  { id: "H4", name: "Apollo Hospitals Greams Rd", lat: 13.0658, lng: 80.2585 },
  { id: "H5", name: "MIOT International", lat: 13.0288, lng: 80.2078 },
  { id: "H6", name: "Fortis Malar", lat: 13.0128, lng: 80.2578 },
  { id: "H7", name: "OMR Private Hospital", lat: 12.9684, lng: 80.2414 },
];

const USE_OFFLINE_TILES =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_USE_OFFLINE_TILES === "true";

const MAP_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/bright";

const VEHICLE_DURATION_MS = 280;
const SNAP_DISTANCE = 0.008;

type VehicleMotion = {
  marker: maplibregl.Marker;
  fromLat: number;
  fromLng: number;
  toLat: number;
  toLng: number;
  curLat: number;
  curLng: number;
  start: number;
  duration: number;
  facingLeft: boolean;
  type: Vehicle["type"];
};

function vehicleLabel(type: Vehicle["type"]) {
  if (type === "police") return "Pink Patrol (police)";
  if (type === "ambulance") return "Ambulance";
  if (type === "fire") return "Fire Service";
  return "Municipal";
}

function vehicleIconHtml(type: Vehicle["type"]) {
  if (type === "police") {
    return `<img src="/police_patrolcar.png" alt="" width="64" height="32" draggable="false" style="transition: transform 0.25s ease;" />`;
  }
  if (type === "ambulance") {
    return `<img src="/ambulance.png" alt="" width="72" height="32" draggable="false" style="transition: transform 0.25s ease;" />`;
  }
  if (type === "fire") {
    return `<img src="/fire_truck.png" alt="" width="80" height="32" draggable="false" style="transition: transform 0.25s ease;" />`;
  }
  if (type === "municipal") return `<span style="font-size:24px;line-height:1">🚜</span>`;
  return `<span style="font-size:24px;line-height:1">🚗</span>`;
}

function makeVehicleElement(v: Vehicle) {
  const el = document.createElement("div");
  el.className = "civic-vehicle-marker";
  el.innerHTML = vehicleIconHtml(v.type);
  el.title = `${vehicleLabel(v.type)} · ${v.status}`;
  return el;
}

function popupHtml(title: string, rows: string[]) {
  return `<div class="civic-popup"><div class="civic-popup-title">${title}</div>${rows
    .map((r) => `<div>${r}</div>`)
    .join("")}</div>`;
}

function add3dBuildings(map: MapLibreMap) {
  if (map.getLayer("3d-buildings")) return;

  const style = map.getStyle();
  const layers = style.layers ?? [];
  let labelLayerId: string | undefined;
  for (const layer of layers) {
    const layout = layer.layout as Record<string, unknown> | undefined;
    if (layer.type === "symbol" && layout && layout["text-field"]) {
      labelLayerId = layer.id;
      break;
    }
  }

  const sources = style.sources ?? {};
  let sourceId = "openmaptiles";
  if (!sources[sourceId]) {
    for (const [id, s] of Object.entries(sources)) {
      if ((s as { type?: string }).type === "vector") {
        sourceId = id;
        break;
      }
    }
  }

  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, {
      url: "https://tiles.openfreemap.org/planet",
      type: "vector",
    });
  }

  map.addLayer(
    {
      id: "3d-buildings",
      source: sourceId,
      "source-layer": "building",
      type: "fill-extrusion",
      minzoom: 14,
      paint: {
        "fill-extrusion-color": "#aaa",
        "fill-extrusion-height": [
          "interpolate",
          ["linear"],
          ["zoom"],
          14,
          0,
          14.5,
          ["coalesce", ["get", "render_height"], ["get", "height"], 15],
        ],
        "fill-extrusion-base": [
          "interpolate",
          ["linear"],
          ["zoom"],
          14,
          0,
          14.5,
          ["coalesce", ["get", "render_min_height"], ["get", "min_height"], 0],
        ],
        "fill-extrusion-opacity": 0.6,
      },
    },
    labelLayerId,
  );
}

function addOverlayLayers(map: MapLibreMap) {
  map.addSource("hex-grid", { type: "geojson", data: emptyFc() });
  map.addSource("incidents", { type: "geojson", data: emptyFc() });
  map.addSource("routes", { type: "geojson", data: emptyFc() });

  map.addLayer({
    id: "hex-fill",
    type: "fill",
    source: "hex-grid",
    paint: {
      "fill-color": ["get", "fillColor"],
      "fill-opacity": ["get", "fillOpacity"],
    },
  });
  map.addLayer({
    id: "hex-outline",
    type: "line",
    source: "hex-grid",
    paint: {
      "line-color": ["get", "strokeColor"],
      "line-width": ["get", "strokeWidth"],
      "line-opacity": ["get", "strokeOpacity"],
    },
  });
  map.addLayer({
    id: "incident-dots",
    type: "circle",
    source: "incidents",
    paint: {
      "circle-radius": 5,
      "circle-color": "#dc2626",
      "circle-stroke-width": 2,
      "circle-stroke-color": "#7f1d1d",
    },
  });
  map.addLayer({
    id: "dispatch-routes",
    type: "line",
    source: "routes",
    paint: {
      "line-color": "#22d3ee",
      "line-width": 4.5,
      "line-opacity": 0.92,
    },
  });
}

function emptyFc(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function setSourceData(map: MapLibreMap, id: string, data: GeoJSON.FeatureCollection) {
  const src = map.getSource(id) as GeoJSONSource | undefined;
  src?.setData(data);
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

function hexFeatureCollection(
  hexCells: HexCell[],
  hexLabelById: Record<string, string>,
  greenCorridorHexes: string[],
  showHexGrid: boolean,
): GeoJSON.FeatureCollection {
  if (!showHexGrid) return emptyFc();
  const features: GeoJSON.Feature[] = [];
  for (const cell of hexCells) {
    const positions = (cell.polygon || []).map(([lat, lng]) => [lng, lat] as [number, number]);
    if (positions.length < 3) continue;
    if (
      positions[0][0] !== positions[positions.length - 1][0] ||
      positions[0][1] !== positions[positions.length - 1][1]
    ) {
      positions.push(positions[0]);
    }
    const isCorridor = greenCorridorHexes.includes(cell.hex_id);
    const count = cell.incident_count ?? 0;
    const label = hexLabelById[cell.hex_id] ?? "?";
    const priority = cell.patrol_priority_score ?? 0;
    features.push({
      type: "Feature",
      properties: {
        hex_id: cell.hex_id,
        label,
        count,
        priority,
        fillColor: isCorridor ? "#0d9488" : count >= 3 ? "#f59e0b" : "#334155",
        fillOpacity: isCorridor ? 0.12 : count >= 5 ? 0.14 : count >= 2 ? 0.1 : 0.05,
        strokeColor: isCorridor ? "#0d9488" : count >= 3 ? "#f59e0b" : "#475569",
        strokeWidth: isCorridor ? 2.2 : count >= 2 ? 1.8 : 1.2,
        strokeOpacity: isCorridor ? 0.95 : 0.75,
      },
      geometry: { type: "Polygon", coordinates: [positions] },
    });
  }
  return { type: "FeatureCollection", features };
}

function incidentFeatureCollection(incidents: Incident[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: incidents.map((inc) => ({
      type: "Feature" as const,
      properties: { id: inc.id, type: inc.type, status: inc.status },
      geometry: { type: "Point" as const, coordinates: [inc.longitude, inc.latitude] },
    })),
  };
}

function routeFeatureCollection(paths: [number, number][][]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: paths
      .filter((path) => path.length >= 2)
      .map((path, i) => ({
        type: "Feature" as const,
        properties: { id: String(i) },
        geometry: {
          type: "LineString" as const,
          coordinates: path.map(([lat, lng]) => [lng, lat]),
        },
      })),
  };
}

function offlineStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    sources: {
      raster: {
        type: "raster",
        tiles: ["/tiles/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "Chennai tiles (offline)",
      },
    },
    layers: [{ id: "raster", type: "raster", source: "raster" }],
  };
}

function signalElement(s: TrafficSignal) {
  const r = s.phase === "RED" ? "#dc2626" : "#4b5563";
  const y = s.phase === "YELLOW" ? "#facc15" : "#4b5563";
  const g = s.phase === "GREEN" ? "#22c55e" : "#4b5563";
  const el = document.createElement("div");
  el.innerHTML = `
    <div class="traffic-signal-marker" style="
      width:14px;height:24px;background:#1f2937;border-radius:4px;
      border:1px solid #374151;display:flex;flex-direction:column;
      align-items:center;justify-content:space-around;padding:2px;
    ">
      <div style="width:8px;height:6px;border-radius:50%;background:${r};box-shadow:0 0 4px ${r}"></div>
      <div style="width:8px;height:6px;border-radius:50%;background:${y};box-shadow:0 0 4px ${y}"></div>
      <div style="width:8px;height:6px;border-radius:50%;background:${g};box-shadow:0 0 4px ${g}"></div>
    </div>`;
  return el.firstElementChild as HTMLElement;
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
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const motionsRef = useRef<Map<string, VehicleMotion>>(new Map());
  const extraMarkersRef = useRef<maplibregl.Marker[]>([]);
  const hexLabelById = useMemo(() => buildHexLabelMap(hexCells), [hexCells]);

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

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    maplibregl.setWorkerUrl("/maplibre-gl-worker.mjs");

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: USE_OFFLINE_TILES ? offlineStyle() : MAP_STYLE,
      center: [CHENNAI_CENTER[1], CHENNAI_CENTER[0]],
      zoom: 14.2,
      pitch: 55,
      bearing: -17.6,
      minZoom: 10,
      maxZoom: 18,
      maxBounds: CHENNAI_BOUNDS,
      canvasContextAttributes: { antialias: true },
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-left");
    mapRef.current = map;

    map.on("error", (e) => {
      console.warn("MapLibre event:", e);
    });

    const onLoad = () => {
      if (!USE_OFFLINE_TILES) add3dBuildings(map);
      addOverlayLayers(map);
      setMapReady(true);
    };
    map.on("load", onLoad);

    const hexPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });
    map.on("mousemove", "hex-fill", (e) => {
      const f = e.features?.[0];
      if (!f || !e.lngLat) return;
      const p = f.properties ?? {};
      hexPopup
        .setLngLat(e.lngLat)
        .setHTML(
          popupHtml(`Hex ${p.label ?? "?"}`, [
            `ID: ${String(p.hex_id ?? "").slice(0, 12)}…`,
            `Incidents: ${p.count ?? 0}`,
            Number(p.priority) > 0 ? `Priority: ${Number(p.priority).toFixed(1)}` : "",
          ].filter(Boolean)),
        )
        .addTo(map);
    });
    map.on("mouseleave", "hex-fill", () => hexPopup.remove());

    const incidentPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });
    map.on("mousemove", "incident-dots", (e) => {
      const f = e.features?.[0];
      if (!f || !e.lngLat) return;
      const p = f.properties ?? {};
      incidentPopup
        .setLngLat(e.lngLat)
        .setHTML(popupHtml("Incident", [`Type: ${p.type}`, `Status: ${p.status}`]))
        .addTo(map);
    });
    map.on("mouseleave", "incident-dots", () => incidentPopup.remove());

    const ro = new ResizeObserver(() => map.resize());
    ro.observe(containerRef.current);

    let raf = 0;
    const tick = (now: number) => {
      for (const motion of motionsRef.current.values()) {
        const duration = motion.duration || 220;
        const t = Math.min(1.0, (now - motion.start) / duration);
        motion.curLat = motion.fromLat + (motion.toLat - motion.fromLat) * t;
        motion.curLng = motion.fromLng + (motion.toLng - motion.fromLng) * t;
        motion.marker.setLngLat([motion.curLng, motion.curLat]);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      setMapReady(false);
      for (const m of extraMarkersRef.current) m.remove();
      extraMarkersRef.current = [];
      for (const motion of motionsRef.current.values()) motion.marker.remove();
      motionsRef.current.clear();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    setSourceData(map, "hex-grid", hexFeatureCollection(hexCells, hexLabelById, greenCorridorHexes, showHexGrid));
  }, [hexCells, hexLabelById, greenCorridorHexes, showHexGrid, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    setSourceData(map, "incidents", incidentFeatureCollection(incidents));
  }, [incidents, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const paths = [
      ...(routedPath.length >= 2 ? [routedPath] : []),
      ...allRoutedPaths.map((p) => p.path),
    ];
    setSourceData(map, "routes", routeFeatureCollection(paths));
  }, [routedPath, allRoutedPaths, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const motions = motionsRef.current;
    const seen = new Set<string>();
    const now = performance.now();

    for (const v of vehicles) {
      const id = String(v.id);
      seen.add(id);
      const existing = motions.get(id);
      if (!existing) {
        const el = makeVehicleElement(v);
        const marker = new maplibregl.Marker({ element: el, anchor: "center" })
          .setLngLat([v.longitude, v.latitude])
          .setPopup(
            new maplibregl.Popup({ offset: 16, closeButton: false }).setHTML(
              popupHtml(vehicleLabel(v.type), [
                `Status: ${v.status}`,
                `ID: ${id.slice(0, 8)}…`,
              ]),
            ),
          )
          .addTo(map);
        motions.set(id, {
          marker,
          fromLat: v.latitude,
          fromLng: v.longitude,
          toLat: v.latitude,
          toLng: v.longitude,
          curLat: v.latitude,
          curLng: v.longitude,
          start: now,
          duration: 220,
          facingLeft: false,
          type: v.type,
        });
        continue;
      }
      if (existing.type !== v.type) {
        existing.marker.getElement().innerHTML = vehicleIconHtml(v.type);
        existing.type = v.type;
      }
      existing.marker.setPopup(
        new maplibregl.Popup({ offset: 16, closeButton: false }).setHTML(
          popupHtml(vehicleLabel(v.type), [`Status: ${v.status}`, `ID: ${id.slice(0, 8)}…`]),
        ),
      );
      const jump = Math.hypot(v.latitude - existing.curLat, v.longitude - existing.curLng);
      if (jump < 1e-9) continue;
      if (jump > SNAP_DISTANCE) {
        existing.curLat = v.latitude;
        existing.curLng = v.longitude;
        existing.fromLat = v.latitude;
        existing.fromLng = v.longitude;
        existing.toLat = v.latitude;
        existing.toLng = v.longitude;
        existing.marker.setLngLat([v.longitude, v.latitude]);
      } else {
        const dLng = v.longitude - existing.curLng;
        if (dLng < -1e-6 && !existing.facingLeft) {
          existing.facingLeft = true;
          const img = existing.marker.getElement().querySelector("img");
          if (img) img.style.transform = "scaleX(-1)";
        } else if (dLng > 1e-6 && existing.facingLeft) {
          existing.facingLeft = false;
          const img = existing.marker.getElement().querySelector("img");
          if (img) img.style.transform = "scaleX(1)";
        }

        const elapsed = now - existing.start;
        const duration = Math.max(140, Math.min(450, elapsed || 220));

        existing.fromLat = existing.curLat;
        existing.fromLng = existing.curLng;
        existing.toLat = v.latitude;
        existing.toLng = v.longitude;
        existing.start = now;
        existing.duration = duration;
      }
    }

    for (const id of Array.from(motions.keys())) {
      if (!seen.has(id)) {
        motions.get(id)?.marker.remove();
        motions.delete(id);
      }
    }
  }, [vehicles, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    for (const m of extraMarkersRef.current) m.remove();
    extraMarkersRef.current = [];

    for (const h of CHENNAI_HOSPITALS) {
      const el = document.createElement("div");
      el.style.fontSize = "20px";
      el.style.lineHeight = "1";
      el.textContent = "🏥";
      extraMarkersRef.current.push(
        new maplibregl.Marker({ element: el, anchor: "center" })
          .setLngLat([h.lng, h.lat])
          .setPopup(new maplibregl.Popup({ offset: 10, closeButton: false }).setText(h.name))
          .addTo(map),
      );
    }

    for (const s of trafficSignals) {
      extraMarkersRef.current.push(
        new maplibregl.Marker({ element: signalElement(s), anchor: "center" })
          .setLngLat([s.longitude, s.latitude])
          .setPopup(
            new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(
              popupHtml(`🚦 ${s.name}`, [`Phase: ${s.phase}`]),
            ),
          )
          .addTo(map),
      );
    }
  }, [trafficSignals, mapReady]);

  return <div ref={containerRef} className="civic-maplibre h-full w-full" />;
}
