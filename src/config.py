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
# Terminal 2 Restroom Block — four zones, sixteen fixtures.
#
# Zone layout:
#   T2_Restroom_A  — departure side, heaviest traffic (9 fixtures)
#   T2_Restroom_B  — arrival side, medium traffic    (4 fixtures)
#   T2_Family_Room — accessible/family, low traffic  (2 fixtures)
#   T2_Staff_WC    — staff only, very low traffic    (2 fixtures)  [includes urinal as toilet type]
#
# fixture_type: "sink" | "toilet" | "urinal"
FIXTURES = [
    # ── T2_Restroom_A (departure side) ────────────────────────────────────────
    ("T2_Restroom_A", "Sink_01",    "sink"),      # anomaly 1: sustained leak target
    ("T2_Restroom_A", "Sink_02",    "sink"),      # anomaly 3: false-positive trap
    ("T2_Restroom_A", "Sink_03",    "sink"),
    ("T2_Restroom_A", "Toilet_A1",  "toilet"),
    ("T2_Restroom_A", "Toilet_A2",  "toilet"),
    ("T2_Restroom_A", "Toilet_A3",  "toilet"),
    ("T2_Restroom_A", "Urinal_A1",  "urinal"),
    ("T2_Restroom_A", "Urinal_A2",  "urinal"),
    # ── T2_Restroom_B (arrival side) ──────────────────────────────────────────
    ("T2_Restroom_B", "Sink_04",    "sink"),
    ("T2_Restroom_B", "Sink_05",    "sink"),
    ("T2_Restroom_B", "Toilet_B1",  "toilet"),   # anomaly 2: slow drip target
    ("T2_Restroom_B", "Toilet_B2",  "toilet"),
    ("T2_Restroom_B", "Urinal_B1",  "urinal"),
    # ── T2_Family_Room ────────────────────────────────────────────────────────
    ("T2_Family_Room", "Sink_06",   "sink"),
    ("T2_Family_Room", "Toilet_F1", "toilet"),
    # ── T2_Staff_WC ───────────────────────────────────────────────────────────
    ("T2_Staff_WC",   "Sink_07",    "sink"),
    ("T2_Staff_WC",   "Toilet_S1",  "toilet"),
]

# ── Zone traffic multipliers ──────────────────────────────────────────────────
# Applied to the base event rate; modifies how busy each zone is relative to
# the main departure restroom (T2_Restroom_A = 1.0 baseline).
ZONE_TRAFFIC_MULTIPLIER = {
    "T2_Restroom_A":  1.00,   # departure side — busiest
    "T2_Restroom_B":  0.70,   # arrival side — moderately busy
    "T2_Family_Room": 0.25,   # family/accessible — low throughput
    "T2_Staff_WC":    0.12,   # staff only — very low
}

# ── Discrete event model — flow parameters ────────────────────────────────────
# Each fixture type has a volume_per_event distribution (litres) and a
# duration_seconds distribution.  The flow_rate_lpm for the event's 1-minute
# row is: event_volume_L / (event_duration_sec / 60)
#
# Values sourced from KOHLER commercial fixture specs and ASHRAE plumbing guides.
EVENT_PARAMS = {
    "sink": {
        "volume_L":      {"min": 0.5,  "max": 2.5},   # 0.5–2.5 L per handwash
        "duration_sec":  {"min": 15,   "max": 45},     # 15–45 second wash
        # Occupancy extends 1 min before (walking in) + 1 min after (drying)
        "occ_pre_min":  1,
        "occ_post_min": 1,
    },
    "toilet": {
        "volume_L":      {"min": 4.8,  "max": 6.0},   # 4.8–6.0 L per dual-flush
        "duration_sec":  {"min": 5,    "max": 12},     # 5–12 second flush cycle
        "occ_pre_min":  1,   # stall occupied before flush
        "occ_post_min": 0,   # person leaves immediately after
    },
    "urinal": {
        "volume_L":      {"min": 1.5,  "max": 2.5},   # 1.5–2.5 L per flush
        "duration_sec":  {"min": 3,    "max": 8},      # 3–8 second flush
        "occ_pre_min":  0,
        "occ_post_min": 0,
    },
}

# ── Airport traffic curve: base use-events per fixture per hour ───────────────
# Represents a single fixture in the busiest zone (T2_Restroom_A).
# Zone multipliers are applied on top of these rates.
# Calibrated so peak-hour sinks see ~2–3 uses/hour per fixture (realistic for
# a busy commercial airport restroom with adequate fixture count).
BASE_EVENTS_PER_HOUR = {
     0: 0.05,   # 00:00 — near-silent, occasional red-eye traveller
     1: 0.03,
     2: 0.02,
     3: 0.02,
     4: 0.06,
     5: 0.80,   # 05:00 — early crew/cleaning + first departures
     6: 3.00,   # 06:00 — first departure bank opens
     7: 5.00,   # 07:00 — morning peak begins
     8: 6.50,   # 08:00 — heaviest departure bank (~6 uses/fixture/hr)
     9: 5.50,
    10: 4.00,
    11: 3.50,
    12: 3.80,   # 12:00 — midday pickup
    13: 3.50,
    14: 3.00,
    15: 2.80,
    16: 3.20,
    17: 4.50,   # 17:00 — evening departure bank
    18: 5.50,   # 18:00 — second peak
    19: 5.00,
    20: 3.80,
    21: 2.50,
    22: 1.20,
    23: 0.40,   # 23:00 — last flights, winding down
}

