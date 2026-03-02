// 2025-02-26
"use client";

import { useMemo, useState } from "react";

import type { IncidentType } from "@/types";

interface IncidentFormProps {
  defaultLat: number;
  defaultLng: number;
  onSubmit: (payload: { type: IncidentType; latitude: number; longitude: number }) => Promise<void>;
  isSubmitting: boolean;
}

const INCIDENT_TYPES: IncidentType[] = ["crime", "fire", "medical", "accident", "civic"];

export default function IncidentForm({
  defaultLat,
  defaultLng,
  onSubmit,
  isSubmitting,
}: IncidentFormProps) {
  const [incidentType, setIncidentType] = useState<IncidentType>("fire");
  const [latitude, setLatitude] = useState<number>(defaultLat);
  const [longitude, setLongitude] = useState<number>(defaultLng);

  const disabled = useMemo(
    () => isSubmitting || Number.isNaN(latitude) || Number.isNaN(longitude),
    [isSubmitting, latitude, longitude],
  );

  return (
    <section className="rounded-lg border border-white/10 bg-[#1a1d21]/80 p-3">
      <h2 className="text-xs font-semibold text-white">Create Incident</h2>
      <p className="mt-0.5 text-[10px] text-white/50">POST /api/incidents</p>
      <div className="mt-2 grid gap-2">
        <label className="grid gap-1 text-[10px] text-white/70">
          Type
          <select
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
            value={incidentType}
            onChange={(event) => setIncidentType(event.target.value as IncidentType)}
          >
            {INCIDENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <div className="grid grid-cols-2 gap-2">
        <label className="grid gap-1 text-[10px] text-white/70">
          Latitude
          <input
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
              type="number"
              step="0.000001"
              value={latitude}
              onChange={(event) => setLatitude(Number(event.target.value))}
            />
          </label>
        <label className="grid gap-1 text-[10px] text-white/70">
          Longitude
          <input
            className="rounded border border-white/20 bg-[#252a31] px-2 py-1.5 text-xs text-white outline-none focus:border-amber-500"
              type="number"
              step="0.000001"
              value={longitude}
              onChange={(event) => setLongitude(Number(event.target.value))}
            />
          </label>
        </div>

        <button
          className="rounded bg-amber-500 px-3 py-1.5 text-xs font-medium text-[#1a1d21] hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          disabled={disabled}
          onClick={() => onSubmit({ type: incidentType, latitude, longitude })}
        >
          {isSubmitting ? "Submitting…" : "Submit Incident"}
        </button>
      </div>
    </section>
  );
}
