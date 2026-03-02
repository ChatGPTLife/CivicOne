// 2025-02-26
"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { fetchIncidents, markIncidentAttended } from "@/lib/api";
import type { IncidentListItem } from "@/lib/api";
import { getSocketClient } from "@/lib/socket";

const TYPE_LABELS: Record<string, string> = {
  fire: "Fire",
  medical: "Medical",
  road_accident: "Road Accident",
  road_damage: "Road Damage",
  garbage: "Garbage",
  public_safety: "Public Safety",
  theft: "Theft",
  suspicious: "Suspicious",
  public_disturbance: "Public Disturbance",
};

const TYPE_ICONS: Record<string, string> = {
  fire: "🔥",
  medical: "🏥",
  road_accident: "🚗",
  road_damage: "🛣️",
  garbage: "🗑️",
  public_safety: "🛡️",
  theft: "🔒",
  suspicious: "👁️",
  public_disturbance: "📢",
};

function IncidentCard({
  inc,
  onMarkAttended,
  markingId,
}: {
  inc: IncidentListItem;
  onMarkAttended: (id: string) => void;
  markingId: string | null;
}) {
  const typeLabel = TYPE_LABELS[inc.type] ?? inc.type;
  const typeIcon = TYPE_ICONS[inc.type] ?? "📍";
  const mapUrl = `https://www.google.com/maps?q=${inc.latitude},${inc.longitude}`;

  return (
    <div className="group rounded-xl border border-white/10 bg-[#252a31] transition-all hover:border-amber-500/30 hover:shadow-lg hover:shadow-amber-500/5">
      <div className="flex gap-4 p-4">
        {/* Media / Icon */}
        <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-[#1a1d21]">
          {inc.photo_url ? (
            <Image
              src={inc.photo_url}
              alt="Incident"
              width={80}
              height={80}
              className="h-full w-full object-cover"
              unoptimized
            />
          ) : (
            <span className="text-3xl">{typeIcon}</span>
          )}
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold text-white">{typeLabel}</h3>
              {inc.report_id && (
                <span className="text-xs text-white/50 font-mono">{inc.report_id}</span>
              )}
            </div>
            <span
              className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                inc.attended
                  ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30"
                  : "bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30"
              }`}
            >
              {inc.attended ? "Resolved" : inc.status}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-white/60">
            <span className="font-mono">
              {inc.latitude.toFixed(5)}, {inc.longitude.toFixed(5)}
            </span>
            {inc.hex_id && (
              <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-white/70">
                {inc.hex_id}
              </span>
            )}
            <span className="capitalize text-white/50">{inc.source}</span>
          </div>

          <p className="mt-1 text-xs text-white/40">
            {new Date(inc.created_at).toLocaleString(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
            })}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href={mapUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-xs text-white/80 hover:bg-white/10 hover:text-white transition-colors"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
              View on map
            </a>
            <Link
              href="/"
              className="inline-flex items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-400 hover:bg-amber-500/20 transition-colors"
            >
              Open Live Map
            </Link>
            {!inc.attended && (
              <button
                type="button"
                onClick={() => onMarkAttended(inc.id)}
                disabled={markingId === inc.id}
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/20 px-2.5 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500/30 disabled:opacity-50 transition-colors"
              >
                {markingId === inc.id ? (
                  <>
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                    Marking…
                  </>
                ) : (
                  "Mark attended"
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [markingId, setMarkingId] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const data = await fetchIncidents();
      setIncidents(data.incidents);
    } catch (err) {
      console.error("Failed to fetch incidents:", err);
      setIncidents([]);
      setFetchError(
        err && typeof err === "object" && "message" in err
          ? String((err as Error).message)
          : "Failed to load incidents. Check that the backend is running on port 8000.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const socket = getSocketClient();
    const onNewIncident = (event: Record<string, unknown>) => {
      const id = String(event.id ?? "");
      if (!id) return;
      setIncidents((prev) => {
        if (prev.some((i) => i.id === id)) return prev;
        const inc: IncidentListItem = {
          id,
          type: String(event.type ?? "civic"),
          latitude: Number(event.latitude ?? 0),
          longitude: Number(event.longitude ?? 0),
          hex_id: (event.hex_id as string) ?? null,
          assigned_vehicle_id: (event.assigned_vehicle_id as string) ?? null,
          status: String(event.status ?? "new"),
          attended: false,
          report_id: (event.report_id as string) ?? null,
          photo_url: (event.photo_url as string) ?? null,
          video_url: (event.video_url as string) ?? null,
          voice_url: (event.voice_url as string) ?? null,
          source: String(event.source ?? "web"),
          created_at: String(event.created_at ?? new Date().toISOString()),
        };
        return [inc, ...prev];
      });
    };
    const onIncidentAttended = (event: { incident_id: string }) => {
      setIncidents((prev) =>
        prev.map((i) =>
          i.id === event.incident_id ? { ...i, attended: true, status: "attended" } : i,
        ),
      );
    };
    socket.on("new_incident", onNewIncident);
    socket.on("incident_attended", onIncidentAttended);
    return () => {
      socket.off("new_incident", onNewIncident);
      socket.off("incident_attended", onIncidentAttended);
    };
  }, []);

  const handleMarkAttended = async (id: string) => {
    setMarkingId(id);
    try {
      await markIncidentAttended(id);
      setIncidents((prev) =>
        prev.map((i) => (i.id === id ? { ...i, attended: true, status: "attended" } : i)),
      );
    } catch (err) {
      console.error("Failed to mark attended:", err);
    } finally {
      setMarkingId(null);
    }
  };

  const activeCount = incidents.filter((i) => !i.attended).length;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#1a1d21]">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-[#2d3238] bg-[#252a31] px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold text-white">Incidents</h1>
          <p className="mt-0.5 text-sm text-white/60">
            Reported incidents from Telegram and web
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-4 rounded-lg border border-white/10 bg-[#1a1d21] px-4 py-2">
            <div>
              <span className="text-2xl font-bold text-white">{incidents.length}</span>
              <span className="ml-1 text-xs text-white/50">total</span>
            </div>
            <div className="h-8 w-px bg-white/10" />
            <div>
              <span className="text-2xl font-bold text-amber-400">{activeCount}</span>
              <span className="ml-1 text-xs text-white/50">active</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10 disabled:opacity-50 transition-colors"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {loading && incidents.length === 0 ? (
          <div className="flex h-48 items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-amber-500/30 border-t-amber-500" />
              <p className="text-sm text-white/60">Loading incidents…</p>
            </div>
          </div>
        ) : fetchError ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-red-500/20 bg-red-500/5 py-16 text-center">
            <span className="text-5xl opacity-50">⚠️</span>
            <h3 className="mt-4 text-lg font-medium text-white">Could not load incidents</h3>
            <p className="mt-1 max-w-md text-sm text-white/60">{fetchError}</p>
            <p className="mt-2 text-xs text-white/40">
              Ensure the backend is running: <code className="rounded bg-white/10 px-1">python app.py</code>
            </p>
            <button
              type="button"
              onClick={() => load()}
              className="mt-4 rounded-lg bg-amber-500/20 px-4 py-2 text-sm font-medium text-amber-400 hover:bg-amber-500/30 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : incidents.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-[#252a31]/50 py-16 text-center">
            <span className="text-5xl opacity-50">📍</span>
            <h3 className="mt-4 text-lg font-medium text-white">No incidents yet</h3>
            <p className="mt-1 max-w-sm text-sm text-white/60">
              Incidents reported via Telegram or the web form will appear here.
            </p>
            <button
              type="button"
              onClick={() => load()}
              className="mt-4 rounded-lg bg-amber-500/20 px-4 py-2 text-sm font-medium text-amber-400 hover:bg-amber-500/30 transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {incidents.map((inc) => (
              <IncidentCard
                key={inc.id}
                inc={inc}
                onMarkAttended={handleMarkAttended}
                markingId={markingId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
