"use client";

import React, { useState, useMemo } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Clock,
  Droplets,
  Filter,
  Info,
  Layers,
  Minus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wrench,
  X,
} from "lucide-react";
import {
  FixtureHealthRecord,
  FacilityHealthSummary,
  Ticket,
} from "./types";

interface FixtureHealthViewProps {
  records: FixtureHealthRecord[];
  summary: FacilityHealthSummary | null;
  loading: boolean;
  onOpenTicket?: (ticketId: string) => void;
}

const ZONE_NAMES: Record<string, string> = {
  T2_Restroom_A: "Departure Restroom A",
  T2_Restroom_B: "Arrival Restroom B",
  T2_Family_Room: "Family Restroom",
  T2_Staff_WC: "Staff Operations WC",
};

const ZONE_BADGES: Record<string, { bg: string; text: string; border: string }> = {
  T2_Restroom_A: { bg: "bg-[#6B8CAE]/15", text: "text-[#6B8CAE]", border: "border-[#6B8CAE]/30" },
  T2_Restroom_B: { bg: "bg-[#789A8B]/15", text: "text-[#789A8B]", border: "border-[#789A8B]/30" },
  T2_Family_Room: { bg: "bg-[#B08D57]/15", text: "text-[#B08D57]", border: "border-[#B08D57]/30" },
  T2_Staff_WC: { bg: "bg-[#847E9C]/15", text: "text-[#847E9C]", border: "border-[#847E9C]/30" },
};

