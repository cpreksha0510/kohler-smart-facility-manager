"""
config.py — Single source of truth for all constants.

Change values here to adjust simulation behaviour, detection thresholds,
or facility layout without touching logic files.
"""

import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "facility.db"   # created at project root, not inside src/

# ── Simulation window ──────────────────────────────────────────────────────────
SIM_START = datetime.datetime(2024, 1, 15, 0, 0, 0)   # Jan 15 2024, 00:00
SIM_DURATION_HOURS = 48
READING_INTERVAL_MINUTES = 1                           # one row per minute per fixture

# ── Facility layout (zone_id, fixture_id, fixture_type) ────────────────────────
# Terminal 2 Restroom Block — two zones, five fixtures.
FIXTURES = [
    ("T2_Restroom_A", "Sink_01",   "sink"),
    ("T2_Restroom_A", "Sink_02",   "sink"),
    ("T2_Restroom_A", "Toilet_01", "toilet"),
    ("T2_Restroom_B", "Sink_03",   "sink"),
    ("T2_Restroom_B", "Toilet_02", "toilet"),
]

# ── Normal flow rates during an active use event (liters per minute) ───────────
FLOW_RATES = {
    "sink":   {"min": 5.0, "max": 8.0},   # handwashing
    "toilet": {"min": 8.0, "max": 12.0},  # flush cycle
}

# ── Use-event duration ranges (minutes) ───────────────────────────────────────
EVENT_DURATION = {
    "sink":   {"min": 0.5, "max": 2.0},   # 30 s – 2 min handwash
    "toilet": {"min": 0.3, "max": 0.8},   # 20 s – 50 s flush
}

# ── Occupancy probability by hour-of-day (0–23) ────────────────────────────────
# Realistic airport restroom traffic: near-zero overnight, peaks at morning
# and evening rush, steady moderate during the day.
OCCUPANCY_PROB = {
    0: 0.02, 1: 0.02, 2: 0.01, 3: 0.01, 4: 0.02,
    5: 0.10, 6: 0.30, 7: 0.60, 8: 0.70, 9: 0.65,
    10: 0.55, 11: 0.55, 12: 0.60, 13: 0.55, 14: 0.50,
    15: 0.50, 16: 0.55, 17: 0.65, 18: 0.70, 19: 0.65,
    20: 0.55, 21: 0.40, 22: 0.20, 23: 0.08,
}

# ── Anomaly injection windows ──────────────────────────────────────────────────
# Times expressed as hour offsets from SIM_START (for hour-based windows)
# or as minute offsets (for minute-precise windows).

# Anomaly 1: Sustained leak — Sink_01, Day 2 02:00–06:00
# 3.5 LPM continuous flow with zero occupancy. At 2am the baseline is ~0 LPM
# (virtually no one uses the sink overnight), so 3.5 LPM will clearly exceed
# mean + 2.5σ. This is the PRIMARY anomaly that Phase 1 is expected to catch.
ANOMALY_SUSTAINED_LEAK = {
    "fixture_id": "Sink_01",
    "zone_id":    "T2_Restroom_A",
    "start_hour": 26,     # hour 26 from SIM_START = Day 2, 02:00
    "end_hour":   30,     # hour 30 from SIM_START = Day 2, 06:00
    "flow_lpm":   3.5,
    "occupancy":  0,
}

# Anomaly 2: Slow drip — Toilet_02, Day 2 00:00–08:00
# 0.25 LPM tiny trickle with zero occupancy.
# INTENTIONALLY below the 4a detection threshold — the overnight baseline is
# ~0 LPM but std is also ~0, so with STD_FLOOR the threshold ≈ 0.5 LPM.
# 0.25 LPM < 0.5 LPM → NOT flagged by Phase 1.
# Phase 2 (Section 4c rate-of-change detector) will catch this.
# The data is injected now so it exists in the DB when Phase 2 runs.
ANOMALY_SLOW_DRIP = {
    "fixture_id": "Toilet_02",
    "zone_id":    "T2_Restroom_B",
    "start_hour": 24,     # Day 2, 00:00
    "end_hour":   32,     # Day 2, 08:00
    "flow_lpm":   0.25,
    "occupancy":  0,
}

