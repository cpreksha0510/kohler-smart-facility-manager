"use client";

import React, { useEffect, useState } from "react";
import { Play, Pause, RotateCcw, FastForward, Clock } from "lucide-react";

interface ReplayScrubberProps {
  simStart: string;
  simDurationHours: number;
  currentHours: number;
  onChangeHours: React.Dispatch<React.SetStateAction<number>>;
  isPlaying: boolean;
  onTogglePlay: () => void;
  onReset: () => void;
}

export function ReplayScrubber({
  simStart,
  simDurationHours,
  currentHours,
  onChangeHours,
  isPlaying,
  onTogglePlay,
  onReset,
}: ReplayScrubberProps) {
  const [speed, setSpeed] = useState<number>(2); // hours per second

  // Playback timer effect
  useEffect(() => {
    if (!isPlaying) return;

    const intervalMs = 500;
    const increment = (speed * intervalMs) / 1000;

    const timer = setInterval(() => {
      onChangeHours((prev) => {
        const next = prev + increment;
        if (next >= simDurationHours) {
          onTogglePlay(); // stop at end
          return simDurationHours;
        }
        return next;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isPlaying, speed, simDurationHours, onChangeHours, onTogglePlay]);

  // Compute simulated timestamp from currentHours
  const getSimulatedDate = () => {
    const startDate = new Date(simStart || "2024-01-15T00:00:00");
    const d = new Date(startDate.getTime() + currentHours * 3600 * 1000);
    return d.toLocaleString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  };

  const progressPercent = Math.min(100, Math.round((currentHours / simDurationHours) * 100));

  return (
    <div className="bg-[#141A22] border border-[#D4A359]/30 rounded-xl p-5 shadow-lg">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-4">
        {/* Controls: Play, Reset, Speed */}
        <div className="flex items-center gap-3">
          <button
            onClick={onTogglePlay}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-[#D4A359] text-black hover:bg-[#D4A359]/90 shadow-md transition-all"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 fill-current" />}
            <span>{isPlaying ? "Pause" : "Play Simulation"}</span>
          </button>

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-[#0B0F14] hover:bg-white/10 text-[#8B949E] hover:text-[#F0F6FC] border border-white/10 transition-all"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset (00:00)</span>
          </button>

          {/* Speed Pills */}
          <div className="flex items-center bg-[#0B0F14] p-1 rounded-lg border border-white/[0.08]">
            <span className="text-[10px] text-[#8B949E] px-2 font-medium">Speed:</span>
            {[0.5, 1, 2, 4, 8].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                  speed === s ? "bg-[#1B222C] text-[#D4A359] font-bold" : "text-[#8B949E] hover:text-[#F0F6FC]"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Current Simulated Clock */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] uppercase tracking-wider text-[#8B949E] block">
              Simulated Replay Clock
            </span>
            <div className="text-lg font-mono font-bold text-[#D4A359] flex items-center gap-1.5 justify-end">
              <Clock className="h-4 w-4" />
              <span>{getSimulatedDate()}</span>
            </div>
          </div>
          <div className="px-2.5 py-1 rounded bg-white/[0.04] border border-white/10 text-xs font-mono text-[#F0F6FC]">
            {progressPercent}%
          </div>
        </div>
      </div>

      {/* Scrubbing Slider Track */}
      <div className="space-y-1.5">
        <input
          type="range"
          min="0"
          max={simDurationHours}
          step="0.1"
          value={currentHours}
          onChange={(e) => onChangeHours(parseFloat(e.target.value))}
          className="w-full h-2 bg-[#0B0F14] rounded-lg appearance-none cursor-pointer accent-[#D4A359]"
        />
        <div className="flex justify-between text-[10px] text-[#8B949E] font-mono">
          <span>0h (Mon 00:00)</span>
          <span>12h (Mon 12:00)</span>
          <span>24h (Tue 00:00)</span>
          <span>36h (Tue 12:00)</span>
          <span>48h (Wed 00:00)</span>
        </div>
      </div>
    </div>
  );
}
