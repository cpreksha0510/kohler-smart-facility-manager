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

const DATE_PRESETS: { id: string; label: string; shortLabel: string }[] = [
  { id: "all", label: "Full 7 Days", shortLabel: "All 7D" },
  { id: "last24h", label: "Last 24 Hours", shortLabel: "Last 24h" },
  { id: "last3d", label: "Last 3 Days", shortLabel: "Last 3d" },
  { id: "day1", label: "Day 1 (Jan 15)", shortLabel: "Day 1" },
  { id: "day2", label: "Day 2 (Jan 16)", shortLabel: "Day 2" },
  { id: "day3", label: "Day 3 (Jan 17)", shortLabel: "Day 3" },
  { id: "day4", label: "Day 4 (Jan 18)", shortLabel: "Day 4" },
  { id: "day5", label: "Day 5 (Jan 19)", shortLabel: "Day 5" },
  { id: "day6", label: "Day 6 (Jan 20)", shortLabel: "Day 6" },
  { id: "day7", label: "Day 7 (Jan 21)", shortLabel: "Day 7" },
];

const isTimestampInRange = (tsStr: string, range: string) => {
  if (range === "all") return true;
  if (range === "last24h") return tsStr.startsWith("2024-01-21");
  if (range === "last3d") {
    return (
      tsStr.startsWith("2024-01-19") ||
      tsStr.startsWith("2024-01-20") ||
      tsStr.startsWith("2024-01-21")
    );
  }
  if (range === "day1") return tsStr.startsWith("2024-01-15");
  if (range === "day2") return tsStr.startsWith("2024-01-16");
  if (range === "day3") return tsStr.startsWith("2024-01-17");
  if (range === "day4") return tsStr.startsWith("2024-01-18");
  if (range === "day5") return tsStr.startsWith("2024-01-19");
  if (range === "day6") return tsStr.startsWith("2024-01-20");
  if (range === "day7") return tsStr.startsWith("2024-01-21");
  return true;
};

export function FlowRateChart({
  readings,
  zoneTotals,
  loading,
  isReplay = false,
  replayCutoffDate,
}: FlowRateChartProps) {
  const [chartMode, setChartMode] = useState<"zone_total" | "per_fixture">("zone_total");
  const [dateRange, setDateRange] = useState<string>("all");
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
        if (!isReplay && !isTimestampInRange(item.timestamp_str, dateRange)) continue;
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
        if (!isReplay && !isTimestampInRange(item.timestamp_str, dateRange)) continue;
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
  }, [chartMode, zoneTotals, readings, selectedZones, isReplay, replayCutoffDate, dateRange]);

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
    <div className="bg-[#101010] rounded-md p-5 shadow-sm">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-white tracking-wide uppercase">
              Flow Rate Telemetry (L/min)
            </h2>
            <span className="text-[11px] text-[#8B949E]">
              {isReplay
                ? "Replay Telemetry (Full 7-day timeline)"
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
              ? "Full 7-Day simulated timeline — scrub or press Play to stream flow telemetry across the complete canvas"
              : "7-Day continuous sensor stream downsampled at 5-minute intervals"}
          </p>
        </div>

        {/* View Mode Radio & Zone Chips */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center bg-[#080808] p-1 rounded-md">
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

      {/* Date Range Selector (Full Dataset View only) */}
      {!isReplay && (
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3 p-2.5 rounded-md bg-[#080B0F]">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-medium text-[#8B949E] uppercase tracking-wider">Date Range:</span>
            <div className="flex items-center bg-[#10151E] p-0.5 rounded-md">
              {[
                { id: "all", label: "Full 7 Days" },
                { id: "last24h", label: "Last 24 Hours" },
                { id: "last3d", label: "Last 3 Days" },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => setDateRange(p.id)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                    dateRange === p.id
                      ? "bg-[#1B222C] text-[#D4A359] font-semibold border border-[#D4A359]/30 shadow-sm"
                      : "text-[#8B949E] hover:text-white"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <div className="h-4 w-px bg-white/10 mx-1 hidden sm:block" />

            <div className="flex items-center bg-[#10151E] p-0.5 rounded-md overflow-x-auto">
              <span className="text-[10px] text-[#8B949E] px-2 font-medium">Day:</span>
              {[1, 2, 3, 4, 5, 6, 7].map((d) => {
                const id = `day${d}`;
                const dateLabel = `Jan ${14 + d}`;
                return (
                  <button
                    key={id}
                    onClick={() => setDateRange(id)}
                    title={`${dateLabel} (Day ${d})`}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                      dateRange === id
                        ? "bg-[#1B222C] text-[#5B8DEF] font-bold border border-[#5B8DEF]/30 shadow-sm"
                        : "text-[#8B949E] hover:text-white"
                    }`}
                  >
                    D{d} <span className="text-[9px] opacity-70">({14 + d}th)</span>
                  </button>
                );
              })}
            </div>
          </div>

          <span className="text-[11px] text-[#8B949E]">
            Window: <strong className="text-white font-medium">
              {DATE_PRESETS.find((p) => p.id === dateRange)?.label || "Full 7 Days"}
            </strong> ({chartData.length} pts)
          </span>
        </div>
      )}

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
            Loading 7-day flow telemetry...
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
