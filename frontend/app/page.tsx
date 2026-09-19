"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Header } from "@/components/Header";
import { MetricCards } from "@/components/MetricCards";
import { SustainabilityPanel } from "@/components/SustainabilityPanel";
import { FlowRateChart } from "@/components/FlowRateChart";
import { OccupancyHeatmap } from "@/components/OccupancyHeatmap";
import { TicketsTable } from "@/components/TicketsTable";
import { TicketsView } from "@/components/TicketsView";
import { DailyDigestCard } from "@/components/DailyDigestCard";
import { ReplayScrubber } from "@/components/ReplayScrubber";
import { AiCopilotDrawer } from "@/components/AiCopilotDrawer";
import {
  OverviewMetrics,
  Reading,
  Ticket,
  DailyDigest,
  OccupancyHeatmapData,
  SustainabilitySummary,
} from "@/components/types";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "tickets">("dashboard");
  const [viewMode, setViewMode] = useState<"full" | "replay">("full");
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);

  // Core Data
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [zoneTotals, setZoneTotals] = useState<
    { timestamp_str: string; zone_id: string; flow_rate_lpm: number }[]
  >([]);
  const [heatmapData, setHeatmapData] = useState<OccupancyHeatmapData | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [digests, setDigests] = useState<Record<string, DailyDigest>>({});
  const [sustainability, setSustainability] = useState<SustainabilitySummary | null>(null);
  const [loading, setLoading] = useState(true);

  // Replay Simulator State
  const [replayHours, setReplayHours] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Initial Data Fetch
  const fetchData = async () => {
    try {
      setLoading(true);
      const [ovRes, ztRes, rdRes, hmRes, tkRes, dgRes, susRes] = await Promise.all([
        fetch("/api/overview"),
        fetch("/api/readings/zone-totals?downsample_mins=5"),
        fetch("/api/readings?downsample_mins=5"),
        fetch("/api/occupancy-heatmap"),
        fetch("/api/tickets"),
        fetch("/api/digests"),
        fetch("/api/sustainability/summary"),
      ]);

      if (ovRes.ok) setMetrics(await ovRes.json());
      if (ztRes.ok) setZoneTotals(await ztRes.json());
      if (rdRes.ok) setReadings(await rdRes.json());
      if (hmRes.ok) setHeatmapData(await hmRes.json());
      if (tkRes.ok) setTickets(await tkRes.json());
      if (dgRes.ok) setDigests(await dgRes.json());
      if (susRes.ok) setSustainability(await susRes.json());
    } catch (err) {
      console.error("Error fetching facility telemetry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Update Ticket Status (Optimistic UI + SQLite PATCH)
  const handleTicketStatusChange = async (
    ticketId: string,
    newStatus: "open" | "dispatched" | "resolved",
    resolutionNote?: string
  ) => {
    // 1. Optimistic local update
    setTickets((prev) =>
      prev.map((t) =>
        t.ticket_id === ticketId
          ? {
              ...t,
              status: newStatus,
              resolution_note:
                resolutionNote !== undefined ? resolutionNote : t.resolution_note,
            }
          : t
      )
    );

    // 2. Call backend
    try {
      const payload: { status: string; resolution_note?: string } = { status: newStatus };
      if (resolutionNote !== undefined) {
        payload.resolution_note = resolutionNote;
      }
      const res = await fetch(`/api/tickets/${encodeURIComponent(ticketId)}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update status");
      const updatedData = await res.json();
      if (updatedData.ticket) {
        setTickets((prev) =>
          prev.map((t) => (t.ticket_id === ticketId ? updatedData.ticket : t))
        );
      }
    } catch (err) {
      console.error("Failed to update ticket status on server:", err);
      // Revert on error
      fetchData();
    }
  };

  // Replay Simulator: Filtered data according to replayHours
  const replayCutoffDate = useMemo(() => {
    if (!metrics?.sim_start) return new Date("2024-01-15T00:00:00");
    const start = new Date(metrics.sim_start);
    return new Date(start.getTime() + replayHours * 3600 * 1000);
  }, [metrics?.sim_start, replayHours]);

  const activeReadings = useMemo(() => {
    if (viewMode === "full") return readings;
    return readings.filter((r) => new Date(r.timestamp_str) <= replayCutoffDate);
  }, [viewMode, readings, replayCutoffDate]);

  const activeZoneTotals = useMemo(() => {
    if (viewMode === "full") return zoneTotals;
    return zoneTotals.filter((zt) => new Date(zt.timestamp_str) <= replayCutoffDate);
  }, [viewMode, zoneTotals, replayCutoffDate]);

  const activeTickets = useMemo(() => {
    if (viewMode === "full") return tickets;
    return tickets.filter((t) => new Date(t.timestamp_flagged) <= replayCutoffDate);
  }, [viewMode, tickets, replayCutoffDate]);

  const activeMetrics = useMemo(() => {
    if (!metrics) return null;
    if (viewMode === "full") return metrics;
    const waterLoss = activeTickets.reduce((acc, t) => acc + (t.estimated_water_loss_liters || 0), 0);
    const costImpact = activeTickets.reduce((acc, t) => acc + (t.estimated_cost_impact || 0), 0);
    const openCount = activeTickets.filter((t) => t.status !== "resolved").length;
    const totalSimHours = metrics.sim_duration_hours || 48;
    const progressRatio = Math.min(1, Math.max(0, replayHours / totalSimHours));
    const scaledReadings = Math.round(metrics.sensor_readings_count * progressRatio);

    return {
      ...metrics,
      sensor_readings_count: scaledReadings,
      total_tickets_count: activeTickets.length,
      open_tickets_count: openCount,
      estimated_water_loss_liters: waterLoss,
      estimated_cost_impact_inr: costImpact,
    };
  }, [viewMode, metrics, activeTickets, replayHours]);

  const openTicketsCount = activeTickets.filter((t) => t.status !== "resolved").length;

  return (
    <div className="min-h-screen bg-[#0D1117] text-[#F0F6FC] flex flex-col font-sans selection:bg-[#6B8CAE]/30">
      {/* 1. Executive Brand Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        viewMode={viewMode}
        setViewMode={(mode) => {
          setViewMode(mode);
          if (mode === "replay") {
            setIsPlaying(false);
          }
        }}
        openCopilot={() => setIsCopilotOpen(true)}
        openTicketsCount={openTicketsCount}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6 space-y-6">
        {activeTab === "tickets" ? (
          <TicketsView
            tickets={tickets}
            onStatusChange={handleTicketStatusChange}
            loading={loading}
          />
        ) : (
          <>
            {/* Replay Scrubber Banner (if replay mode) */}
            {viewMode === "replay" && (
              <ReplayScrubber
                simStart={metrics?.sim_start || "2024-01-15T00:00:00"}
                simDurationHours={metrics?.sim_duration_hours || 48}
                currentHours={replayHours}
                onChangeHours={setReplayHours}
                isPlaying={isPlaying}
                onTogglePlay={() => setIsPlaying(!isPlaying)}
                onReset={() => {
                  setIsPlaying(false);
                  setReplayHours(0);
                }}
              />
            )}

            {/* 2. Top-Level Metric Cards */}
            <MetricCards metrics={activeMetrics} loading={loading} />

            {/* 2b. Feature 2: Sustainability & Water Conservation Impact */}
            <SustainabilityPanel summary={sustainability} loading={loading} />

            {/* 3. Flow Rate Telemetry Chart (Recharts) */}
            <FlowRateChart
              readings={readings}
              zoneTotals={zoneTotals}
              loading={loading}
              isReplay={viewMode === "replay"}
              replayCutoffDate={replayCutoffDate}
            />

            {/* 4. Occupancy Heatmap (17 fixtures x 24h) */}
            <OccupancyHeatmap data={heatmapData} loading={loading} />

            {/* 5. End-of-Day Operational Digest Card */}
            <DailyDigestCard digests={digests} />

            {/* 6. Flagged Anomaly Tickets Table */}
            <TicketsTable
              tickets={activeTickets}
              onStatusChange={handleTicketStatusChange}
              loading={loading}
              onNavigateToTickets={() => setActiveTab("tickets")}
            />
          </>
        )}
      </main>

      {/* AI Copilot Slide-out Sheet Drawer */}
      <AiCopilotDrawer
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-white/[0.08] bg-[#161B22] py-4 text-center text-xs text-[#8B949E]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>KOHLER Facility Monitor · Airport Restroom Operations Platform</span>
          <span className="font-mono text-[11px] text-[#C5A059]">Branch: ui-experiment</span>
        </div>
      </footer>
    </div>
  );
}
