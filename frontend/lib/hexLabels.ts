// 2025-02-26
import type { HexCell } from "@/types";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export function indexToHexLabel(index: number): string {
  // 0..25 => A..Z
  // 26..51 => A-1..Z-1
  // 52..77 => A-2..Z-2, etc.
  const letter = ALPHABET[index % 26];
  const group = Math.floor(index / 26); // 0-based group
  return group === 0 ? letter : `${letter}-${group}`;
}

export function buildHexLabelMap(hexCells: HexCell[]): Record<string, string> {
  // Stable mapping: sort by hex_id (deterministic)
  const sorted = [...hexCells].sort((a, b) => a.hex_id.localeCompare(b.hex_id));
  const map: Record<string, string> = {};
  sorted.forEach((cell, idx) => {
    map[cell.hex_id] = indexToHexLabel(idx);
  });
  return map;
}

