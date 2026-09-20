"use client";

import React from "react";
import {
  ShieldCheck,
  AlertCircle,
  Activity,
  Clock,
  UserX,
  Droplets,
  HelpCircle,
  Gauge,
  SlidersHorizontal,
} from "lucide-react";
import { TicketEvidence } from "./types";

interface EvidencePanelProps {
  evidence: TicketEvidence;
}

export function EvidencePanel({ evidence }: EvidencePanelProps) {
  const {
    expected_flow_lpm,
    observed_flow_lpm,
    peak_flow_lpm,
    flow_deviation_lpm,
    duration_minutes,
    occupancy_rate,
    occupancy_mismatch,
    sensor_health,
    normalized_flow_deviation,
    normalized_duration,
    normalized_occupancy_mismatch,
    normalized_sensor_health,
    evidence_strength_score,
    evidence_strength_label,
    estimated_water_loss_liters,
  } = evidence;

  // Strength Badge Palette
  const strengthStyles = {
    Strong: {
      bg: "bg-[#2EB88A]/15",
      text: "text-[#2EB88A]",
      border: "border-[#2EB88A]/35",
      bar: "bg-[#2EB88A]",
    },
    Moderate: {
      bg: "bg-[#EAAA08]/15",
      text: "text-[#EAAA08]",
      border: "border-[#EAAA08]/35",
      bar: "bg-[#EAAA08]",
    },
    Weak: {
      bg: "bg-[#717BBC]/15",
      text: "text-[#717BBC]",
      border: "border-[#717BBC]/35",
      bar: "bg-[#717BBC]",
    },
  }[evidence_strength_label] || {
    bg: "bg-white/10",
    text: "text-[#F0F6FC]",
    border: "border-white/20",
    bar: "bg-white",
  };

  return (
    <div className="mt-4 pt-4 border-t border-white/[0.08] bg-[#0B0F14]/90 rounded-lg p-4 space-y-4">
      {/* 1. Header & Evidence Strength */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-[#D4A359]/15 text-[#D4A359]">
            <SlidersHorizontal className="h-4 w-4" />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#F0F6FC]">
              Why was this flagged?
            </span>
            <span className="ml-2 text-[11px] text-[#8B949E]">
              Deterministic Telemetry Evidence Breakdown
            </span>
          </div>
        </div>

        {/* Evidence Strength Badge (Section 4.4 — Transparent, No Fake Confidence %) */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-[#8B949E]">Evidence Strength:</span>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold border ${strengthStyles.bg} ${strengthStyles.text} ${strengthStyles.border}`}
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>{evidence_strength_label}</span>
            <span className="text-[10px] opacity-75 font-mono">
              ({evidence_strength_score}/100)
            </span>
          </span>
        </div>
      </div>

      {/* 2. Four Multi-Signal Evidence Bars (Section 4.3) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 bg-[#141A22] p-3 rounded-lg border border-white/[0.06]">
        {/* Flow Deviation */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#8B949E] flex items-center gap-1">
              <Activity className="h-3 w-3 text-[#4D88C7]" /> Flow Deviation
            </span>
            <span className="font-mono font-medium text-[#F0F6FC]">
              {normalized_flow_deviation}%
            </span>
          </div>
          <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#4D88C7] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, normalized_flow_deviation))}%` }}
            />
          </div>
          <div className="text-[10px] text-[#8B949E]/70 font-mono">
            +{flow_deviation_lpm.toFixed(2)} L/m above base
          </div>
        </div>

        {/* Duration */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#8B949E] flex items-center gap-1">
              <Clock className="h-3 w-3 text-[#D4A359]" /> Duration Span
            </span>
            <span className="font-mono font-medium text-[#F0F6FC]">
              {normalized_duration}%
            </span>
          </div>
          <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#D4A359] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, normalized_duration))}%` }}
            />
          </div>
          <div className="text-[10px] text-[#8B949E]/70 font-mono">
            {duration_minutes} min duration
          </div>
        </div>

        {/* Occupancy Mismatch */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#8B949E] flex items-center gap-1">
              <UserX className="h-3 w-3 text-[#F38744]" /> Occupancy Mismatch
            </span>
            <span className="font-mono font-medium text-[#F0F6FC]">
              {normalized_occupancy_mismatch}%
            </span>
          </div>
          <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#F38744] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, normalized_occupancy_mismatch))}%` }}
            />
          </div>
          <div className="text-[10px] text-[#8B949E]/70 font-mono">
            {occupancy_mismatch === 1.0 ? "Zero occupancy (Flow + Vacant)" : "Normal presence"}
          </div>
        </div>

        {/* Sensor Health */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[#8B949E] flex items-center gap-1">
              <Gauge className="h-3 w-3 text-[#2EB88A]" /> Sensor Diagnostic
            </span>
            <span className="font-mono font-medium text-[#F0F6FC]">
              {normalized_sensor_health}%
            </span>
          </div>
          <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#2EB88A] rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, normalized_sensor_health))}%` }}
            />
          </div>
          <div className="text-[10px] text-[#8B949E]/70 font-mono">
            Status: {sensor_health} (100% confidence)
          </div>
        </div>
      </div>

      {/* 3. Physical Telemetry Facts Grid (Section 4.2) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
        <div className="bg-[#141A22] p-2 rounded border border-white/[0.04]">
          <span className="text-[10px] text-[#8B949E] block uppercase tracking-wider">
            Expected Baseline
          </span>
          <span className="font-mono font-semibold text-[#F0F6FC]">
            {expected_flow_lpm.toFixed(2)} L/min
          </span>
        </div>

        <div className="bg-[#141A22] p-2 rounded border border-white/[0.04]">
          <span className="text-[10px] text-[#8B949E] block uppercase tracking-wider">
            Observed Flow
          </span>
          <span className="font-mono font-semibold text-[#F0F6FC]">
            {observed_flow_lpm.toFixed(2)} L/min
            {peak_flow_lpm > observed_flow_lpm && (
              <span className="text-[10px] text-[#8B949E] font-normal ml-1">
                (peak {peak_flow_lpm.toFixed(2)})
              </span>
            )}
          </span>
        </div>

        <div className="bg-[#141A22] p-2 rounded border border-white/[0.04]">
          <span className="text-[10px] text-[#8B949E] block uppercase tracking-wider">
            Active Occupancy
          </span>
          <span className="font-mono font-semibold text-[#F0F6FC]">
            {occupancy_rate === 0.0 ? "0% (Unoccupied)" : `${Math.round(occupancy_rate * 100)}%`}
          </span>
        </div>

        <div className="bg-[#141A22] p-2 rounded border border-white/[0.04]">
          <span className="text-[10px] text-[#8B949E] block uppercase tracking-wider">
            Total Water Lost
          </span>
          <span className="font-mono font-semibold text-[#F0F6FC]">
            {estimated_water_loss_liters.toFixed(1)} Litres
          </span>
        </div>
      </div>

      {/* 4. Formula & Grounding Rationale Note */}
      <div className="flex items-start gap-2 pt-1 text-[11px] text-[#8B949E]/80 bg-[#141A22]/50 p-2.5 rounded border border-white/[0.04]">
        <HelpCircle className="h-3.5 w-3.5 text-[#D4A359] shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p>
            <strong className="text-[#F0F6FC]">Evidence Weighting Formula:</strong>{" "}
            <span className="font-mono text-[10px] text-[#D4A359]">
              30% Flow Deviation + 25% Duration + 25% Occupancy Mismatch + 20% Sensor Health
            </span>
          </p>
          <p className="text-[10px] text-[#8B949E]">
            {occupancy_mismatch === 1.0
              ? "Continuous water flow while the fixture remained completely unoccupied is inconsistent with passenger use and strongly indicates a stuck valve or mechanical leak."
              : "Flow parameters deviated from historical hourly moving baseline during occupied usage."}
          </p>
        </div>
      </div>
    </div>
  );
}
