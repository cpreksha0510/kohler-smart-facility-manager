"use client";

import React from "react";
import { Activity, AlertTriangle, Droplets, Grid } from "lucide-react";
import { OverviewMetrics } from "./types";

interface MetricCardsProps {
  metrics: OverviewMetrics | null;
  loading: boolean;
}

export function MetricCards({ metrics, loading }: MetricCardsProps) {
  const readingsCount = metrics ? metrics.sensor_readings_count.toLocaleString() : "...";
  const ticketsCount = metrics ? metrics.total_tickets_count : 0;
  const openTickets = metrics ? metrics.open_tickets_count : 0;
  const zonesCount = metrics ? metrics.zones_monitored_count : 4;
  const waterLoss = metrics ? `${metrics.estimated_water_loss_liters.toFixed(1)} L` : "0.0 L";
  const costImpact = metrics ? `₹${metrics.estimated_cost_impact_inr.toFixed(2)}` : "₹0.00";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Sensor Readings */}
      <div className="bg-[#141A22] border border-white/[0.08] hover:border-white/[0.15] rounded-xl p-4.5 transition-all shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">Sensor Readings</span>
          <div className="h-8 w-8 rounded-lg bg-[#4D88C7]/15 border border-[#4D88C7]/30 flex items-center justify-center text-[#4D88C7]">
            <Activity className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold text-[#F0F6FC] tracking-tight font-mono">
            {loading ? "..." : readingsCount}
          </div>
          <p className="text-xs text-[#8B949E] mt-1">
            1-min telemetry rate per fixture
          </p>
        </div>
      </div>

      {/* 2. Flagged Anomaly Tickets */}
      <div className="bg-[#141A22] border border-white/[0.08] hover:border-white/[0.15] rounded-xl p-4.5 transition-all shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">Flagged Tickets</span>
          <div className="h-8 w-8 rounded-lg bg-[#F38744]/15 border border-[#F38744]/30 flex items-center justify-center text-[#F38744]">
            <AlertTriangle className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <div>
            <div className="text-2xl font-bold text-[#F0F6FC] tracking-tight font-mono">
              {loading ? "..." : ticketsCount}
            </div>
            <p className="text-xs text-[#8B949E] mt-1">
              <span className="font-semibold text-[#F0F6FC]">{openTickets} active</span> requiring attention
            </p>
          </div>
          {openTickets > 0 && (
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-[#F38744]/15 border border-[#F38744]/30 text-[#F38744]">
              Action Needed
            </span>
          )}
        </div>
      </div>

      {/* 3. Monitored Zones */}
      <div className="bg-[#141A22] border border-white/[0.08] hover:border-white/[0.15] rounded-xl p-4.5 transition-all shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">Monitored Zones</span>
          <div className="h-8 w-8 rounded-lg bg-[#D4A359]/15 border border-[#D4A359]/30 flex items-center justify-center text-[#D4A359]">
            <Grid className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold text-[#F0F6FC] tracking-tight font-mono">
            {loading ? "..." : `${zonesCount} Zones`}
          </div>
          <p className="text-xs text-[#8B949E] mt-1">
            Departure, Arrival, Family &amp; Staff WC
          </p>
        </div>
      </div>

      {/* 4. Estimated Water Loss */}
      <div className="bg-[#141A22] border border-white/[0.08] hover:border-white/[0.15] rounded-xl p-4.5 transition-all shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-[#8B949E] uppercase tracking-wider">Estimated Water Loss</span>
          <div className="h-8 w-8 rounded-lg bg-[#4D88C7]/15 border border-[#4D88C7]/30 flex items-center justify-center text-[#4D88C7]">
            <Droplets className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-3">
          <div className="text-2xl font-bold text-[#F0F6FC] tracking-tight font-mono">
            {loading ? "..." : waterLoss}
          </div>
          <p className="text-xs text-[#8B949E] mt-1">
            Utility Cost Impact: <span className="text-[#F0F6FC] font-medium">{costImpact}</span>
          </p>
        </div>
      </div>
    </div>
  );
}
