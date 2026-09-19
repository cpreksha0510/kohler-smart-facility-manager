"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Filter,
  SlidersHorizontal,
} from "lucide-react";
import { Ticket } from "./types";
import { EvidencePanel } from "./EvidencePanel";

interface TicketsTableProps {
  tickets: Ticket[];
  onStatusChange: (ticketId: string, newStatus: "open" | "dispatched" | "resolved") => Promise<void>;
  loading: boolean;
  onNavigateToTickets?: () => void;
}

export function TicketsTable({
  tickets,
  onStatusChange,
  loading,
  onNavigateToTickets,
}: TicketsTableProps) {
  const [filterTab, setFilterTab] = useState<"all" | "open" | "dispatched" | "resolved">("all");
  const [statusMenuOpen, setStatusMenuOpen] = useState<string | null>(null);
  const [updatingTicket, setUpdatingTicket] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});

  const toggleEvidence = (ticketId: string) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [ticketId]: !prev[ticketId],
    }));
  };

  const filteredTickets = tickets.filter((t) => {
    if (filterTab === "all") return true;
    return t.status === filterTab;
  });

  const handleSelectStatus = async (ticketId: string, status: "open" | "dispatched" | "resolved") => {
    setStatusMenuOpen(null);
    setUpdatingTicket(ticketId);
    try {
      await onStatusChange(ticketId, status);
    } finally {
      setUpdatingTicket(null);
    }
  };

  const getSeverityBadge = (label: string, score: number) => {
    switch (label.toLowerCase()) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#E4572E]/15 text-[#E4572E] border border-[#E4572E]/30">
            <AlertTriangle className="h-3 w-3" /> Critical ({score.toFixed(0)})
          </span>
        );
      case "high":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#F0A202]/15 text-[#F0A202] border border-[#F0A202]/30">
            <AlertCircle className="h-3 w-3" /> High ({score.toFixed(0)})
          </span>
        );
      case "medium":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#D9B44A]/15 text-[#D9B44A] border border-[#D9B44A]/30">
            Medium ({score.toFixed(0)})
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-white/10 text-[#8B949E] border border-white/10">
            Low ({score.toFixed(0)})
          </span>
        );
    }
  };

  const getStatusPill = (ticket: Ticket) => {
    const isUpdating = updatingTicket === ticket.ticket_id;
    let colorClass = "bg-white/[0.06] text-[#8B949E] border-white/[0.1]";
    let iconEl = <Clock className="h-3 w-3" />;
    let label = "Open";

    if (ticket.status === "dispatched") {
      colorClass = "bg-sky-500/15 text-sky-400 border-sky-500/30";
      iconEl = <Clock className="h-3 w-3 animate-spin" />;
      label = "Dispatched";
    } else if (ticket.status === "resolved") {
      colorClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
      iconEl = <CheckCircle2 className="h-3 w-3" />;
      label = "Resolved";
    }

    return (
      <div className="relative inline-block">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setStatusMenuOpen(statusMenuOpen === ticket.ticket_id ? null : ticket.ticket_id);
          }}
          disabled={isUpdating}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-all hover:ring-1 hover:ring-white/20 ${colorClass}`}
        >
          {iconEl}
          <span>{label}</span>
          <ChevronDown className="h-3 w-3 opacity-60 ml-0.5" />
        </button>

        {/* Status Dropdown Menu */}
        {statusMenuOpen === ticket.ticket_id && (
          <div className="absolute right-0 mt-1 w-36 rounded-lg bg-[#1F242C] border border-white/15 shadow-xl z-50 py-1 text-xs">
            <button
              onClick={() => handleSelectStatus(ticket.ticket_id, "open")}
              className="w-full text-left px-3 py-1.5 hover:bg-white/10 text-white flex items-center gap-2"
            >
              <span className="h-2 w-2 rounded-full bg-[#F0A202]" /> Open
            </button>
            <button
              onClick={() => handleSelectStatus(ticket.ticket_id, "dispatched")}
              className="w-full text-left px-3 py-1.5 hover:bg-white/10 text-white flex items-center gap-2"
            >
              <span className="h-2 w-2 rounded-full bg-sky-400" /> Dispatched
            </button>
            <button
              onClick={() => handleSelectStatus(ticket.ticket_id, "resolved")}
              className="w-full text-left px-3 py-1.5 hover:bg-white/10 text-white flex items-center gap-2"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-400" /> Resolved
            </button>
          </div>
        )}
      </div>
    );
  };

  const openCount = tickets.filter((t) => t.status === "open").length;
  const dispatchedCount = tickets.filter((t) => t.status === "dispatched").length;
  const resolvedCount = tickets.filter((t) => t.status === "resolved").length;

  return (
    <div className="bg-[#161B22] border border-white/[0.08] rounded-xl overflow-hidden shadow-sm">
      {/* Table Header & Filter Tabs */}
      <div className="px-5 py-4 border-b border-white/[0.08] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-white tracking-wide uppercase">
            Flagged Anomaly Tickets
          </h2>
          <p className="text-xs text-[#8B949E] mt-0.5">
            Deterministic 3-pass multi-signal detection with automated Google Gemini incident explainability
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center bg-[#0D1117] p-1 rounded-lg border border-white/[0.08]">
          <button
            onClick={() => setFilterTab("all")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${
              filterTab === "all" ? "bg-[#21262D] text-white" : "text-[#8B949E] hover:text-white"
            }`}
          >
            All ({tickets.length})
          </button>
          <button
            onClick={() => setFilterTab("open")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${
              filterTab === "open"
                ? "bg-[#21262D] text-[#F0A202] font-semibold"
                : "text-[#8B949E] hover:text-white"
            }`}
          >
            Open ({openCount})
          </button>
          <button
            onClick={() => setFilterTab("dispatched")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${
              filterTab === "dispatched"
                ? "bg-[#21262D] text-sky-400 font-semibold"
                : "text-[#8B949E] hover:text-white"
            }`}
          >
            Dispatched ({dispatchedCount})
          </button>
          <button
            onClick={() => setFilterTab("resolved")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all ${
              filterTab === "resolved"
                ? "bg-[#21262D] text-emerald-400 font-semibold"
                : "text-[#8B949E] hover:text-white"
            }`}
          >
            Resolved ({resolvedCount})
          </button>
        </div>
      </div>

      {/* Tickets Table Body */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#12161A] text-[#8B949E] border-b border-white/[0.08] uppercase text-[11px] tracking-wider">
              <th className="py-3 px-4 w-2 font-medium"></th>
              <th className="py-3 px-3 font-medium">Ticket ID</th>
              <th className="py-3 px-3 font-medium">Flagged At</th>
              <th className="py-3 px-3 font-medium">Zone</th>
              <th className="py-3 px-3 font-medium">Fixture</th>
              <th className="py-3 px-3 font-medium">Anomaly Type</th>
              <th className="py-3 px-3 font-medium">Severity</th>
              <th className="py-3 px-3 font-medium text-right">Water Loss</th>
              <th className="py-3 px-3 font-medium text-right">Utility Cost</th>
              <th className="py-3 px-4 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {filteredTickets.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-10 text-center text-xs text-[#8B949E]">
                  No tickets found matching current filter.
                </td>
              </tr>
            ) : (
              filteredTickets.map((t) => {
                const isResolved = t.status === "resolved";
                const stripeColor =
                  t.severity_label === "Critical"
                    ? "#E4572E"
                    : t.severity_label === "High"
                    ? "#F0A202"
                    : t.severity_label === "Medium"
                    ? "#D9B44A"
                    : "#6E7681";

                return (
                  <React.Fragment key={t.ticket_id}>
                    {/* Primary Row */}
                    <tr
                      className={`hover:bg-white/[0.02] transition-colors ${
                        isResolved ? "opacity-60" : ""
                      }`}
                    >
                      {/* Severity indicator stripe */}
                      <td className="py-3.5 px-0 w-1.5" style={{ backgroundColor: stripeColor }} />
                      <td className="py-3.5 px-3 font-mono font-medium text-[#C9D1D9]">
                        {t.ticket_id}
                      </td>
                      <td className="py-3.5 px-3 text-[#8B949E]">{t.timestamp_flagged_str}</td>
                      <td className="py-3.5 px-3 font-medium text-white">
                        {t.zone_id.replace("T2_", "").replace("_", " ")}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[#C5A059] font-medium">
                        {t.fixture_id}
                      </td>
                      <td className="py-3.5 px-3 text-[#8B949E]">
                        <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-[11px]">
                          {t.anomaly_type.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-3.5 px-3">
                        {getSeverityBadge(t.severity_label, t.severity_score)}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-white font-medium">
                        {t.estimated_water_loss_liters?.toFixed(1)} L
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-[#8B949E]">
                        ₹{t.estimated_cost_impact?.toFixed(2)}
                      </td>
                      <td className="py-3.5 px-4 text-right">{getStatusPill(t)}</td>
                    </tr>

                    {/* AI Explanation & Evidence Sub-Row */}
                    <tr className="bg-[#12161A]/50 border-b border-white/[0.06]">
                      <td className="w-1.5" style={{ backgroundColor: `${stripeColor}33` }} />
                      <td colSpan={9} className="py-2.5 px-3 pr-6 space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 max-w-5xl">
                          {t.explanation ? (
                            <div className="flex items-start gap-2.5 flex-1">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-[#6B8CAE]/15 text-[#6B8CAE] border border-[#6B8CAE]/30 shrink-0 mt-0.5">
                                <Sparkles className="h-2.5 w-2.5" /> AI Analysis
                              </span>
                              <p className="text-xs text-[#C9D1D9] leading-relaxed whitespace-normal break-words">
                                {t.explanation}
                              </p>
                            </div>
                          ) : (
                            <div className="text-xs text-[#8B949E]">
                              Telemetry anomaly recorded.
                            </div>
                          )}

                          {/* Evidence Toggle Button */}
                          <button
                            onClick={() => toggleEvidence(t.ticket_id)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium text-[#C9A873] bg-[#B08D57]/10 hover:bg-[#B08D57]/20 border border-[#B08D57]/30 transition-all cursor-pointer shrink-0 self-start sm:self-auto"
                          >
                            <SlidersHorizontal className="h-3 w-3" />
                            <span>
                              {expandedEvidence[t.ticket_id] ? "Hide Evidence" : "Why was this flagged?"}
                            </span>
                            {expandedEvidence[t.ticket_id] ? (
                              <ChevronUp className="h-3 w-3" />
                            ) : (
                              <ChevronDown className="h-3 w-3" />
                            )}
                          </button>
                        </div>

                        {/* Expandable Evidence Breakdown Panel */}
                        {expandedEvidence[t.ticket_id] && t.evidence && (
                          <div className="pt-2">
                            <EvidencePanel evidence={t.evidence} />
                          </div>
                        )}
                      </td>
                    </tr>
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
