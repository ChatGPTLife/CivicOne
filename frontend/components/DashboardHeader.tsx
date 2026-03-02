// 2025-02-26
interface DashboardHeaderProps {
  backendUrl: string;
  socketUrl: string;
  showHexGrid: boolean;
  onToggleHex: () => void;
}

export default function DashboardHeader({
  backendUrl,
  socketUrl,
  showHexGrid,
  onToggleHex,
}: DashboardHeaderProps) {
  return (
    <header className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">One City One Number – Chennai</h1>
          <p className="text-sm text-zinc-600">Unified City Emergency & Civic Dispatch Command Dashboard</p>
          <p className="mt-1 text-xs text-zinc-500">Axios API: {backendUrl} | WebSocket: {socketUrl}</p>
        </div>

        <button
          type="button"
          onClick={onToggleHex}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
        >
          {showHexGrid ? "Hide Hex Grid" : "Show Hex Grid"}
        </button>
      </div>
    </header>
  );
}