# Anomaly 3: False-positive trap — Sink_02, Day 1 08:15–08:28
# High flow (7.5 LPM) with occupancy = 1 during morning rush.
# This simulates a long handwashing session (e.g., medical glove removal,
# cleaning spill) — legitimate use, should NOT be flagged.
# Phase 1 (4a only) may flag it because the flow duration is unusual even if
# occupancy = 1. Phase 2's multi-signal correlation (4b) will suppress it by
# seeing occupancy = 1 and downgrading the alert.
ANOMALY_FALSE_POSITIVE = {
    "fixture_id":   "Sink_02",
    "zone_id":      "T2_Restroom_A",
    "start_minute": 495,  # 8h 15m from SIM_START = Day 1, 08:15
    "end_minute":   508,  # 8h 28m from SIM_START = Day 1, 08:28  (13 min)
    "flow_lpm":     7.5,
    "occupancy":    1,
}

# ── Detection thresholds (Section 4a) ─────────────────────────────────────────
BASELINE_SIGMA = 2.5         # flag if flow > mean + BASELINE_SIGMA × std
MIN_BASELINE_SAMPLES = 5     # minimum prior readings required before flagging;
                             # avoids spurious flags when history is near-empty
STD_FLOOR = 0.2              # minimum effective std to prevent degenerate zero-
                             # variance baselines at overnight hours.
                             # With floor: threshold = 0 + 2.5×0.2 = 0.5 LPM.
                             # Sustained leak (3.5 LPM) > 0.5 → caught.
                             # Slow drip (0.25 LPM) < 0.5 → not caught (by design).

# ── Phase 2 detection thresholds (Sections 4b, 4c) ───────────────────────────

# 4b — Multi-signal correlation
MIN_SESSION_DURATION_MINUTES = 10   # Sessions shorter than this are treated as
                                    # brief normal spikes (e.g. flush) and suppressed.
                                    # The false-positive shower (13 min, occ=1) passes
                                    # the duration gate but loses occupancy_mismatch credit.

# 4c — Slow-drip detection via cumulative flow in unoccupied overnight windows.
# Strategy: rather than a regression slope (which dilutes when most readings are
# zero-flow), we sum total flow over a 2-hour rolling window restricted to
# overnight + zero-occupancy minutes.  An idle fixture sums ≈ 0 L; the injected
# drip (0.25 LPM × 120 min) sums ≈ 30 L — well above the 10 L alert threshold.
SLOW_DRIP_WINDOW_MINUTES = 120           # rolling window width (2 hours)
SLOW_DRIP_CUMULATIVE_THRESHOLD_L = 10.0  # litres over window to trigger slow-drip flag
SLOW_DRIP_MIN_READINGS = 30             # ignore windows with fewer data points
SLOW_DRIP_OVERNIGHT_HOURS = (22, 6)     # inclusive start/exclusive end of "overnight"
                                        # 22:00–05:59 is expected to be unoccupied

# ── Severity scoring weights (Section 4d) ─────────────────────────────────────
W_FLOW_DEV      = 0.40   # normalised flow deviation above baseline
W_DURATION      = 0.30   # normalised session duration
W_OCC_MISMATCH  = 0.20   # 1.0 if all readings unoccupied, 0.0 if any occupancy=1
W_SENSOR_HEALTH = 0.10   # penalty if sensor_status is FAULT/OFFLINE

# Normalisation caps — values at or beyond these cap the component at 1.0
FLOW_DEV_CAP_LPM = 10.0   # flow deviation ≥ 10 LPM above baseline → component = 1.0
DURATION_CAP_MIN  = 60.0  # duration ≥ 60 min → component = 1.0

# Severity label buckets (score × 100 mapped to Low/Medium/High/Critical)
# score range: 0–100
SEVERITY_CRITICAL_THRESHOLD = 76
SEVERITY_HIGH_THRESHOLD     = 51
SEVERITY_MEDIUM_THRESHOLD   = 26
# Below 26 → Low

# ── Business impact (used from Phase 2 onwards) ───────────────────────────────
# Assumption: Indian municipal commercial water rate ≈ ₹50 per 1,000 litres.
# Midpoint of BWSSB (Bangalore) / MCGM (Mumbai) commercial slab tariffs.
# State this assumption clearly in interviews and the prompts doc.
WATER_COST_PER_LITER = 0.05  # ₹ per litre

# ── Dashboard ─────────────────────────────────────────────────────────────────
DASHBOARD_REFRESH_SECONDS = 5    # full dataset auto-refresh interval
REPLAY_REFRESH_SECONDS = 3       # replay mode step interval (faster for demo)
