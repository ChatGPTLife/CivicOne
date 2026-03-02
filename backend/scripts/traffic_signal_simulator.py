#!/usr/bin/env python3
# 2025-02-26
"""
Traffic signal simulator for One City One Number – Chennai.

Goal:
- Maintain a set of static traffic signals across Chennai.
- Simulate realistic phase changes (GREEN → YELLOW → RED) in a loop.
- Provide a single place where the dispatch engine can later ask:
    "What is the current state of all signals near this route?"

For now this script just runs a console simulation so you can see the timing.
Later we can:
- Push updates over Socket.IO (similar to the patrol simulator), or
- Expose an API/DB table that the dispatch engine reads.

Usage:
  From backend folder:
    python scripts/traffic_signal_simulator.py
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Literal


Phase = Literal["GREEN", "YELLOW", "RED"]


@dataclass
class TrafficSignal:
  id: str
  name: str
  latitude: float
  longitude: float
  green_s: int = 35
  yellow_s: int = 4
  red_s: int = 35

  @property
  def cycle_s(self) -> int:
    return self.green_s + self.yellow_s + self.red_s

  def phase_at(self, t: float) -> Phase:
    """
    Return the phase at absolute time t (seconds since epoch).
    All signals share the same clock; we can later offset by id if needed.
    """
    position = int(t) % self.cycle_s
    if position < self.green_s:
      return "GREEN"
    if position < self.green_s + self.yellow_s:
      return "YELLOW"
    return "RED"


# Static sample signals placed across Chennai (approximate coordinates).
# You can add more entries here as needed.
TRAFFIC_SIGNALS: list[TrafficSignal] = [
  TrafficSignal("sig_egmore", "Egmore Junction", 13.0774, 80.2609),
  TrafficSignal("sig_central", "Chennai Central", 13.0825, 80.2757),
  TrafficSignal("sig_guindy", "Guindy Kathipara", 13.0108, 80.2037),
  TrafficSignal("sig_adyar", "Adyar Signal", 13.0040, 80.2558),
  TrafficSignal("sig_tnagar", "T Nagar Panagal", 13.0417, 80.2330),
  TrafficSignal("sig_velachery", "Velachery Main", 12.9792, 80.2209),
  TrafficSignal("sig_thiruvanmiyur", "Thiruvanmiyur", 12.9848, 80.2573),
  TrafficSignal("sig_omr_sholinganallur", "OMR Sholinganallur", 12.9010, 80.2274),
  TrafficSignal("sig_anna_nagar", "Anna Nagar Roundtana", 13.0878, 80.2070),
  TrafficSignal("sig_poonamallee", "Poonamallee Junction", 13.0487, 80.1105),
]


def format_phase(phase: Phase) -> str:
  if phase == "GREEN":
    return "GREEN  (go)"
  if phase == "YELLOW":
    return "YELLOW (prepare)"
  return "RED    (stop)"


def main() -> None:
  print("Traffic Signal Simulator – Chennai")
  print("Simulating static signals with realistic phase timings.")
  print("Press Ctrl+C to stop.\n")

  try:
    while True:
      now = time.time()
      print(f"t = {int(now)}")
      for sig in TRAFFIC_SIGNALS:
        phase = sig.phase_at(now)
        # For later integration, dispatch engine can import this module and call phase_at()
        print(
          f"  {sig.name:30s} "
          f"({sig.latitude:.4f}, {sig.longitude:.4f})  ->  {format_phase(phase)}"
        )
      print("-" * 72)
      # Update once per second; internally cycle seconds are 35/4/35.
      time.sleep(1.0)
  except KeyboardInterrupt:
    print("\nStopped traffic signal simulation.")


if __name__ == "__main__":
  main()

