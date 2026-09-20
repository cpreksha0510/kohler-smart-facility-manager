"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Users } from "lucide-react";
import { OccupancyHeatmapData } from "./types";

interface OccupancyHeatmapProps {
  data: OccupancyHeatmapData | null;
  loading: boolean;
}

export function OccupancyHeatmap({ data, loading }: OccupancyHeatmapProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<{
    fixture: string;
    hour: number;
    val: number;
    x: number;
    y: number;
  } | null>(null);

  if (!data || data.fixtures.length === 0) {
    return null;
  }

  // Color interpolation for 0.0 to 1.0 occupancy
  const getCellColor = (val: number) => {
    if (val <= 0.02) return "#101010";
    if (val < 0.2) return "#182438";
    if (val < 0.4) return "#233959";
    if (val < 0.6) return "#305482";
    if (val < 0.8) return "#4373B0";
    return "#5B8DEF";
  };

  return (
    <div className="bg-[#101010] rounded-md overflow-hidden shadow-sm transition-all">
      {/* Collapsible Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Users className="h-4 w-4 text-[#5B8DEF]" />
          <span className="text-sm font-semibold text-white tracking-wide">
            Occupancy Pattern by Hour of Day
          </span>
          <span className="text-xs text-[#8B949E]">
            ({data.fixtures.length} fixtures monitored across 24 hours)
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#8B949E]">
          <span>{isOpen ? "Collapse" : "Expand Heatmap"}</span>
          {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
      </button>

      {/* Heatmap Body */}
      {isOpen && (
        <div className="p-5 border-t border-white/[0.08] relative">
          <div className="overflow-x-auto">
            <div className="min-w-[700px]">
              {/* Hour Labels */}
              <div className="flex items-center mb-1.5 ml-24">
                {data.hours.map((h) => (
                  <div
                    key={h}
                    className="flex-1 text-center text-[10px] text-[#8B949E] font-mono"
                  >
                    {h.toString().padStart(2, "0")}h
                  </div>
                ))}
              </div>

              {/* Matrix Rows */}
              <div className="space-y-1">
                {data.fixtures.map((fixture, rowIdx) => {
                  const rowData = data.matrix[rowIdx] || [];
                  return (
                    <div key={fixture} className="flex items-center gap-2">
                      {/* Fixture Label */}
                      <span className="w-22 text-[11px] font-mono text-[#C9D1D9] truncate text-right pr-2">
                        {fixture}
                      </span>

                      {/* 24 Hour Blocks */}
                      <div className="flex-1 flex gap-1 h-5">
                        {rowData.map((val, colIdx) => {
                          const hour = data.hours[colIdx];
                          return (
                            <div
                              key={colIdx}
                              className="flex-1 rounded-[2px] transition-all hover:ring-1 hover:ring-white/80 cursor-pointer"
                              style={{ backgroundColor: getCellColor(val) }}
                              onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect();
                                setHoveredCell({
                                  fixture,
                                  hour,
                                  val,
                                  x: rect.left + rect.width / 2,
                                  y: rect.top - 8,
                                });
                              }}
                              onMouseLeave={() => setHoveredCell(null)}
                            />
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Legend scale */}
              <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-[#8B949E]">
                <span>Occupancy Rate</span>
                <div className="flex items-center gap-2">
                  <span>0% (Empty)</span>
                  <div className="flex gap-1 h-3 w-32 rounded overflow-hidden">
                    <div className="flex-1 bg-[#101010]" />
                    <div className="flex-1 bg-[#182438]" />
                    <div className="flex-1 bg-[#233959]" />
                    <div className="flex-1 bg-[#305482]" />
                    <div className="flex-1 bg-[#4373B0]" />
                    <div className="flex-1 bg-[#5B8DEF]" />
                  </div>
                  <span>100% (Continuous Use)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Floating Tooltip */}
          {hoveredCell && (
            <div
              className="fixed z-50 transform -translate-x-1/2 -translate-y-full px-2.5 py-1.5 bg-[#1B222C] border border-white/20 rounded shadow-xl text-xs pointer-events-none"
              style={{ left: hoveredCell.x, top: hoveredCell.y }}
            >
              <div className="font-semibold text-white">{hoveredCell.fixture}</div>
              <div className="text-[#8B949E]">
                Hour {hoveredCell.hour}:00 · {(hoveredCell.val * 100).toFixed(0)}% Occupied
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
