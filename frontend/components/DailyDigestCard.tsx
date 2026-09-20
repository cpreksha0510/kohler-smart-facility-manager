"use client";

import React, { useState } from "react";
import { FileText, Wrench } from "lucide-react";
import { DailyDigest } from "./types";

interface DailyDigestCardProps {
  digests: Record<string, DailyDigest>;
}

export function DailyDigestCard({ digests }: DailyDigestCardProps) {
  const dates = Object.keys(digests).sort().reverse();
  const [selectedDate, setSelectedDate] = useState<string>(dates[0] || "2024-01-16");

  if (dates.length === 0) return null;

  const currentDigest = digests[selectedDate] || {
    digest: "No summary available for this date.",
    ticket_count: 0,
    created_at: "",
  };

  // Format YYYY-MM-DD -> "Tue, Jan 16, 2024"
  const formatDateTitle = (dStr: string) => {
    try {
      const parts = dStr.split("-");
      const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
    } catch {
      return dStr;
    }
  };

  return (
    <div className="bg-[#101010] border-l-4 border-l-[#C5A059] rounded-md p-5 shadow-sm">
      {/* Header with date selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[#C5A059]" />
          <h3 className="text-sm font-semibold text-white tracking-wide">
            Operational Daily Digest
          </h3>
          <span className="text-xs text-[#8B949E]">(Low &amp; Medium severity summary)</span>
        </div>

        {/* Date Tabs */}
        <div className="flex items-center bg-[#080808] p-1 rounded-lg border border-white/[0.08]">
          {dates.map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDate(d)}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                selectedDate === d
                  ? "bg-[#21262D] text-[#C5A059] font-semibold"
                  : "text-[#8B949E] hover:text-white"
              }`}
            >
              {formatDateTitle(d).split(",").slice(0, 2).join(",")}
            </button>
          ))}
        </div>
      </div>

      {/* Digest Content Card */}
      <div className="bg-[#12161A]/60 rounded-lg p-4 border border-white/[0.04]">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-[#F0F6FC] flex items-center gap-1.5">
            <Wrench className="h-3.5 w-3.5 text-[#C5A059]" />
            Summary for {formatDateTitle(selectedDate)}
          </span>
          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-[#C5A059]/15 border border-[#C5A059]/30 text-[#C5A059]">
            {currentDigest.ticket_count} Low/Med tickets summarized
          </span>
        </div>
        <p className="text-xs text-[#C9D1D9] leading-relaxed">
          {currentDigest.digest}
        </p>
      </div>
    </div>
  );
}
