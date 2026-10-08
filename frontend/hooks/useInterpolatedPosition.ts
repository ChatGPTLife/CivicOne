// 2025-02-26
"use client";

import { useEffect, useRef, useState } from "react";

/** Match patrol simulator tick (~0.2s) with a little overlap so motion never stalls. */
const DURATION_MS = 280;
const SNAP_DISTANCE = 0.008; // ~800m — treat as teleport, snap instead of easing

function easeInOut(t: number) {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

/**
 * Returns smoothly interpolated [lat, lng] that glides toward the latest target
 * over a fixed duration (time-based, frame-rate independent).
 */
export function useInterpolatedPosition(
  targetLat: number,
  targetLng: number,
): [number, number] {
  const [position, setPosition] = useState<[number, number]>([targetLat, targetLng]);
  const currentRef = useRef({ lat: targetLat, lng: targetLng });
  const fromRef = useRef({ lat: targetLat, lng: targetLng });
  const toRef = useRef({ lat: targetLat, lng: targetLng });
  const startRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const jump = Math.hypot(targetLat - currentRef.current.lat, targetLng - currentRef.current.lng);
    if (jump < 1e-9) return;

    if (jump > SNAP_DISTANCE) {
      currentRef.current = { lat: targetLat, lng: targetLng };
      setPosition([targetLat, targetLng]);
      return;
    }

    fromRef.current = { ...currentRef.current };
    toRef.current = { lat: targetLat, lng: targetLng };
    startRef.current = performance.now();

    const animate = (now: number) => {
      const t = Math.min(1, (now - startRef.current) / DURATION_MS);
      const k = easeInOut(t);
      const lat = fromRef.current.lat + (toRef.current.lat - fromRef.current.lat) * k;
      const lng = fromRef.current.lng + (toRef.current.lng - fromRef.current.lng) * k;
      currentRef.current = { lat, lng };
      setPosition([lat, lng]);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        rafRef.current = null;
      }
    };

    if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [targetLat, targetLng]);

  return position;
}
