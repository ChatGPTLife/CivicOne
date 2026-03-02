// 2025-02-26
"use client";

import { useEffect, useRef, useState } from "react";

const LERP_FACTOR = 0.25; // 25% of remaining distance per frame – smooth ease-out
const MIN_DISTANCE = 0.000005; // Stop when this close to target

/**
 * Returns smoothly interpolated [lat, lng] that animates toward target.
 * Uses requestAnimationFrame for butter-smooth 60fps updates.
 */
export function useInterpolatedPosition(
  targetLat: number,
  targetLng: number,
): [number, number] {
  const [position, setPosition] = useState<[number, number]>([targetLat, targetLng]);
  const currentRef = useRef({ lat: targetLat, lng: targetLng });
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const target = { lat: targetLat, lng: targetLng };

    const animate = () => {
      const { lat: clat, lng: clng } = currentRef.current;
      const dlat = target.lat - clat;
      const dlng = target.lng - clng;
      const dist = Math.sqrt(dlat * dlat + dlng * dlng);

      if (dist < MIN_DISTANCE) {
        currentRef.current = { lat: target.lat, lng: target.lng };
        setPosition([target.lat, target.lng]);
        rafRef.current = null;
        return;
      }

      currentRef.current = {
        lat: clat + dlat * LERP_FACTOR,
        lng: clng + dlng * LERP_FACTOR,
      };
      setPosition([currentRef.current.lat, currentRef.current.lng]);
      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [targetLat, targetLng]);

  return position;
}