# ── Legacy aliases — kept so detector.py import doesn't break ─────────────────
# (detector imports OCCUPANCY_PROB indirectly via config; these are not used
#  in the new simulator but retained for backward compatibility with any code
#  that still references them)
OCCUPANCY_PROB = {h: min(v / 2.5, 1.0) for h, v in BASE_EVENTS_PER_HOUR.items()}
FLOW_RATES = {
    "sink":   {"min": 2.0,  "max": 6.0},
    "toilet": {"min": 24.0, "max": 72.0},   # derived: 4.8–6L / 5–12sec × 60
    "urinal": {"min": 11.0, "max": 50.0},   # derived: 1.5–2.5L / 3–8sec × 60
}
EVENT_DURATION = {
    "sink":   {"min": 0.25, "max": 0.75},
    "toilet": {"min": 0.08, "max": 0.20},
    "urinal": {"min": 0.05, "max": 0.13},
}

# ── Anomaly injection windows ──────────────────────────────────────────────────

# Anomaly 1: Sustained leak — Sink_01, Day 2 02:00–06:00
# 3.5 LPM continuous flow with zero occupancy.
# Against the new discrete-event baseline, overnight flow = exactly 0.0 LPM
# (no events occur), so 3.5 LPM is a stark flat line against a zero background —
# exactly what a stuck-valve or pipe-joint failure looks like on a real sensor.
ANOMALY_SUSTAINED_LEAK = {
    "fixture_id": "Sink_01",
    "zone_id":    "T2_Restroom_A",
    "start_hour": 26,     # hour 26 from SIM_START = Day 2, 02:00
    "end_hour":   30,     # hour 30 from SIM_START = Day 2, 06:00
    "flow_lpm":   3.5,
    "occupancy":  0,
}

# Anomaly 2: Slow drip — Toilet_B1, Day 2 00:00–08:00
# 0.25 LPM tiny trickle with zero occupancy.
# INTENTIONALLY below the 4a detection threshold (threshold ≈ 0.5 LPM overnight).
# Against the new baseline, overnight toilet flow = 0.0 LPM, so even 0.25 LPM
# accumulates visibly in the 4c cumulative window scan.
# Phase 2 (Section 4c) catches this; Phase 1 (4a) misses it by design.
ANOMALY_SLOW_DRIP = {
    "fixture_id": "Toilet_B1",
    "zone_id":    "T2_Restroom_B",
    "start_hour": 24,     # Day 2, 00:00
    "end_hour":   32,     # Day 2, 08:00
    "flow_lpm":   0.25,
    "occupancy":  0,
}

# Anomaly 3: False-positive trap — Sink_02, Day 1 08:15–08:28
# High flow (7.5 LPM) with occupancy = 1 during morning rush.
# In the new discrete-event model, a normal sink wash lasts 15–45 seconds
# (1 row).  This anomaly runs for 13 consecutive rows at high flow — anomalous
# duration against a realistic baseline that rarely exceeds 1–2 rows per event.
# Occupancy = 1 throughout. Phase 2 (4b) suppresses it via occ_mismatch = 0.
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
MIN_BASELINE_SAMPLES = 5     # minimum prior readings required before flagging
STD_FLOOR = 0.2              # minimum effective std to prevent zero-variance
                             # baselines at overnight hours (threshold = 0.5 LPM)

# ── Phase 2 detection thresholds (Sections 4b, 4c) ───────────────────────────

# 4b — Multi-signal correlation
MIN_SESSION_DURATION_MINUTES = 10   # sessions shorter than this are suppressed

# 4c — Slow-drip cumulative detection
SLOW_DRIP_WINDOW_MINUTES = 120
SLOW_DRIP_CUMULATIVE_THRESHOLD_L = 10.0
SLOW_DRIP_MIN_READINGS = 30
SLOW_DRIP_OVERNIGHT_HOURS = (22, 6)

# ── Severity scoring weights (Section 4d) ─────────────────────────────────────
W_FLOW_DEV      = 0.40
W_DURATION      = 0.30
W_OCC_MISMATCH  = 0.20
W_SENSOR_HEALTH = 0.10

FLOW_DEV_CAP_LPM = 10.0
DURATION_CAP_MIN  = 60.0

SEVERITY_CRITICAL_THRESHOLD = 76
SEVERITY_HIGH_THRESHOLD     = 51
SEVERITY_MEDIUM_THRESHOLD   = 26

# ── Business impact ───────────────────────────────────────────────────────────
# Rs. 0.05 per litre = Rs. 50 per 1,000 litres.
# Source: midpoint of BWSSB (Bangalore) / MCGM (Mumbai) commercial slab tariffs.
WATER_COST_PER_LITER = 0.05   # Rs. per litre

# ── Dashboard ─────────────────────────────────────────────────────────────────
DASHBOARD_REFRESH_SECONDS = 5
REPLAY_REFRESH_SECONDS = 3

# ── Phase 3: LLM Layer (Section 5) ───────────────────────────────────────────
GEMINI_MODEL_PRIMARY        = "gemini-3.5-flash-lite"
GEMINI_MODEL_FALLBACK       = "gemini-3.6-flash"
LLM_MAX_RETRIES             = 1
LLM_RETRY_BACKOFF_SECONDS   = 2.0
LLM_REQUEST_DELAY_SECONDS   = 0.6   # paces requests to respect Gemini free-tier RPM

