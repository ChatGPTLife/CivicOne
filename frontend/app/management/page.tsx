// 2025-02-26
"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchHexGrid, fetchHexIncidentsSummary, type HexIncidentSummary } from "@/lib/api";
import { buildHexLabelMap } from "@/lib/hexLabels";
import type { HexCell } from "@/types";

interface LookupResult {
  hex_id: string;
  center: [number, number];
  incident_count: number;
  patrol_priority_score: number;
}

export default function ManagementPage() {
  const [hexCells, setHexCells] = useState<HexCell[]>([]);
  const [hexIncidents, setHexIncidents] = useState<HexIncidentSummary[]>([]);
  const [search, setSearch] = useState("");
  const [latInput, setLatInput] = useState("");
  const [lngInput, setLngInput] = useState("");
  const [lookupResult, setLookupResult] = useState<LookupResult | null>(null);
  const [loadingHex, setLoadingHex] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoadingHex(true);
      try {
        const [gridRes, summaryRes] = await Promise.all([
          fetchHexGrid(),
          fetchHexIncidentsSummary(),
        ]);
        setHexCells(gridRes.cells);
        setHexIncidents(summaryRes.cells);
      } finally {
        setLoadingHex(false);
      }
    }
    load();
  }, []);

  const hexLabelById = useMemo(() => buildHexLabelMap(hexCells), [hexCells]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return hexIncidents.slice(0, 500);
    return hexIncidents
      .filter((cell) => {
        const label = hexLabelById[cell.hex_id] ?? "";
        return (
          cell.hex_id.toLowerCase().includes(query) ||
          label.toLowerCase().includes(query)
        );
      })
      .slice(0, 500);
  }, [hexIncidents, hexLabelById, search]);

  async function handleLookup() {
    setError(null);
    setLookupResult(null);
    const lat = Number(latInput);
    const lng = Number(lngInput);
    if (Number.isNaN(lat) || Number.isNaN(lng)) {
      setError("Please enter valid numeric latitude and longitude.");
      return;
    }
    setLookingUp(true);
    try {
      const params = new URLSearchParams({ lat: String(lat), lng: String(lng) });
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/hex-lookup/from-coordinates?${params.toString()}`,
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Lookup failed");
      }
      const data: LookupResult = await response.json();
      setLookupResult(data);
    } catch (e: any) {
      setError(e?.message || "Lookup failed");
    } finally {
      setLookingUp(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 bg-[#1a1d21] p-4 text-white">
      <header>
        <h2 className="text-lg font-semibold">Hex Management</h2>
        <p className="mt-1 text-xs text-white/60">
          View all hex boxes (A–Z / A-1 codes) and find which box any coordinate belongs to.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <div className="space-y-3 rounded-lg border border-white/10 bg-[#252a31] p-3">
          <h3 className="text-sm font-semibold">Coordinate → Hex box</h3>
          <p className="text-[11px] text-white/70">
            Paste a user location (from Telegram or WhatsApp) and we&apos;ll tell you which hex box it falls in.
          </p>

          <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
            <label className="space-y-1">
              <span className="text-white/70">Latitude</span>
              <input
                value={latInput}
                onChange={(e) => setLatInput(e.target.value)}
                className="w-full rounded border border-white/20 bg-[#1a1d21] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
                placeholder="13.08"
              />
            </label>
            <label className="space-y-1">
              <span className="text-white/70">Longitude</span>
              <input
                value={lngInput}
                onChange={(e) => setLngInput(e.target.value)}
                className="w-full rounded border border-white/20 bg-[#1a1d21] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
                placeholder="80.27"
              />
            </label>
          </div>

          <button
            type="button"
            onClick={handleLookup}
            disabled={lookingUp}
            className="mt-2 inline-flex items-center justify-center rounded bg-amber-500 px-3 py-1.5 text-xs font-medium text-[#1a1d21] hover:bg-amber-400 disabled:opacity-50"
          >
            {lookingUp ? "Looking up…" : "Find hex box"}
          </button>

          {error && <p className="mt-2 text-xs text-red-300">{error}</p>}

          {lookupResult && (
            <div className="mt-3 rounded border border-white/15 bg-[#1a1d21] p-2 text-xs">
              <p>
                <span className="text-white/60">Hex box:</span>{" "}
                <span className="font-mono">
                  {buildHexLabelMap([
                    { hex_id: lookupResult.hex_id, polygon: [], center: lookupResult.center, incident_count: 0, patrol_priority_score: 0 },
                  ])[lookupResult.hex_id] ?? "?"}
                </span>
              </p>
              <p className="mt-1">
                <span className="text-white/60">Hex ID:</span>{" "}
                <span className="font-mono">{lookupResult.hex_id}</span>
              </p>
              <p className="mt-1 text-white/70">
                Center: {lookupResult.center[0].toFixed(5)}, {lookupResult.center[1].toFixed(5)}
              </p>
            </div>
          )}
        </div>

        <div className="space-y-2 rounded-lg border border-white/10 bg-[#252a31] p-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Hex boxes by incident count (descending)</h3>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by A/B/C code or hex id…"
              className="w-40 rounded border border-white/20 bg-[#1a1d21] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
            />
          </div>
          <p className="text-[10px] text-white/60">
            Showing {filtered.length} of {hexIncidents.length} hexes (sorted by incidents).
          </p>

          <div className="mt-2 max-h-[360px] overflow-auto rounded border border-white/10 bg-[#1a1d21] text-[11px]">
            <table className="min-w-full border-separate border-spacing-y-[1px]">
              <thead className="sticky top-0 bg-[#111318]">
                <tr className="text-left text-[10px] text-white/60">
                  <th className="px-2 py-1 font-medium">Box</th>
                  <th className="px-2 py-1 font-medium">Hex ID</th>
                  <th className="px-2 py-1 font-medium">Incidents</th>
                  <th className="px-2 py-1 font-medium">Types</th>
                  <th className="px-2 py-1 font-medium">Priority</th>
                </tr>
              </thead>
              <tbody>
                {loadingHex ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-3 text-center text-white/60">
                      Loading…
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-2 py-3 text-center text-white/60">
                      No hexes match this search.
                    </td>
                  </tr>
                ) : (
                  filtered.map((cell) => (
                    <tr key={cell.hex_id} className="bg-[#181b20]">
                      <td className="px-2 py-1 font-mono text-[11px]">
                        {hexLabelById[cell.hex_id] ?? "?"}
                      </td>
                      <td className="px-2 py-1 font-mono text-[10px] truncate max-w-[120px]">
                        {cell.hex_id}
                      </td>
                      <td className="px-2 py-1 text-center font-medium">
                        {cell.incident_count}
                      </td>
                      <td className="px-2 py-1 text-white/70 text-[10px]">
                        {Object.entries(cell.incident_types ?? {})
                          .map(([t, n]) => `${t}:${n}`)
                          .join(", ") || "—"}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {cell.patrol_priority_score.toFixed(1)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
}

