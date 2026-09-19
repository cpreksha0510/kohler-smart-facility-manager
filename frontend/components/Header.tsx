"use client";

import React from "react";
import { Activity, Sparkles, Sliders, Layers, LayoutDashboard, Ticket, Leaf } from "lucide-react";

interface HeaderProps {
  activeTab: "dashboard" | "tickets" | "sustainability";
  setActiveTab: (tab: "dashboard" | "tickets" | "sustainability") => void;
  viewMode: "full" | "replay";
  setViewMode: (mode: "full" | "replay") => void;
  openCopilot: () => void;
  openTicketsCount: number;
}

export function Header({
  activeTab,
  setActiveTab,
  viewMode,
  setViewMode,
  openCopilot,
  openTicketsCount,
}: HeaderProps) {
  return (
    <header className="border-b border-white/[0.08] bg-[#161B22]/80 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        {/* Brand Lockup */}
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-[#6B8CAE]/20 to-[#C5A059]/20 border border-white/10 flex items-center justify-center font-bold text-lg tracking-wider text-[#C5A059]">
            K
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-wider text-white uppercase flex items-center gap-2">
                KOHLER <span className="font-light text-[#8B949E]">Facility Monitor</span>
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Telemetry
              </span>
            </div>
            <p className="text-xs text-[#8B949E] mt-0.5">
              Terminal 2 Airport Restroom Block · 4 Zones · 17 Smart Fixtures · Jan 15–16, 2024
            </p>
          </div>
        </div>

        {/* Navigation & Action Controls */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {/* Main Navigation Tabs */}
          <nav className="flex items-center bg-[#0D1117] p-1 rounded-xl border border-white/[0.08] shadow-inner gap-1">
            <button
              id="nav-tab-dashboard"
              onClick={() => setActiveTab("dashboard")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "dashboard"
                  ? "bg-[#21262D] text-white shadow-sm font-semibold border border-white/10"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              <LayoutDashboard className="h-3.5 w-3.5 text-[#6B8CAE]" />
              <span>Dashboard</span>
            </button>
            <button
              id="nav-tab-tickets"
              onClick={() => setActiveTab("tickets")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "tickets"
                  ? "bg-[#21262D] text-[#C5A059] shadow-sm font-semibold border border-[#C5A059]/30"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              <Ticket className="h-3.5 w-3.5 text-[#C5A059]" />
              <span>Tickets</span>
              {openTicketsCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-[#EF4444]/20 border border-[#EF4444]/40 text-[#EF4444]">
                  {openTicketsCount}
                </span>
              )}
            </button>
            <button
              id="nav-tab-sustainability"
              onClick={() => setActiveTab("sustainability")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "sustainability"
                  ? "bg-[#21262D] text-[#98BAAB] shadow-sm font-semibold border border-[#789A8B]/30"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              <Leaf className="h-3.5 w-3.5 text-[#789A8B]" />
              <span>Sustainability</span>
            </button>
          </nav>

          {/* Mode Switcher (Visible on Dashboard) */}
          {activeTab === "dashboard" && (
            <div className="flex items-center bg-[#0D1117] p-1 rounded-lg border border-white/[0.08]">
              <button
                id="btn-mode-full"
                onClick={() => setViewMode("full")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === "full"
                    ? "bg-[#21262D] text-white shadow-sm"
                    : "text-[#8B949E] hover:text-white"
                }`}
              >
                <Layers className="h-3.5 w-3.5 text-[#6B8CAE]" />
                Full Dataset
              </button>
              <button
                id="btn-mode-replay"
                onClick={() => setViewMode("replay")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === "replay"
                    ? "bg-[#21262D] text-[#C5A059] shadow-sm font-semibold"
                    : "text-[#8B949E] hover:text-white"
                }`}
              >
                <Sliders className="h-3.5 w-3.5 text-[#C5A059]" />
                Replay
              </button>
            </div>
          )}

          {/* AI Copilot Trigger */}
          <button
            id="btn-open-copilot"
            onClick={openCopilot}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium bg-gradient-to-r from-[#C5A059]/15 to-[#6B8CAE]/15 hover:from-[#C5A059]/25 hover:to-[#6B8CAE]/25 text-[#F0F6FC] border border-[#C5A059]/30 transition-all glow-brass"
          >
            <Sparkles className="h-3.5 w-3.5 text-[#C5A059]" />
            <span>AI Copilot</span>
          </button>
        </div>
      </div>
    </header>
  );
}
