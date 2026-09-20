"use client";

import React, { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Reading } from "./types";

interface FlowRateChartProps {
  readings: Reading[];
  zoneTotals: { timestamp_str: string; zone_id: string; flow_rate_lpm: number }[];
  loading: boolean;
  isReplay?: boolean;
  replayCutoffDate?: Date;
}

const ZONE_COLORS: Record<string, string> = {
  T2_Restroom_A: "#5B8DEF",
  T2_Restroom_B: "#3EA882",
  T2_Family_Room: "#E09F3E",
  T2_Staff_WC: "#9D7FE3",
};

const ZONE_LABELS: Record<string, string> = {
  T2_Restroom_A: "Restroom A (Departure)",
  T2_Restroom_B: "Restroom B (Arrival)",
  T2_Family_Room: "Family Room",
  T2_Staff_WC: "Staff WC",
};

export function FlowRateChart({
  readings,
  zoneTotals,
  loading,
  isReplay = false,
  replayCutoffDate,
}: FlowRateChartProps) {
  const [chartMode, setChartMode] = useState<"zone_total" | "per_fixture">("zone_total");
  const [selectedZones, setSelectedZones] = useState<string[]>([
    "T2_Restroom_A",
    "T2_Restroom_B",
    "T2_Family_Room",
    "T2_Staff_WC",
  ]);

  const toggleZone = (zoneId: string) => {
    setSelectedZones((prev) => {
      if (prev.includes(zoneId)) {
        if (prev.length === 1) return prev; // keep at least 1
        return prev.filter((z) => z !== zoneId);
      } else {
        return [...prev, zoneId];
      }
    });
  };

  // Transform data for Recharts (keyed by timestamp)
  const chartData = useMemo(() => {
    if (chartMode === "zone_total") {
      // Group zoneTotals into { timestamp: "...", "T2_Restroom_A": 3.4, ... }
      const timeMap = new Map<string, any>();
      for (const item of zoneTotals) {
        if (!selectedZones.includes(item.zone_id)) continue;
        if (!timeMap.has(item.timestamp_str)) {
          timeMap.set(item.timestamp_str, { timestamp: item.timestamp_str });
        }
        const row = timeMap.get(item.timestamp_str);
        if (isReplay && replayCutoffDate && new Date(item.timestamp_str) > replayCutoffDate) {
          row[item.zone_id] = null;
        } else {
          row[item.zone_id] = Number(item.flow_rate_lpm.toFixed(2));
        }
      }
      return Array.from(timeMap.values());
    } else {
      // Per fixture
      const timeMap = new Map<string, any>();
      for (const item of readings) {
        if (!selectedZones.includes(item.zone_id)) continue;
        const fid = item.fixture_id || "Unknown";
        if (!timeMap.has(item.timestamp_str)) {
          timeMap.set(item.timestamp_str, { timestamp: item.timestamp_str });
        }
        const row = timeMap.get(item.timestamp_str);
        if (isReplay && replayCutoffDate && new Date(item.timestamp_str) > replayCutoffDate) {
          row[fid] = null;
        } else {
          row[fid] = Number(item.flow_rate_lpm.toFixed(2));
        }
      }
      return Array.from(timeMap.values());
    }
  }, [chartMode, zoneTotals, readings, selectedZones, isReplay, replayCutoffDate]);

  // Fixtures list if in per_fixture mode
  const fixtureKeys = useMemo(() => {
    if (chartMode !== "per_fixture") return [];
    const set = new Set<string>();
    for (const r of readings) {
      if (r.fixture_id && selectedZones.includes(r.zone_id)) {
        set.add(r.fixture_id);
      }
    }
    return Array.from(set).sort();
  }, [chartMode, readings, selectedZones]);

  // Dash style helper
  const getDash = (fid: string) => {
    const l = fid.toLowerCase();
    if (l.startsWith("toilet")) return "4 4";
    if (l.startsWith("urinal")) return "2 2";
    return undefined; // solid for sink
  };

  const getFixtureColor = (fid: string) => {
    // Match fixture to its zone color
    const sample = readings.find((r) => r.fixture_id === fid);
    return sample ? ZONE_COLORS[sample.zone_id] || "#5B8DEF" : "#5B8DEF";
  };

  return (
    <div className="bg-[#141A22] border border-white/[0.08] rounded-xl p-5 shadow-sm">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-white tracking-wide uppercase">
              Flow Rate Telemetry (L/min)
            </h2>
            <span className="text-[11px] text-[#8B949E]">
              {isReplay
                ? "Replay Telemetry (Full 48-hour timeline)"
                : chartMode === "zone_total"
                ? "4 Zones Aggregated"
                : "Per-Fixture Breakdown"}
            </span>
            {isReplay && (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#D4A359]/15 text-[#D4A359] border border-[#D4A359]/30">
                Replay Scrubber
              </span>
            )}
          </div>
          <p className="text-xs text-[#8B949E] mt-0.5">
            {isReplay
              ? "Full 48-Hour simulated timeline — scrub or press Play to stream flow telemetry across the complete canvas"
              : "48-Hour continuous sensor stream downsampled at 5-minute intervals"}
          </p>
        </div>

        {/* View Mode Radio & Zone Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center bg-[#0B0F14] p-1 rounded-lg border border-white/[0.08]">
            <button
              onClick={() => setChartMode("zone_total")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                chartMode === "zone_total"
                  ? "bg-[#1B222C] text-white font-semibold border border-white/10 shadow-sm"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              Zone Totals
            </button>
            <button
              onClick={() => setChartMode("per_fixture")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                chartMode === "per_fixture"
                  ? "bg-[#1B222C] text-white font-semibold border border-white/10 shadow-sm"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              Per Fixture
            </button>
          </div>
        </div>
      </div>

      {/* Zone selection filter chips */}
      <div className="flex flex-wrap items-center gap-2 mb-4 pb-3 border-b border-white/[0.06]">
        <span className="text-[11px] text-[#8B949E] uppercase tracking-wider mr-1">Filter Zones:</span>
        {Object.entries(ZONE_COLORS).map(([zid, color]) => {
          const active = selectedZones.includes(zid);
          return (
            <button
              key={zid}
              onClick={() => toggleZone(zid)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                active
                  ? "bg-white/[0.05] text-white"
                  : "bg-transparent text-[#8B949E]/50 border-white/[0.04] opacity-50"
              }`}
              style={{ borderColor: active ? `${color}55` : undefined }}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: active ? color : "#484F58" }}
              />
              <span>{ZONE_LABELS[zid]}</span>
            </button>
          );
        })}
      </div>

      {/* Chart Canvas */}
      <div className="h-[320px] w-full">
        {loading || chartData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-[#8B949E]">
            Loading 48-hour flow telemetry...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="timestamp"
                tick={{ fill: "#8B949E", fontSize: 10 }}
                tickFormatter={(val) => {
                  // val: "2024-01-15 04:00" -> "Jan 15 04:00"
                  const parts = val.split(" ");
                  if (parts.length === 2) {
                    const dateParts = parts[0].split("-");
                    return `${dateParts[1]}/${dateParts[2]} ${parts[1]}`;
                  }
                  return val;
                }}
                stroke="rgba(255,255,255,0.1)"
                minTickGap={40}
              />
              <YAxis
                tick={{ fill: "#8B949E", fontSize: 10 }}
                stroke="rgba(255,255,255,0.1)"
                unit=" L/m"
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#161B22",
                  borderColor: "rgba(255,255,255,0.15)",
                  borderRadius: "8px",
                  fontSize: "11px",
                  color: "#F0F6FC",
                }}
                labelStyle={{ color: "#C5A059", fontWeight: 600, marginBottom: "4px" }}
              />
              {chartMode === "zone_total" ? (
                selectedZones.map((zid) => (
                  <Line
                    key={zid}
                    type="monotone"
                    dataKey={zid}
                    name={ZONE_LABELS[zid]}
                    stroke={ZONE_COLORS[zid]}
                    strokeWidth={1.8}
                    connectNulls={false}
                    isAnimationActive={!isReplay}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                ))
              ) : (
                fixtureKeys.map((fid) => (
                  <Line
                    key={fid}
                    type="monotone"
                    dataKey={fid}
                    name={fid}
                    stroke={getFixtureColor(fid)}
                    strokeWidth={fid === "Sink_01" ? 2.5 : 1.2}
                    strokeDasharray={getDash(fid)}
                    connectNulls={false}
                    isAnimationActive={!isReplay}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                ))
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Legend guide for line styles */}
      {chartMode === "per_fixture" && (
        <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-[#8B949E]">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-0.5 bg-[#6B8CAE] inline-block" /> Solid: Sinks
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-0.5 border-b border-dashed border-[#6B8CAE] inline-block" /> Dashed: Toilets
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-0.5 border-b border-dotted border-[#6B8CAE] inline-block" /> Dotted: Urinals
            </span>
          </div>
          <span className="text-[#C5A059] font-medium">Sink_01 highlighted (Hero Leak)</span>
        </div>
      )}
    </div>
  );
}