export function FixtureHealthView({
  records,
  summary,
  loading,
  onOpenTicket,
}: FixtureHealthViewProps) {
  const [selectedZone, setSelectedZone] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"risk_desc" | "health_asc" | "anomalies_desc" | "fixture_id">("risk_desc");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedFixture, setSelectedFixture] = useState<FixtureHealthRecord | null>(null);
  const [showFormulaInfo, setShowFormulaInfo] = useState<boolean>(false);

  // Filter & Sort
  const filteredRecords = useMemo(() => {
    return records
      .filter((r) => {
        if (selectedZone !== "all" && r.zone_id !== selectedZone) return false;
        if (selectedStatus !== "all" && r.status.toLowerCase() !== selectedStatus.toLowerCase()) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          return (
            r.fixture_id.toLowerCase().includes(q) ||
            (ZONE_NAMES[r.zone_id] || "").toLowerCase().includes(q) ||
            r.recommendation.toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "risk_desc") return b.risk_score - a.risk_score;
        if (sortBy === "health_asc") return a.health_score - b.health_score;
        if (sortBy === "anomalies_desc") return b.anomaly_count - a.anomaly_count;
        return a.fixture_id.localeCompare(b.fixture_id);
      });
  }, [records, selectedZone, selectedStatus, sortBy, searchQuery]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "High Risk":
        return {
          bg: "bg-[#F04438]/15",
          text: "text-[#F04438]",
          border: "border-[#F04438]/30",
          icon: ShieldAlert,
        };
      case "Degrading":
        return {
          bg: "bg-[#C87A58]/15",
          text: "text-[#C87A58]",
          border: "border-[#C87A58]/30",
          icon: AlertTriangle,
        };
      case "Watch":
        return {
          bg: "bg-[#D4A359]/15",
          text: "text-[#D4A359]",
          border: "border-[#D4A359]/30",
          icon: Info,
        };
      default:
        return {
          bg: "bg-[#2EB88A]/15",
          text: "text-[#2EB88A]",
          border: "border-[#2EB88A]/30",
          icon: ShieldCheck,
        };
    }
  };

  const getHealthBarColor = (score: number) => {
    if (score >= 80) return "bg-[#2EB88A]";
    if (score >= 60) return "bg-[#D4A359]";
    if (score >= 40) return "bg-[#C87A58]";
    return "bg-[#F04438]";
  };

  const getTrendBadge = (trend: string) => {
    if (trend === "Deteriorating") {
      return {
        label: "Deteriorating",
        text: "text-[#F04438]",
        bg: "bg-[#F04438]/10",
        border: "border-[#F04438]/25",
        icon: TrendingUp,
      };
    } else if (trend === "Improving") {
      return {
        label: "Improving",
        text: "text-[#2EB88A]",
        bg: "bg-[#2EB88A]/10",
        border: "border-[#2EB88A]/25",
        icon: TrendingDown,
      };
    }
    return {
      label: "Stable",
      text: "text-[#4D88C7]",
      bg: "bg-[#4D88C7]/10",
      border: "border-[#4D88C7]/25",
      icon: Minus,
    };
  };

  return (
    <div className="space-y-8">
      {/* 1. Header Banner & Intro */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <div className="p-2 rounded-lg bg-[#4D88C7]/15 border border-[#4D88C7]/30 text-[#4D88C7]">
              <Activity className="h-5 w-5" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Predictive Fixture Health
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-white/[0.06] text-[#8B949E] border border-white/[0.08]">
                Section 1 Model
              </span>
            </h2>
          </div>
          <p className="text-sm text-[#8B949E] max-w-3xl">
            Continuous mechanical reliability monitoring across 17 airport smart fixtures. Scores are computed from a transparent 6-factor telemetry model with 100% data traceability.
          </p>
        </div>

        {/* Methodology Toggle */}
        <button
          onClick={() => setShowFormulaInfo(!showFormulaInfo)}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-[#0F141D] hover:bg-[#141B26] text-[#8B949E] hover:text-white transition-all self-start md:self-auto"
        >
          <Info className="h-3.5 w-3.5 text-[#D4A359]" />
          <span>{showFormulaInfo ? "Hide Formula Rationale" : "View Health Formula"}</span>
        </button>
      </div>

      {/* 2. Expandable Formula Rationale Box */}
      {showFormulaInfo && (
        <div className="bg-[#0F141D] rounded-md p-5 shadow-lg space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-[#D4A359]" />
              Transparent 6-Factor Health Formula (Section 1.3)
            </h4>
            <span className="text-xs font-mono text-[#D4A359]">health_score = 100 - risk</span>
          </div>
          <p className="text-xs text-[#8B949E] leading-relaxed">
            Per the PRD specification, predictive health operates on a deterministic, fully explainable model rather than an opaque ML black-box. Every fixture is scored between 0 (critical failure risk) and 100 (optimal health) using six normalized telemetry factors:
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Freq. (30%)</span>
              <span className="font-semibold text-white">Anomaly Count</span>
            </div>
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Recurrence (20%)</span>
              <span className="font-semibold text-white">Multi-Session</span>
            </div>
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Drift (20%)</span>
              <span className="font-semibold text-white">Flow Variance</span>
            </div>
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Slow Drip (15%)</span>
              <span className="font-semibold text-white">Overnight Creep</span>
            </div>
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Sensor (10%)</span>
              <span className="font-semibold text-white">Signal Status</span>
            </div>
            <div className="p-2.5 rounded-md bg-[#0B0F14]">
              <span className="text-[#8B949E] block text-[11px]">Unresolved (5%)</span>
              <span className="font-semibold text-white">Open Tickets</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Top-Level KPI Metric Cards (Clean neutral numbers per prompt 9) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Facility Health Average */}
        <div className="bg-[#0F141D] rounded-md p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
              Facility Health Index
            </span>
            <div className="p-2 rounded-md bg-[#4D88C7]/15 border border-[#4D88C7]/30 text-[#4D88C7]">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {summary ? `${summary.average_health_score}` : "—"}
            </span>
            <span className="text-xs text-[#8B949E]">/ 100</span>
          </div>
          <div className="mt-2 text-xs text-[#8B949E] flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[#2EB88A]" />
            <span>Average across 17 monitored fixtures</span>
          </div>
        </div>

        {/* Card 2: High Risk / Degrading Fixtures */}
        <div className="bg-[#0F141D] rounded-md p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
              At-Risk Fixtures
            </span>
            <div className="p-2 rounded-md bg-[#F04438]/15 border border-[#F04438]/30 text-[#F04438]">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {summary ? summary.high_risk_count + summary.degrading_count : 0}
            </span>
            <span className="text-xs text-[#8B949E]">requiring attention</span>
          </div>
          <div className="mt-2 text-xs text-[#8B949E]">
            {summary?.high_risk_count || 0} High Risk · {summary?.degrading_count || 0} Degrading
          </div>
        </div>

        {/* Card 3: Deteriorating Trend */}
        <div className="bg-[#0F141D] rounded-md p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
              Deteriorating Trend
            </span>
            <div className="p-2 rounded-md bg-[#C87A58]/15 border border-[#C87A58]/30 text-[#C87A58]">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {summary ? summary.deteriorating_count : 0}
            </span>
            <span className="text-xs text-[#8B949E]">accelerating anomalies</span>
          </div>
          <div className="mt-2 text-xs text-[#8B949E]">
            Recent incident rate exceeds Day 1 baseline
          </div>
        </div>

        {/* Card 4: Healthy / Optimal */}
        <div className="bg-[#0F141D] rounded-md p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
              Optimal Reliability
            </span>
            <div className="p-2 rounded-md bg-[#2EB88A]/15 border border-[#2EB88A]/30 text-[#2EB88A]">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              {summary ? summary.healthy_count : 0}
            </span>
            <span className="text-xs text-[#8B949E]">/ {summary?.total_fixtures || 17} healthy</span>
          </div>
          <div className="mt-2 text-xs text-[#8B949E]">
            {summary ? Math.round((summary.healthy_count / (summary.total_fixtures || 1)) * 100) : 0}% fleet operating normally
          </div>
        </div>
      </div>

      {/* 4. Filter & Controls Bar */}
      <div className="bg-[#0F141D] rounded-md p-4 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Zone Filters */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-[#8B949E] mr-1 flex items-center gap-1">
            <Filter className="h-3 w-3" /> Zone:
          </span>
          {[
            { id: "all", label: "All Zones" },
            { id: "T2_Restroom_A", label: "Restroom A" },
            { id: "T2_Restroom_B", label: "Restroom B" },
            { id: "T2_Family_Room", label: "Family Room" },
            { id: "T2_Staff_WC", label: "Staff WC" },
          ].map((z) => (
            <button
              key={z.id}
              onClick={() => setSelectedZone(z.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                selectedZone === z.id
                  ? "bg-[#1B222C] text-white border border-[#4D88C7]/30 font-semibold"
                  : "text-[#8B949E] hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              {z.label}
            </button>
          ))}
        </div>

        {/* Search & Sort Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-[#0B0F14] text-xs text-[#F0F6FC] px-2.5 py-1.5 rounded-lg border border-white/[0.08] focus:outline-none focus:border-[#4D88C7]/50"
          >
            <option value="all">All Statuses</option>
            <option value="High Risk">High Risk</option>
            <option value="Degrading">Degrading</option>
            <option value="Watch">Watch</option>
            <option value="Healthy">Healthy</option>
          </select>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="bg-[#0B0F14] text-xs text-[#F0F6FC] px-2.5 py-1.5 rounded-lg border border-white/[0.08] focus:outline-none focus:border-[#4D88C7]/50"
          >
            <option value="risk_desc">Sort: Highest Risk</option>
            <option value="health_asc">Sort: Lowest Health</option>
            <option value="anomalies_desc">Sort: Most Anomalies</option>
            <option value="fixture_id">Sort: Fixture ID</option>
          </select>
        </div>
      </div>

      {/* 5. Fixture Health Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredRecords.map((fixture) => {
          const statusMeta = getStatusBadge(fixture.status);
          const StatusIcon = statusMeta.icon;
          const trendMeta = getTrendBadge(fixture.trend);
          const TrendIcon = trendMeta.icon;
          const zoneBadge = ZONE_BADGES[fixture.zone_id] || {
            bg: "bg-white/5",
            text: "text-white/70",
            border: "border-white/10",
          };

          return (
            <div
              key={fixture.fixture_id}
              onClick={() => setSelectedFixture(fixture)}
              className="group bg-[#0F141D] hover:bg-[#141B26] rounded-md p-5 shadow-sm transition-all duration-200 cursor-pointer flex flex-col justify-between"
            >
              {/* Card Top */}
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-white group-hover:text-[#D4A359] transition-colors">
                        {fixture.fixture_id}
                      </h3>
                      <span className="text-[11px] font-medium uppercase px-2 py-0.5 rounded bg-white/[0.06] text-[#8B949E]">
                        {fixture.fixture_type}
                      </span>
                    </div>
                    <span
                      className={`inline-block mt-1 text-[11px] px-2 py-0.5 rounded border ${zoneBadge.bg} ${zoneBadge.text} ${zoneBadge.border}`}
                    >
                      {ZONE_NAMES[fixture.zone_id] || fixture.zone_id}
                    </span>
                  </div>

                  {/* Status Badge */}
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border ${statusMeta.bg} ${statusMeta.text} ${statusMeta.border}`}
                  >
                    <StatusIcon className="h-3.5 w-3.5" />
                    {fixture.status}
                  </span>
                </div>

                {/* Health Score Meter */}
                <div className="space-y-1.5 my-4">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#8B949E]">Health Score</span>
                    <span className="font-mono font-bold text-white">
                      {fixture.health_score.toFixed(1)} <span className="text-[#8B949E] text-[10px]">/ 100</span>
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-[#0B0F14] overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getHealthBarColor(
                        fixture.health_score
                      )}`}
                      style={{ width: `${Math.max(4, fixture.health_score)}%` }}
                    />
                  </div>
                </div>

                {/* Sub-Metrics: Reliability Trend & Classification */}
                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06] text-xs">
                  <div>
                    <span className="text-[#8B949E] block text-[11px]">Reliability Trend</span>
                    <span
                      className={`inline-flex items-center gap-1 text-[11px] font-semibold ${trendMeta.text}`}
                    >
                      <TrendIcon className="h-3 w-3" />
                      {trendMeta.label}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[#8B949E] block text-[11px]">Reliability Status</span>
                    <span className="font-semibold text-white">
                      {fixture.status}
                    </span>
                  </div>
                </div>

                {/* Incident History Summary */}
                <div className="mt-3 flex items-center justify-between text-xs text-[#8B949E] bg-[#0B0F14]/60 p-2.5 rounded-lg border border-white/[0.04]">
                  <span>Anomalies: <strong className="text-white">{fixture.anomaly_count}</strong></span>
                  <span>Slow Drips: <strong className="text-white">{fixture.slow_drip_count}</strong></span>
                  <span>Sensor Faults: <strong className="text-white">{fixture.sensor_fault_count}</strong></span>
                </div>

                {/* Recommendation Snippet */}
                <p className="mt-3 text-xs text-[#8B949E] line-clamp-2 italic">
                  "{fixture.recommendation}"
                </p>
              </div>

              {/* Card Footer Button */}
              <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-[#4D88C7] group-hover:text-white transition-colors">
                <span className="font-medium">Inspect Risk Factors</span>
                <ChevronRight className="h-4 w-4 transform group-hover:translate-x-0.5 transition-transform" />
              </div>
            </div>
          );
        })}
      </div>

      {/* 6. Fixture Detail Slide-Over Drawer */}
      {selectedFixture && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          {/* Backdrop */}
          <div
            onClick={() => setSelectedFixture(null)}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
          />

          <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-lg bg-[#0F141D] border-l border-white/10 shadow-2xl flex flex-col">
              {/* Drawer Header */}
              <div className="px-6 py-5 border-b border-white/[0.08] bg-[#10141A] flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-lg font-bold text-white">
                      {selectedFixture.fixture_id}
                    </h3>
                    <span className="text-xs uppercase px-2 py-0.5 rounded bg-white/[0.06] text-[#8B949E]">
                      {selectedFixture.fixture_type}
                    </span>
                  </div>
                  <p className="text-xs text-[#8B949E] mt-0.5">
                    {ZONE_NAMES[selectedFixture.zone_id] || selectedFixture.zone_id}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedFixture(null)}
                  className="p-1.5 rounded-lg text-[#8B949E] hover:text-white hover:bg-white/[0.08] transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Drawer Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Status & Health Gauge Banner */}
                <div className="bg-[#0B0F14] rounded-md p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs text-[#8B949E] block">Reliability Status</span>
                      <span
                        className={`inline-flex items-center gap-1.5 mt-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                          getStatusBadge(selectedFixture.status).bg
                        } ${getStatusBadge(selectedFixture.status).text} ${
                          getStatusBadge(selectedFixture.status).border
                        }`}
                      >
                        {selectedFixture.status}
                      </span>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-[#8B949E] block">Health Score</span>
                      <span className="text-2xl font-mono font-bold text-white">
                        {selectedFixture.health_score.toFixed(1)}
                        <span className="text-xs text-[#8B949E]"> / 100</span>
                      </span>
                    </div>
                  </div>

                  <div className="w-full h-2.5 rounded-full bg-[#1B222C] overflow-hidden">
                    <div
                      className={`h-full rounded-full ${getHealthBarColor(selectedFixture.health_score)}`}
                      style={{ width: `${Math.max(5, selectedFixture.health_score)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-[#8B949E] pt-1">
                    <span>Condition: <strong className="text-white">{selectedFixture.status}</strong></span>
                    <span>Operational Trend: <strong className="text-white">{selectedFixture.trend}</strong></span>
                  </div>
                </div>

                {/* Recommendation Box */}
                <div className="bg-[#D4A359]/10 border border-[#D4A359]/30 rounded-md p-4">
                  <div className="flex items-center gap-2 text-[#D4A359] text-xs font-semibold uppercase tracking-wider mb-1.5">
                    <Wrench className="h-4 w-4" />
                    Recommended Operational Action
                  </div>
                  <p className="text-xs text-[#F0F6FC] leading-relaxed">
                    {selectedFixture.recommendation}
                  </p>
                </div>

                {/* Transparent 6-Factor Risk Contribution Breakdown */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
                      Explainable Risk Components (Section 1.3)
                    </h4>
                    <span className="text-[11px] font-mono text-[#D4A359]">Formula Weights</span>
                  </div>

                  <div className="space-y-2.5">
                    {[
                      {
                        label: "Anomaly Frequency Score",
                        weight: "30%",
                        score: selectedFixture.risk_factors.anomaly_frequency_score,
                        contribution: (selectedFixture.risk_factors.anomaly_frequency_score * 0.3).toFixed(1),
                        desc: "Incident occurrences & peak severity",
                      },
                      {
                        label: "Recurrence Score",
                        weight: "20%",
                        score: selectedFixture.risk_factors.recurrence_score,
                        contribution: (selectedFixture.risk_factors.recurrence_score * 0.2).toFixed(1),
                        desc: "Repeated anomalies across multiple sessions",
                      },
                      {
                        label: "Flow Drift Score",
                        weight: "20%",
                        score: selectedFixture.risk_factors.flow_drift_score,
                        contribution: (selectedFixture.risk_factors.flow_drift_score * 0.2).toFixed(1),
                        desc: "Upward telemetry drift from baseline",
                      },
                      {
                        label: "Slow Drip Detection",
                        weight: "15%",
                        score: selectedFixture.risk_factors.slow_drip_score,
                        contribution: (selectedFixture.risk_factors.slow_drip_score * 0.15).toFixed(1),
                        desc: "Overnight idle micro-seepage flags",
                      },
                      {
                        label: "Sensor Telemetry Health",
                        weight: "10%",
                        score: selectedFixture.risk_factors.sensor_health_score,
                        contribution: (selectedFixture.risk_factors.sensor_health_score * 0.1).toFixed(1),
                        desc: "Fault or anomalous transducer readings",
                      },
                      {
                        label: "Unresolved Ticket Penalty",
                        weight: "5%",
                        score: selectedFixture.risk_factors.unresolved_score,
                        contribution: (selectedFixture.risk_factors.unresolved_score * 0.05).toFixed(1),
                        desc: "Active open vs resolved maintenance status",
                      },
                    ].map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-[#0B0F14] border border-white/[0.06] rounded-lg p-3 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white font-medium flex items-center gap-1.5">
                            {item.label}
                            <span className="text-[10px] text-[#8B949E] font-mono">({item.weight})</span>
                          </span>
                          <span className="font-mono text-xs text-[#D4A359]">
                            +{item.contribution} pts
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-[#1B222C] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#4D88C7]"
                            style={{ width: `${Math.max(2, item.score)}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-[#8B949E]">
                          <span>{item.desc}</span>
                          <span className="font-mono">{item.score.toFixed(1)} / 100</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Historical Incident Log */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-[#8B949E]">
                    Incident & Anomaly Log ({selectedFixture.anomaly_count})
                  </h4>

                  {selectedFixture.anomaly_count === 0 ? (
                    <div className="p-4 rounded-md bg-[#0B0F14] text-center text-xs text-[#8B949E]">
                      No anomalous tickets recorded. Fixture telemetry is stable.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="p-3 rounded-lg bg-[#0B0F14] border border-white/[0.06] text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-white">Historical Incidents</span>
                          <span className="text-[#8B949E] font-mono">{selectedFixture.anomaly_count} total</span>
                        </div>
                        <p className="text-[#8B949E]">
                          Slow Drip Count: <span className="text-white">{selectedFixture.slow_drip_count}</span> · Sensor Faults: <span className="text-white">{selectedFixture.sensor_fault_count}</span>
                        </p>
                        {selectedFixture.last_incident_at && (
                          <p className="text-[#8B949E] text-[11px] pt-1">
                            Last Incident: <span className="text-white font-mono">{selectedFixture.last_incident_at}</span>
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
