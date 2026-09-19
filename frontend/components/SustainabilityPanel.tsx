"use client";

import React from "react";
import {
  Leaf,
  Droplets,
  TrendingDown,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Building2,
  HelpCircle,
  ArrowUpRight,
} from "lucide-react";
import { SustainabilitySummary } from "./types";

interface SustainabilityPanelProps {
  summary: SustainabilitySummary | null;
  loading: boolean;
}

const ZONE_LABELS: Record<string, string> = {
  T2_Restroom_A: "Restroom A (Departure)",
  T2_Restroom_B: "Restroom B (Arrival)",
  T2_Family_Room: "Family Room",
  T2_Staff_WC: "Staff WC",
};

const ZONE_COLORS: Record<string, string> = {
  T2_Restroom_A: "#6B8CAE",
  T2_Restroom_B: "#789A8B",
  T2_Family_Room: "#B08D57",
  T2_Staff_WC: "#847E9C",
};

export function SustainabilityPanel({ summary, loading }: SustainabilityPanelProps) {
  if (loading || !summary) {
    return (
      <div className="bg-[#161B22] border border-white/[0.08] rounded-xl p-5 shadow-sm animate-pulse space-y-4">
        <div className="h-4 w-48 bg-white/10 rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white/5 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const {
    water_waste_liters,
    water_saved_liters,
    cost_impact_inr,
    avoided_cost_inr,
    projected_unresolved_loss_24h_liters,
    projected_unresolved_loss_7d_liters,
    highest_waste_fixture,
    highest_waste_zone,
    zone_breakdown,
  } = summary;

  return (
    <div className="bg-[#161B22] border border-white/[0.08] rounded-xl p-5 shadow-sm space-y-5">
      {/* 1. Header with Model Disclosure Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-[#789A8B]/15 border border-[#789A8B]/30 text-[#98BAAB]">
            <Leaf className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide uppercase">
              Sustainability &amp; Water Conservation Impact
            </h2>
            <p className="text-xs text-[#8B949E]">
              Telemetry-driven waste quantification &amp; preventive maintenance savings
            </p>
          </div>
        </div>

        {/* Explicit Counterfactual Model Disclosure per Section 9 Rule 5 & 6 */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#789A8B]/10 text-[#98BAAB] border border-[#789A8B]/25">
            <ShieldCheck className="h-3 w-3" />
            <span>Counterfactual Simulation Model (24h Baseline)</span>
          </span>
        </div>
      </div>

      {/* 2. Top-Level Metrics Grid (4 Key Impact Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card A: Actual Water Waste */}
        <div className="bg-[#0D1117] border border-white/[0.06] rounded-xl p-4 space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#8B949E] uppercase tracking-wider font-semibold">
              Water Waste Volume
            </span>
            <div className="p-1 rounded bg-[#E4572E]/10 text-[#E4572E]">
              <Droplets className="h-3.5 w-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-white">
              {water_waste_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <div className="text-xs text-[#E4572E] font-mono mt-0.5">
              ₹{cost_impact_inr.toFixed(2)} municipal tariff impact
            </div>
          </div>
          <div className="text-[10px] text-[#8B949E] pt-1">
            Measured across all flagged anomaly sessions
          </div>
        </div>

        {/* Card B: Estimated Water Saved (Counterfactual) */}
        <div className="bg-[#0D1117] border border-[#789A8B]/30 rounded-xl p-4 space-y-2 relative overflow-hidden bg-gradient-to-b from-[#789A8B]/5 to-transparent">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#98BAAB] uppercase tracking-wider font-semibold">
              Estimated Water Saved
            </span>
            <div className="p-1 rounded bg-[#789A8B]/15 text-[#98BAAB]">
              <TrendingDown className="h-3.5 w-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-[#98BAAB]">
              {water_saved_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <div className="text-xs text-[#98BAAB] font-mono mt-0.5">
              ₹{avoided_cost_inr.toFixed(2)} estimated avoided cost
            </div>
          </div>
          <div className="text-[10px] text-[#8B949E] pt-1">
            Saved via prompt technician resolution
          </div>
        </div>

        {/* Card C: Projected Unresolved Waste (Runaway Risk Horizon) */}
        <div className="bg-[#0D1117] border border-white/[0.06] rounded-xl p-4 space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#8B949E] uppercase tracking-wider font-semibold">
              Unaddressed Risk (+24h)
            </span>
            <div className="p-1 rounded bg-[#D99B26]/10 text-[#D99B26]">
              <AlertTriangle className="h-3.5 w-3.5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-bold font-mono text-[#D99B26]">
              +{projected_unresolved_loss_24h_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <div className="text-xs text-[#8B949E] font-mono mt-0.5">
              +{(projected_unresolved_loss_24h_liters * 0.05).toFixed(2)} if open tickets run 24h
            </div>
          </div>
          <div className="text-[10px] text-[#8B949E] pt-1 font-mono">
            7-Day Runaway: +{projected_unresolved_loss_7d_liters.toLocaleString()} L
          </div>
        </div>

        {/* Card D: Conservation Hotspots */}
        <div className="bg-[#0D1117] border border-white/[0.06] rounded-xl p-4 space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#8B949E] uppercase tracking-wider font-semibold">
              Primary Loss Hotspot
            </span>
            <div className="p-1 rounded bg-[#B08D57]/10 text-[#C9A873]">
              <Building2 className="h-3.5 w-3.5" />
            </div>
          </div>
          <div>
            <div className="text-lg font-bold font-mono text-white">
              {highest_waste_fixture ? highest_waste_fixture.fixture_id : "None"}
            </div>
            <div className="text-xs text-[#C9A873] font-medium truncate mt-0.5">
              {highest_waste_fixture ? highest_waste_fixture.zone_id.replace("T2_", "").replace("_", " ") : "Normal"}
            </div>
          </div>
          <div className="text-[10px] text-[#8B949E] pt-1">
            {highest_waste_fixture
              ? `${highest_waste_fixture.water_waste_liters} L lost (${highest_waste_fixture.ticket_count} incidents)`
              : "No active incidents"}
          </div>
        </div>
      </div>

      {/* 3. Zone-Level Conservation Breakdown */}
      <div className="pt-2">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            Zone Conservation Breakdown
          </span>
          <span className="text-[11px] text-[#8B949E]">
            Comparing observed loss vs counterfactual avoided volume
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {zone_breakdown.map((z) => {
            const color = ZONE_COLORS[z.zone_id] || "#6B8CAE";
            const label = ZONE_LABELS[z.zone_id] || z.zone_id;
            return (
              <div
                key={z.zone_id}
                className="bg-[#0D1117] p-3 rounded-lg border border-white/[0.04] flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <div className="min-w-0">
                    <span className="text-xs font-semibold text-white block truncate">{label}</span>
                    <span className="text-[10px] text-[#8B949E]">
                      {z.open_count} open · {z.resolved_count} resolved
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-xs font-mono font-bold text-white">
                    {z.water_waste_liters.toLocaleString()} L <span className="text-[10px] font-normal text-[#8B949E]">lost</span>
                  </div>
                  <div className="text-[11px] font-mono text-[#98BAAB]">
                    {z.water_saved_liters > 0
                      ? `+${z.water_saved_liters.toLocaleString()} L saved`
                      : "0.0 L saved"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Methodology Footer */}
      <div className="flex items-start gap-2 pt-2 border-t border-white/[0.04] text-[11px] text-[#8B949E]">
        <HelpCircle className="h-3.5 w-3.5 text-[#B08D57] shrink-0 mt-0.5" />
        <p>
          <strong className="text-white">Conservation Methodology:</strong> Prevented waste represents the
          counterfactual water volume that would have escaped during standard unassisted inspection cycles (24 hours)
          minus the actual volume lost before technician resolution. Cost is calculated at ₹0.05/L (commercial utility tariff).
        </p>
      </div>
    </div>
  );
}
