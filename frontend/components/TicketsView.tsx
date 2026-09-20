"use client";

import React, { useState, useMemo } from "react";
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Wrench,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Filter,
  Eye,
  EyeOff,
  Check,
  X,
  FileText,
  SlidersHorizontal,
  TrendingDown,
} from "lucide-react";
import { Ticket } from "./types";
import { EvidencePanel } from "./EvidencePanel";

interface TicketsViewProps {
  tickets: Ticket[];
  onStatusChange: (
    ticketId: string,
    newStatus: "open" | "dispatched" | "resolved",
    resolutionNote?: string
  ) => Promise<void>;
  loading: boolean;
}

const SEVERITY_ORDER: Record<string, number> = {
  critical: 1,
  high: 2,
  medium: 3,
  low: 4,
};

const ZONE_LABELS: Record<string, string> = {
  T2_Restroom_A: "Restroom A (Departure)",
  T2_Restroom_B: "Restroom B (Arrival)",
  T2_Family_Room: "Family Room",
  T2_Staff_WC: "Staff WC",
};

const QUICK_NOTES = [
  "Valve replaced",
  "False alarm — sensor recalibrated",
  "Supply fitting tightened",
  "Flapper seal cleaned and tested",
];

export function TicketsView({ tickets, onStatusChange, loading }: TicketsViewProps) {
  // Filter States
  const [selectedZone, setSelectedZone] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [showResolved, setShowResolved] = useState<boolean>(false);

  // Modal State for Resolution Note
  const [resolvingTicket, setResolvingTicket] = useState<Ticket | null>(null);
  const [resolutionNote, setResolutionNote] = useState<string>("");
  const [isSubmittingResolution, setIsSubmittingResolution] = useState(false);

  // Evidence panel expansion state (Feature 4 Explainability)
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});
  const toggleEvidence = (ticketId: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [ticketId]: !prev[ticketId],
    }));
  };

  // ── Sorting & Partitioning ──────────────────────────────────────────────────
  // Active: status is 'open' or 'dispatched'
  // Resolved: status is 'resolved'
  const { activeTickets, resolvedTickets } = useMemo(() => {
    // 1. Filter by zone and anomaly type
    const filtered = tickets.filter((t) => {
      if (selectedZone !== "all" && t.zone_id !== selectedZone) return false;
      if (selectedType !== "all" && t.anomaly_type !== selectedType) return false;
      return true;
    });

    const active: Ticket[] = [];
    const resolved: Ticket[] = [];

    for (const t of filtered) {
      if (t.status === "resolved") {
        resolved.push(t);
      } else {
        active.push(t);
      }
    }

    // 2. Sort Active: Severity first (Critical -> High -> Medium -> Low),
    // then most recently flagged first (timestamp_flagged DESC)
    active.sort((a, b) => {
      const rankA = SEVERITY_ORDER[a.severity_label.toLowerCase()] || 99;
      const rankB = SEVERITY_ORDER[b.severity_label.toLowerCase()] || 99;
      if (rankA !== rankB) return rankA - rankB;
      return new Date(b.timestamp_flagged).getTime() - new Date(a.timestamp_flagged).getTime();
    });

    // Sort Resolved: Most recently flagged first
    resolved.sort((a, b) => new Date(b.timestamp_flagged).getTime() - new Date(a.timestamp_flagged).getTime());

    return { activeTickets: active, resolvedTickets: resolved };
  }, [tickets, selectedZone, selectedType]);

  // Handle status button click
  const handleStatusClick = (ticket: Ticket, targetStatus: "open" | "dispatched" | "resolved") => {
    if (ticket.status === targetStatus) return;

    if (targetStatus === "resolved") {
      // Open resolution note modal
      setResolvingTicket(ticket);
      setResolutionNote(ticket.resolution_note || "");
    } else {
      // Immediate update
      onStatusChange(ticket.ticket_id, targetStatus);
    }
  };

  // Submit Resolution from Modal
  const handleConfirmResolution = async () => {
    if (!resolvingTicket) return;
    setIsSubmittingResolution(true);
    try {
      await onStatusChange(resolvingTicket.ticket_id, "resolved", resolutionNote.trim());
      setResolvingTicket(null);
      setResolutionNote("");
    } finally {
      setIsSubmittingResolution(false);
    }
  };

  const getSeverityBadge = (label: string, score: number) => {
    switch (label.toLowerCase()) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold bg-[#F04438]/15 text-[#F04438] border border-[#F04438]/35">
            <AlertTriangle className="h-3 w-3" /> Critical ({score.toFixed(0)})
          </span>
        );
      case "high":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold bg-[#F38744]/15 text-[#F38744] border border-[#F38744]/35">
            <AlertCircle className="h-3 w-3" /> High ({score.toFixed(0)})
          </span>
        );
      case "medium":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold bg-[#EAAA08]/15 text-[#EAAA08] border border-[#EAAA08]/35">
            Medium ({score.toFixed(0)})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold bg-[#717BBC]/15 text-[#717BBC] border border-[#717BBC]/35">
            Low ({score.toFixed(0)})
          </span>
        );
    }
  };

  const getAnomalyTypeBadge = (type: string) => {
    const formatted = type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-[#1A2332] text-[#7C95B6] border border-[#2D3B4E]">
        {formatted}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* ── Top Filtering & Controls Toolbar ─────────────────────────────────── */}
      <div className="bg-[#0F141D] rounded-md p-4.5 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          {/* Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5 text-xs text-[#8B949E]">
              <Filter className="h-3.5 w-3.5 text-[#D4A359]" />
              <span className="font-semibold uppercase tracking-wider text-[11px]">Filters:</span>
            </div>

            {/* Zone Filter */}
            <select
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="bg-[#0B0F14] border border-white/15 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#D4A359]"
            >
              <option value="all">All Zones</option>
              <option value="T2_Restroom_A">T2_Restroom_A (Departure)</option>
              <option value="T2_Restroom_B">T2_Restroom_B (Arrival)</option>
              <option value="T2_Family_Room">T2_Family_Room</option>
              <option value="T2_Staff_WC">T2_Staff_WC</option>
            </select>

            {/* Anomaly Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-[#0D1117] border border-white/15 text-white text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#C5A059]"
            >
              <option value="all">All Anomaly Types</option>
              <option value="sustained_leak">Sustained Leak</option>
              <option value="slow_drip">Slow Drip</option>
              <option value="hygiene_threshold">Hygiene Threshold</option>
              <option value="sensor_fault">Sensor Fault</option>
            </select>
          </div>

          {/* Resolved Section Visibility Toggle */}
          <button
            onClick={() => setShowResolved(!showResolved)}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              showResolved
                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                : "bg-[#0D1117] text-[#8B949E] hover:text-white border-white/10"
            }`}
          >
            {showResolved ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            <span>
              {showResolved ? "Hide Resolved Tickets" : `Show Resolved (${resolvedTickets.length})`}
            </span>
          </button>
        </div>
      </div>

      {/* ── ACTIVE TICKETS SECTION ───────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-white tracking-wide uppercase flex items-center gap-2">
              Active Tickets Queue
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#F0A202]/15 text-[#F0A202] border border-[#F0A202]/30">
              {activeTickets.length} active
            </span>
          </div>
          <span className="text-xs text-[#8B949E]">
            Sorted by: <strong className="text-white">Severity Rank</strong> (Critical → High → Med → Low), then most recent
          </span>
        </div>

        {activeTickets.length === 0 ? (
          <div className="bg-[#0F141D] rounded-md p-10 text-center text-xs text-[#8B949E]">
            No active tickets matching the selected filters. All anomalies resolved or suppressed.
          </div>
        ) : (
          <div className="space-y-3.5">
            {activeTickets.map((t) => {
              const stripeColor =
                t.severity_label === "Critical"
                  ? "#F04438"
                  : t.severity_label === "High"
                  ? "#F38744"
                  : t.severity_label === "Medium"
                  ? "#EAAA08"
                  : "#717BBC";

              return (
                <div
                  key={t.ticket_id}
                  className="bg-[#0F141D] rounded-md p-5 shadow-sm transition-all relative overflow-hidden"
                >
                  {/* Left severity indicator bar */}
                  <div
                    className="absolute left-0 top-0 bottom-0 w-1.5"
                    style={{ backgroundColor: stripeColor }}
                  />

                  {/* Header Row: Ticket ID, Severity, Anomaly Type, Zone, Fixture, Status Button Group */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
                    <div className="flex flex-wrap items-center gap-2.5">
                      {getSeverityBadge(t.severity_label, t.severity_score)}
                      <span className="font-mono text-xs font-bold text-white">{t.ticket_id}</span>
                      {getAnomalyTypeBadge(t.anomaly_type)}
                      <span className="text-xs text-[#8B949E]">
                        in <strong className="text-white">{t.zone_id.replace("T2_", "").replace("_", " ")}</strong> · <strong className="text-[#C9D1D9] font-mono">{t.fixture_id}</strong>
                      </span>
                    </div>

                    {/* Status Button Group: Open | Dispatched | Resolved */}
                    <div className="flex items-center bg-[#0B0F14] p-1 rounded-lg border border-white/[0.08] self-start sm:self-auto shrink-0">
                      <button
                        onClick={() => handleStatusClick(t, "open")}
                        className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                          t.status === "open"
                            ? "bg-[#1B222C] text-[#F38744] font-bold shadow-sm border border-[#F38744]/35"
                            : "text-[#8B949E] hover:text-white"
                        }`}
                      >
                        Open
                      </button>
                      <button
                        onClick={() => handleStatusClick(t, "dispatched")}
                        className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-all ${
                          t.status === "dispatched"
                            ? "bg-[#4D88C7]/20 text-[#4D88C7] font-bold border border-[#4D88C7]/35 shadow-sm"
                            : "text-[#8B949E] hover:text-white"
                        }`}
                      >
                        <Wrench className="h-3 w-3" />
                        Dispatched
                      </button>
                      <button
                        onClick={() => handleStatusClick(t, "resolved")}
                        className="flex items-center gap-1 px-3 py-1 rounded text-xs font-medium text-[#8B949E] hover:text-[#2EB88A] transition-all"
                      >
                        <Check className="h-3 w-3" />
                        Mark Resolved
                      </button>
                    </div>
                  </div>

                  {/* Telemetry Numbers Row */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 py-3 text-xs">
                    <div>
                      <span className="text-[#8B949E] block text-[10px] uppercase">Flagged At</span>
                      <span className="font-mono text-[#F0F6FC]">{t.timestamp_flagged_str}</span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block text-[10px] uppercase">Current Status</span>
                      <span className="font-semibold text-white capitalize flex items-center gap-1.5">
                        {t.status === "dispatched" ? (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-[#4D88C7] animate-ping" />
                            <span className="text-[#4D88C7]">Technician Dispatched</span>
                          </>
                        ) : (
                          <>
                            <span className="h-1.5 w-1.5 rounded-full bg-[#F38744]" />
                            <span className="text-[#F38744]">Open Incident</span>
                          </>
                        )}
                      </span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block text-[10px] uppercase">Estimated Water Loss</span>
                      <span className="font-mono text-white font-bold">{t.estimated_water_loss_liters?.toFixed(1)} L</span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block text-[10px] uppercase">Municipal Cost Impact</span>
                      <span className="font-mono text-white font-bold">₹{t.estimated_cost_impact?.toFixed(2)}</span>
                    </div>
                    <div>
                      <span className="text-[#8B949E] block text-[10px] uppercase">If Unresolved (24h)</span>
                      <span className="font-mono text-white font-bold">
                        {(t.sustainability?.projections?.["24h"]?.projected_loss_liters ?? Math.round(((t.evidence?.observed_flow_lpm ?? 0) * 1440) * 10) / 10).toLocaleString()} L
                      </span>
                      <span className="text-[10px] text-[#8B949E] block font-mono">
                        ₹{(t.sustainability?.projections?.["24h"]?.projected_cost_inr ?? Math.round(((t.evidence?.observed_flow_lpm ?? 0) * 1440 * 0.05) * 100) / 100).toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* AI Analysis Explanation Sub-card */}
                  {t.explanation && (
                    <div className="mt-2 pt-3 border-t border-white/[0.06] bg-[#0B0F14]/70 rounded-lg p-3 border border-white/[0.04]">
                      <div className="flex items-start gap-2.5">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-[#4D88C7]/15 text-[#4D88C7] border border-[#4D88C7]/30 shrink-0 mt-0.5">
                          <Sparkles className="h-2.5 w-2.5" /> AI Analysis
                        </span>
                        <p className="text-xs text-[#C9D1D9] leading-relaxed whitespace-normal break-words">
                          {t.explanation}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Feature 4: Explainable Anomaly Detection ("Why was this flagged?") */}
                  <div className="mt-3 pt-2.5 border-t border-white/[0.04] flex flex-wrap items-center justify-between gap-2">
                    <button
                      onClick={() => toggleEvidence(t.ticket_id)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium text-[#D4A359] bg-[#D4A359]/10 hover:bg-[#D4A359]/20 border border-[#D4A359]/30 transition-all cursor-pointer"
                    >
                      <SlidersHorizontal className="h-3.5 w-3.5" />
                      <span>{expandedEvidence[t.ticket_id] ? "Hide Evidence Breakdown" : "Why was this flagged?"}</span>
                      {expandedEvidence[t.ticket_id] ? (
                        <ChevronUp className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )}
                    </button>

                    {t.evidence && (
                      <div className="flex items-center gap-1.5 text-[11px] text-[#8B949E]">
                        <span>Evidence Strength:</span>
                        <strong
                          className={
                            t.evidence.evidence_strength_label === "Strong"
                              ? "text-[#2EB88A]"
                              : t.evidence.evidence_strength_label === "Moderate"
                              ? "text-[#EAAA08]"
                              : "text-[#717BBC]"
                          }
                        >
                          {t.evidence.evidence_strength_label}
                        </strong>
                      </div>
                    )}
                  </div>

                  {/* Expandable Evidence Breakdown Panel */}
                  {expandedEvidence[t.ticket_id] && t.evidence && (
                    <EvidencePanel evidence={t.evidence} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── RESOLVED TICKETS AUDIT SECTION ───────────────────────────────────── */}
      {showResolved && (
        <div className="space-y-4 pt-4 border-t border-white/[0.08]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-[#2EB88A]" />
              <h3 className="text-sm font-bold text-white tracking-wide uppercase">
                Resolved Tickets Audit Log
              </h3>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#2EB88A]/15 text-[#2EB88A] border border-[#2EB88A]/30">
                {resolvedTickets.length} resolved
              </span>
            </div>
            <span className="text-xs text-[#8B949E]">Historical resolutions &amp; audit notes</span>
          </div>

          {resolvedTickets.length === 0 ? (
            <div className="bg-[#0F141D] rounded-md p-8 text-center text-xs text-[#8B949E]">
              No resolved tickets recorded yet.
            </div>
          ) : (
            <div className="space-y-3">
              {resolvedTickets.map((t) => (
                <div
                  key={t.ticket_id}
                  className="bg-[#0F141D] rounded-md p-4.5 opacity-90 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2.5 border-b border-white/[0.04]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-[#2EB88A]/15 text-[#2EB88A] border border-[#2EB88A]/30">
                        <CheckCircle2 className="h-3 w-3" /> Resolved
                      </span>
                      <span className="font-mono text-xs font-semibold text-white">{t.ticket_id}</span>
                      <span className="text-xs text-[#8B949E]">
                        {t.fixture_id} · {t.zone_id.replace("T2_", "").replace("_", " ")}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[#8B949E] font-mono">{t.timestamp_flagged_str}</span>
                      {/* Reopen Action */}
                      <button
                        onClick={() => handleStatusClick(t, "open")}
                        className="text-xs px-2.5 py-1 rounded bg-[#0B0F14] hover:bg-white/10 text-[#8B949E] hover:text-white border border-white/10 transition-all"
                      >
                        Reopen
                      </button>
                    </div>
                  </div>

                  {/* Resolution Note Callout */}
                  <div className="mt-3 p-3 bg-[#2EB88A]/10 border border-[#2EB88A]/25 rounded-lg text-xs flex items-start gap-2.5">
                    <FileText className="h-4 w-4 text-[#2EB88A] shrink-0 mt-0.5" />
                    <div>
                      <span className="text-[11px] font-semibold text-[#2EB88A] block uppercase tracking-wider">
                        Resolution Audit Note:
                      </span>
                      <p className="text-[#C9D1D9] mt-0.5">
                        {t.resolution_note || "No resolution note provided."}
                      </p>
                    </div>
                  </div>

                  {/* Feature 2: Intervention Impact (Section 2.7) */}
                  {t.sustainability?.intervention_impact && (
                    <div className="mt-2.5 p-3 bg-[#0B0F14] border border-white/[0.08] rounded-lg text-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="inline-flex items-center gap-1.5 font-bold uppercase tracking-wider text-[#F0F6FC] text-[11px]">
                          <span className="p-1 rounded bg-[#2EB88A]/15 text-[#2EB88A]">
                            <TrendingDown className="h-3 w-3" />
                          </span>
                          Intervention Impact
                        </span>
                        <span className="text-[10px] text-[#8B949E] font-mono">
                          Counterfactual 24h Baseline Model
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 py-1">
                        <div className="bg-[#0B0F14] p-2 rounded border border-white/[0.04]">
                          <span className="text-[10px] text-[#8B949E] block uppercase">Actual Water Lost</span>
                          <span className="font-mono font-bold text-[#F0F6FC] text-sm">
                            {t.sustainability.intervention_impact.actual_loss_liters.toFixed(1)} L
                          </span>
                        </div>
                        <div className="bg-[#0B0F14] p-2 rounded border border-white/[0.04]">
                          <span className="text-[10px] text-[#8B949E] block uppercase font-medium">Estimated Water Saved</span>
                          <span className="font-mono font-bold text-[#F0F6FC] text-sm">
                            +{t.sustainability.intervention_impact.estimated_water_saved_liters.toFixed(1)} L
                          </span>
                        </div>
                        <div className="bg-[#0B0F14] p-2 rounded border border-white/[0.04]">
                          <span className="text-[10px] text-[#8B949E] block uppercase font-medium">Estimated Avoided Cost</span>
                          <span className="font-mono font-bold text-[#F0F6FC] text-sm">
                            ₹{t.sustainability.intervention_impact.avoided_cost_inr.toFixed(2)}
                          </span>
                        </div>
                      </div>

                      <p className="text-[10px] text-[#8B949E] italic">
                        Prompt technician resolution prevented an estimated additional{" "}
                        {t.sustainability.intervention_impact.estimated_water_saved_liters.toFixed(1)} Litres from escaping during
                        the standard 24-hour unassisted inspection cycle.
                      </p>
                    </div>
                  )}

                  {/* AI Explanation preserved */}
                  {t.explanation && (
                    <div className="mt-2 text-xs text-[#8B949E] italic pl-2 border-l-2 border-white/10">
                      Incident Summary: {t.explanation}
                    </div>
                  )}

                  {/* Feature 4: Explainable Anomaly Detection ("Why was this flagged?") */}
                  <div className="mt-3 pt-2.5 border-t border-white/[0.04] flex flex-wrap items-center justify-between gap-2">
                    <button
                      onClick={() => toggleEvidence(t.ticket_id)}
                      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-[#D4A359] bg-[#D4A359]/10 hover:bg-[#D4A359]/20 border border-[#D4A359]/30 transition-all cursor-pointer"
                    >
                      <SlidersHorizontal className="h-3 w-3" />
                      <span>{expandedEvidence[t.ticket_id] ? "Hide Evidence" : "Why was this flagged?"}</span>
                      {expandedEvidence[t.ticket_id] ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      )}
                    </button>

                    {t.evidence && (
                      <div className="flex items-center gap-1.5 text-[11px] text-[#8B949E]">
                        <span>Evidence Strength:</span>
                        <strong
                          className={
                            t.evidence.evidence_strength_label === "Strong"
                              ? "text-[#2EB88A]"
                              : t.evidence.evidence_strength_label === "Moderate"
                              ? "text-[#EAAA08]"
                              : "text-[#717BBC]"
                          }
                        >
                          {t.evidence.evidence_strength_label}
                        </strong>
                      </div>
                    )}
                  </div>

                  {/* Expandable Evidence Breakdown Panel */}
                  {expandedEvidence[t.ticket_id] && t.evidence && (
                    <EvidencePanel evidence={t.evidence} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── RESOLUTION NOTE MODAL DIALOG ────────────────────────────────────── */}
      {resolvingTicket && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0F141D] rounded-md max-w-lg w-full p-6 shadow-2xl space-y-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-2">
                <div className="h-7 w-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Resolve Anomaly Ticket</h3>
                  <p className="text-xs font-mono text-[#8B949E]">{resolvingTicket.ticket_id}</p>
                </div>
              </div>
              <button
                onClick={() => setResolvingTicket(null)}
                className="p-1 rounded text-[#8B949E] hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Ticket Snapshot info */}
            <div className="bg-[#12161A] p-3 rounded-lg text-xs space-y-1 text-[#8B949E] border border-white/[0.04]">
              <div>
                Target: <strong className="text-white">{resolvingTicket.fixture_id}</strong> in{" "}
                <strong className="text-white">{resolvingTicket.zone_id.replace("T2_", "").replace("_", " ")}</strong>
              </div>
              <div>
                Anomaly: <span className="text-[#8FA3BB] font-medium">{resolvingTicket.anomaly_type.replace(/_/g, " ")}</span> · Severity:{" "}
                <strong className="text-white">{resolvingTicket.severity_label}</strong>
              </div>
            </div>

            {/* Prompt for Short Resolution Note */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-white block">
                Resolution Note <span className="text-[#8B949E] font-normal">(required audit trail)</span>
              </label>
              <textarea
                rows={3}
                placeholder="e.g. Valve replaced, flapper seal adjusted, sensor recalibrated..."
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                className="w-full bg-[#0D1117] border border-white/15 rounded-lg p-3 text-xs text-white placeholder-[#8B949E] focus:outline-none focus:border-emerald-400 transition-all"
                autoFocus
              />

              {/* Quick Suggestion Chips */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {QUICK_NOTES.map((note) => (
                  <button
                    key={note}
                    type="button"
                    onClick={() => setResolutionNote(note)}
                    className="text-[11px] px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.1] text-[#8B949E] hover:text-white border border-white/[0.08] transition-all"
                  >
                    + {note}
                  </button>
                ))}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                type="button"
                onClick={() => setResolvingTicket(null)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-[#8B949E] hover:text-white bg-transparent hover:bg-white/5 transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmittingResolution}
                onClick={handleConfirmResolution}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-emerald-500 hover:bg-emerald-600 text-black shadow-lg transition-all disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                <span>Confirm &amp; Resolve Ticket</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
