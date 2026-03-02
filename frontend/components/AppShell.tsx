// 2025-02-26
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useRadio } from "@/components/RadioProvider";

const SIDEBAR_ITEMS = [
  { href: "/", label: "Live Map", icon: "map" },
  { href: "/incidents", label: "Incidents", icon: "incident" },
  { href: "/dispatch", label: "Dispatch", icon: "dispatch" },
  { href: "/simulation", label: "Deploy Vehicles", icon: "deploy" },
  { href: "/management", label: "Hex Management", icon: "hex" },
  { href: "/logs", label: "Event Logs", icon: "logs" },
] as const;

function SidebarIcon({ icon }: { icon: string }) {
  const size = 20;
  if (icon === "map")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M9 20l-5.5-3L3 20V4l5.5 3L12 4l5.5 3L21 4v16l-5.5-3L12 20l-3-1.5" />
      </svg>
    );
  if (icon === "incident")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    );
  if (icon === "dispatch")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <rect x="1" y="3" width="15" height="13" rx="2" />
        <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
        <circle cx="5.5" cy="18.5" r="2.5" />
        <circle cx="18.5" cy="18.5" r="2.5" />
      </svg>
    );
  if (icon === "deploy")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
      </svg>
    );
  if (icon === "hex")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M12 2l7 4v8l-7 4-7-4V6l7-4z" />
      </svg>
    );
  if (icon === "logs")
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    );
  return null;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { radioEnabled, enableRadio } = useRadio();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex min-h-screen flex-col bg-[#1a1d21]">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[#2d3238] bg-[#252a31] px-3">
        <button
          type="button"
          onClick={() => setSidebarOpen((o) => !o)}
          className="flex h-8 w-8 items-center justify-center rounded text-white/80 hover:bg-white/10 hover:text-white"
          aria-label="Toggle sidebar"
        >
          <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M3 6h18M3 12h18M3 18h18" />
          </svg>
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded bg-amber-500/90 text-[#1a1d21]">
          <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-white">Civic-one</span>
          <span className="text-[10px] text-white/60">One City One Number</span>
        </div>
        <button
          type="button"
          onClick={async () => {
            enableRadio();
            try {
              const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
              await fetch(`${base}/api/radio/test`);
            } catch {
              // ignore
            }
          }}
          className={`ml-auto rounded px-3 py-1.5 text-xs font-medium ${
            radioEnabled
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-white/10 text-white/80 hover:bg-white/20"
          }`}
          title={radioEnabled ? "Radio on - click to test" : "Click to enable radio and play test"}
        >
          {radioEnabled ? "🔊 Radio on" : "🔇 Enable radio"}
        </button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav
          className={`flex shrink-0 flex-col border-r border-[#2d3238] bg-[#252a31] py-2 transition-all duration-200 ${
            sidebarOpen ? "w-44" : "w-14"
          }`}
        >
          {SIDEBAR_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex h-11 items-center gap-3 rounded-none border-l-2 px-3 transition-colors ${
                  isActive
                    ? "border-amber-500 bg-amber-500/10 text-amber-400"
                    : "border-transparent text-white/60 hover:bg-white/5 hover:text-white/90"
                }`}
                title={item.label}
              >
                <span className="flex shrink-0">
                  <SidebarIcon icon={item.icon} />
                </span>
                {sidebarOpen && (
                  <span className="truncate text-sm font-medium">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Main content - map or page content */}
        <main className="flex-1 overflow-hidden bg-[#1a1d21]">
          {children}
        </main>
      </div>
    </div>
  );
}
