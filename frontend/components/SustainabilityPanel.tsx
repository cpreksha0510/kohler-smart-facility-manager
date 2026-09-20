"use client";

import React, { useState } from "react";
import {
  Leaf,
  Droplets,
  TrendingDown,
  AlertTriangle,
  Building2,
  HelpCircle,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
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
  T2_Restroom_A: "#5B8DEF",
  T2_Restroom_B: "#3EA882",
  T2_Family_Room: "#E09F3E",
  T2_Staff_WC: "#9D7FE3",
};

export function SustainabilityPanel({ summary, loading }: SustainabilityPanelProps) {
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  if (loading || !summary) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-20 bg-[#0F141D] rounded-md" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-[#0F141D] rounded-md" />
          ))}
        </div>
        <div className="h-48 bg-[#0F141D] rounded-md" />
      </div>
    );
  }

  const {
    water_waste_liters,
    water_saved_liters,
    cost_impact_inr,
    avoided_cost_inr,
    projected_unresolved_loss_24h_liters,
    highest_waste_fixture,
    zone_breakdown,
  } = summary;

  return (
    <div className="space-y-6">
      {/* 1. Dedicated Header Banner */}
      <div className="bg-[#0F141D] rounded-md p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-md bg-[#2EB88A]/15 border border-[#2EB88A]/30 text-[#2EB88A]">
              <Leaf className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#F0F6FC] tracking-wide uppercase flex items-center gap-2">
                Sustainability &amp; Water Conservation Impact
              </h2>
              <p className="text-xs text-[#8B949E] mt-0.5">
                Facility-wide water recovery metrics, runaway risk horizons &amp; preventive maintenance savings
              </p>
            </div>
          </div>

          {/* Counterfactual Simulation Model Badge */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#2EB88A]/10 text-[#2EB88A] border border-[#2EB88A]/25">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Counterfactual Simulation Model (24h Baseline)</span>
            </span>
          </div>
        </div>
      </div>

      {/* 2. Top-Level Metric Cards (Exactly 1 Main Number + 1 Short Supporting Line per Card) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card A: Water Waste Volume */}
        <div className="bg-[#0F141D] rounded-md p-4.5 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">
              Water Waste Volume
            </span>
            <div className="h-8 w-8 rounded-md bg-[#F04438]/10 border border-[#F04438]/20 flex items-center justify-center text-[#F04438]">
              <Droplets className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-[#F0F6FC] tracking-tight">
              {water_waste_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <p className="text-xs text-[#8B949E] font-mono mt-1">
              ₹{cost_impact_inr.toFixed(2)} municipal tariff impact
            </p>
          </div>
        </div>

        {/* Card B: Estimated Water Saved (Counterfactual) */}
        <div className="bg-[#0F141D] rounded-md p-4.5 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">
              Estimated Water Saved
            </span>
            <div className="h-8 w-8 rounded-md bg-[#2EB88A]/15 border border-[#2EB88A]/30 flex items-center justify-center text-[#2EB88A]">
              <TrendingDown className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-[#F0F6FC] tracking-tight">
              {water_saved_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <p className="text-xs text-[#8B949E] font-mono mt-1">
              ₹{avoided_cost_inr.toFixed(2)} estimated avoided cost
            </p>
          </div>
        </div>

        {/* Card C: Unaddressed Risk (+24h) */}
        <div className="bg-[#0F141D] rounded-md p-4.5 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">
              Unaddressed Risk (+24h)
            </span>
            <div className="h-8 w-8 rounded-md bg-[#EAAA08]/10 border border-[#EAAA08]/20 flex items-center justify-center text-[#EAAA08]">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-[#F0F6FC] tracking-tight">
              +{projected_unresolved_loss_24h_liters.toLocaleString()} <span className="text-xs font-normal text-[#8B949E]">L</span>
            </div>
            <p className="text-xs text-[#8B949E] font-mono mt-1">
              +₹{(projected_unresolved_loss_24h_liters * 0.05).toFixed(2)} if unresolved for 24h
            </p>
          </div>
        </div>

        {/* Card D: Primary Loss Hotspot */}
        <div className="bg-[#0F141D] rounded-md p-4.5 transition-all shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">
              Primary Loss Hotspot
            </span>
            <div className="h-8 w-8 rounded-md bg-[#D4A359]/10 border border-[#D4A359]/20 flex items-center justify-center text-[#D4A359]">
              <Building2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-[#F0F6FC] tracking-tight">
              {highest_waste_fixture ? highest_waste_fixture.fixture_id : "None"}
            </div>
            <p className="text-xs text-[#8B949E] font-mono mt-1 truncate">
              {highest_waste_fixture
                ? `${highest_waste_fixture.zone_id.replace("T2_", "").replace("_", " ")} · ${highest_waste_fixture.water_waste_liters} L lost`
                : "Normal operations"}
            </p>
          </div>
        </div>
      </div>

      {/* 3. Zone Conservation Breakdown */}
      <div className="bg-[#0F141D] rounded-md p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-3 border-b border-white/[0.06]">
          <div>
            <h3 className="text-xs font-bold text-[#F0F6FC] uppercase tracking-wider">
              Zone Conservation Breakdown
            </h3>
            <p className="text-xs text-[#8B949E] mt-0.5">
              Runaway risk horizons and verified savings per airport terminal sector
            </p>
          </div>
          <span className="text-[11px] text-[#8B949E]">
            Ranked by total volumetric waste
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {zone_breakdown.map((z) => {
            const wasteL = z.water_waste_liters || 0;
            const savedL = z.water_saved_liters || 0;
            const color = ZONE_COLORS[z.zone_id] || "#4D88C7";
            const zoneName = ZONE_LABELS[z.zone_id] || z.zone_id.replace("T2_", "").replace("_", " ");

            return (
              <div
                key={z.zone_id}
                className="p-4 rounded-md bg-[#0B0F14] flex items-center justify-between"
              >
                <div className="flex items-center gap-2.5">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <div>
                    <span className="text-xs font-semibold text-white block">{zoneName}</span>
                    <span className="text-[11px] text-[#8B949E]">{z.open_count} open · {z.resolved_count} resolved</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs font-mono font-bold text-[#F0F6FC]">
                    {wasteL.toLocaleString()} L <span className="text-[10px] font-normal text-[#8B949E]">lost</span>
                  </div>
                  <div className="text-xs font-mono text-[#8B949E] font-medium mt-0.5">
                    {savedL > 0
                      ? `+${savedL.toLocaleString()} L saved`
                      : "0.0 L saved"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Collapsible Conservation Methodology Accordion (Collapsed by Default) */}
      <div className="bg-[#0F141D] rounded-md p-4.5 shadow-sm">
        <button
          id="toggle-methodology-accordion"
          onClick={() => setIsMethodologyOpen(!isMethodologyOpen)}
          className="w-full flex items-center justify-between text-left text-xs font-medium text-[#8B949E] hover:text-[#F0F6FC] transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-[#D4A359]" />
            <span className="font-semibold text-[#F0F6FC]">Conservation Methodology &amp; Baseline Model</span>
            <span className="text-[11px] text-[#8B949E] hidden sm:inline">
              — click to {isMethodologyOpen ? "collapse" : "view details"}
            </span>
          </div>
          {isMethodologyOpen ? (
            <ChevronUp className="h-4 w-4 text-[#8B949E]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[#8B949E]" />
          )}
        </button>

        {isMethodologyOpen && (
          <div className="mt-3.5 pt-3.5 border-t border-white/[0.06] text-xs text-[#8B949E] space-y-3 leading-relaxed">
            <p>
              <strong className="text-[#F0F6FC]">Counterfactual Simulation Model:</strong> Prevented waste represents the
              simulated water volume that would have escaped during the standard 24-hour unassisted inspection cycle (1,440 minutes)
              minus the actual volume lost before technician resolution.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 font-mono text-[11px] text-[#C9D1D9]">
              <div className="bg-[#0B0F14] p-2.5 rounded-lg border border-white/[0.04]">
                <span className="text-[#8B949E] block text-[10px] uppercase font-sans font-semibold mb-1">
                  Avoided Volume Formula
                </span>
                Max((Observed LPM × 1,440 min) − Actual Loss, 0)
              </div>
              <div className="bg-[#0B0F14] p-2.5 rounded-lg border border-white/[0.04]">
                <span className="text-[#8B949E] block text-[10px] uppercase font-sans font-semibold mb-1">
                  Utility Tariff Rate
                </span>
                ₹0.05 / Litre (commercial airport municipal baseline)
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
