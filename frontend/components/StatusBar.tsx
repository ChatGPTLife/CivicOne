// 2025-02-26
interface StatusBarProps {
  hexCount: number;
  incidentCount: number;
  vehicleCount: number;
  connected: boolean;
  greenCorridorActive?: boolean;
}

export default function StatusBar({ hexCount, incidentCount, vehicleCount, connected, greenCorridorActive }: StatusBarProps) {
  return (
    <section className="grid grid-cols-2 gap-3 rounded-lg border border-white/10 bg-[#1a1d21]/80 p-3 sm:grid-cols-5">
      <div>
        <p className="text-[10px] uppercase tracking-wide text-white/50">Socket</p>
        <p className="text-xs font-semibold text-white">{connected ? "Connected" : "Disconnected"}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wide text-white/50">Hex Cells</p>
        <p className="text-xs font-semibold text-white">{hexCount}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wide text-white/50">Incidents</p>
        <p className="text-xs font-semibold text-white">{incidentCount}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wide text-white/50">Vehicles</p>
        <p className="text-xs font-semibold text-white">{vehicleCount}</p>
      </div>
      <div>
        <p className="text-[10px] uppercase tracking-wide text-white/50">Green Corridor</p>
        <p className={`text-xs font-semibold ${greenCorridorActive ? "text-emerald-400" : "text-white/60"}`}>
          {greenCorridorActive ? "Active" : "Inactive"}
        </p>
      </div>
    </section>
  );
}
