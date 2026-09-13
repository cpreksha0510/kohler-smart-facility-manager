"""
simulator.py — 48-hour batch sensor data generator for the airport restroom block.

Generates realistic sensor readings for 5 fixtures across 2 zones (Terminal 2),
with a probabilistic use-event model driven by hour-of-day occupancy patterns,
then overlays three precisely-specified anomalies:

  Anomaly 1 — Sustained leak  : Sink_01, Day 2 02:00–06:00, 3.5 LPM, zero occupancy
  Anomaly 2 — Slow drip       : Toilet_02, Day 2 00:00–08:00, 0.25 LPM, zero occupancy
  Anomaly 3 — False positive  : Sink_02, Day 1 08:15–08:28, 7.5 LPM, occupancy = 1

Usage:
    python src/simulator.py            # batch mode (default)
    python src/simulator.py --seed 99  # change random seed

Output:
    facility.db at the project root, sensor_readings table populated.
    (~14,400 rows = 48 h × 60 min × 5 fixtures)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── Path setup (run from any directory) ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    SIM_START, SIM_DURATION_HOURS, READING_INTERVAL_MINUTES,
    FIXTURES, FLOW_RATES, EVENT_DURATION, OCCUPANCY_PROB,
    ANOMALY_SUSTAINED_LEAK, ANOMALY_SLOW_DRIP, ANOMALY_FALSE_POSITIVE,
    DB_PATH,
)
from src.database import init_db, insert_readings_df


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_timestamps() -> list:
    """Return list of datetime objects for every minute of the 48h window."""
    total_minutes = SIM_DURATION_HOURS * 60 // READING_INTERVAL_MINUTES
    return [
        SIM_START + pd.Timedelta(minutes=i * READING_INTERVAL_MINUTES)
        for i in range(total_minutes)
    ]


def in_hour_window(minute_offset: int, start_hour: int, end_hour: int) -> bool:
    """True if minute_offset falls in [start_hour*60, end_hour*60)."""
    return start_hour * 60 <= minute_offset < end_hour * 60


def in_minute_window(minute_offset: int, start_minute: int, end_minute: int) -> bool:
    """True if minute_offset falls in [start_minute, end_minute)."""
    return start_minute <= minute_offset < end_minute


# ── Core simulator ─────────────────────────────────────────────────────────────

def simulate_fixture(
    fixture_id: str,
    zone_id: str,
    fixture_type: str,
    timestamps: list,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Simulate one fixture's readings for the full 48h window.

    Use-event model
    ---------------
    Each minute, if not currently in an event, draw from a Bernoulli with
    probability = OCCUPANCY_PROB[hour] × 0.15.  This gives roughly 10 use
    events per hour at peak (hour 8) and <1 per hour overnight — consistent
    with a busy commercial restroom fixture.

    When an event starts, sample flow and duration from realistic ranges, then
    hold those values for the event's duration (decrement remaining each minute).

    Anomaly injection takes priority over normal events.
    """
    n = len(timestamps)
    flows      = np.zeros(n, dtype=float)
    occupancy  = np.zeros(n, dtype=int)
    flush_cnt  = np.zeros(n, dtype=int)
    status_arr = ["OK"] * n

    flush_count    = 0
    in_event       = False
    event_remaining = 0
    event_flow     = 0.0

    flow_range = FLOW_RATES[fixture_type]
    dur_range  = EVENT_DURATION[fixture_type]

    for i, ts in enumerate(timestamps):
        minute_offset = i   # minutes since SIM_START
        hour = ts.hour

        # ── Anomaly injection (takes priority over normal simulation) ──────────

        # Anomaly 1: Sustained leak on Sink_01
        if (
            fixture_id == ANOMALY_SUSTAINED_LEAK["fixture_id"]
            and in_hour_window(minute_offset,
                               ANOMALY_SUSTAINED_LEAK["start_hour"],
                               ANOMALY_SUSTAINED_LEAK["end_hour"])
        ):
            flows[i]     = max(0.0, ANOMALY_SUSTAINED_LEAK["flow_lpm"] + rng.normal(0, 0.05))
            occupancy[i] = ANOMALY_SUSTAINED_LEAK["occupancy"]
            flush_cnt[i] = flush_count
            in_event = False   # suppress any in-progress normal event
            continue

        # Anomaly 2: Slow drip on Toilet_02
        if (
            fixture_id == ANOMALY_SLOW_DRIP["fixture_id"]
            and in_hour_window(minute_offset,
                               ANOMALY_SLOW_DRIP["start_hour"],
                               ANOMALY_SLOW_DRIP["end_hour"])
        ):
            flows[i]     = max(0.0, ANOMALY_SLOW_DRIP["flow_lpm"] + rng.normal(0, 0.02))
            occupancy[i] = ANOMALY_SLOW_DRIP["occupancy"]
            flush_cnt[i] = flush_count
            in_event = False
            continue

        # Anomaly 3: False-positive trap on Sink_02
        if (
            fixture_id == ANOMALY_FALSE_POSITIVE["fixture_id"]
            and in_minute_window(minute_offset,
                                 ANOMALY_FALSE_POSITIVE["start_minute"],
                                 ANOMALY_FALSE_POSITIVE["end_minute"])
        ):
            flows[i]     = max(0.0, ANOMALY_FALSE_POSITIVE["flow_lpm"] + rng.normal(0, 0.1))
            occupancy[i] = ANOMALY_FALSE_POSITIVE["occupancy"]
            flush_cnt[i] = flush_count
            in_event = False
            continue

        # ── Normal use-event simulation ────────────────────────────────────────
        if in_event:
            # Continue existing event
            flows[i]     = max(0.0, event_flow + rng.normal(0, 0.15))
            occupancy[i] = 1
            event_remaining -= 1
            if event_remaining <= 0:
                in_event = False
        else:
            # Probability of a new event starting this minute
            p_start = OCCUPANCY_PROB.get(hour, 0.01) * 0.15
            if rng.random() < p_start:
                in_event        = True
                event_flow      = rng.uniform(flow_range["min"], flow_range["max"])
                raw_duration    = rng.uniform(dur_range["min"], dur_range["max"])
                event_remaining = max(1, round(raw_duration)) - 1  # current minute counts
                flush_count    += 1
                flows[i]        = max(0.0, event_flow + rng.normal(0, 0.15))
                occupancy[i]    = 1
            # else: idle — flow=0, occupancy=0 (already zeroed by np.zeros)

        flush_cnt[i] = flush_count

    return pd.DataFrame({
        "timestamp":              [ts.isoformat() for ts in timestamps],
        "zone_id":                zone_id,
        "fixture_id":             fixture_id,
        "flow_rate_lpm":          flows.round(3),
        "occupancy":              occupancy,
        "flush_count_cumulative": flush_cnt,
        "sensor_status":          status_arr,
    })


# ── Batch mode ─────────────────────────────────────────────────────────────────

def run_batch(random_seed: int = 42) -> None:
    """
    Generate all 48h of readings in one pass and write to SQLite.
    Results are deterministic given the same seed.
    """
    print("=" * 60)
    print("KOHLER Smart Facility Manager — Simulator (batch mode)")
    print("=" * 60)
    print(f"  Random seed   : {random_seed}")
    print(f"  Sim window    : {SIM_START}  ->  +48 h")
    print(f"  Fixtures      : {len(FIXTURES)}")
    print(f"  Expected rows : {SIM_DURATION_HOURS * 60 * len(FIXTURES):,}")
    print()

    print("Initialising database...")
    init_db(str(DB_PATH))

    print("Building timestamps...")
    timestamps = build_timestamps()

    rng = np.random.default_rng(random_seed)
    frames = []

    for zone_id, fixture_id, fixture_type in FIXTURES:
        print(f"  Simulating  {fixture_id:<12} ({fixture_type}) in {zone_id}...")
        df = simulate_fixture(fixture_id, zone_id, fixture_type, timestamps, rng)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)

    print(f"\nWriting {len(combined):,} rows to {DB_PATH}...")
    insert_readings_df(str(DB_PATH), combined)

    print("\n[OK] Done.")
    print(f"  Rows written : {len(combined):,}")
    print(f"  Date range   : {combined['timestamp'].iloc[0]}  ->  {combined['timestamp'].iloc[-1]}")
    print()

    # ── Anomaly window summary ─────────────────────────────────────────────────
    print("Injected anomaly windows:")
    print(f"  [1] Sustained leak  - {ANOMALY_SUSTAINED_LEAK['fixture_id']:12}"
          f"  Day 2 {ANOMALY_SUSTAINED_LEAK['start_hour']-24:02d}:00 to {ANOMALY_SUSTAINED_LEAK['end_hour']-24:02d}:00"
          f"  @ {ANOMALY_SUSTAINED_LEAK['flow_lpm']} LPM, occ={ANOMALY_SUSTAINED_LEAK['occupancy']}")
    print(f"  [2] Slow drip       - {ANOMALY_SLOW_DRIP['fixture_id']:12}"
          f"  Day 2 {ANOMALY_SLOW_DRIP['start_hour']-24:02d}:00 to {ANOMALY_SLOW_DRIP['end_hour']-24:02d}:00"
          f"  @ {ANOMALY_SLOW_DRIP['flow_lpm']} LPM, occ={ANOMALY_SLOW_DRIP['occupancy']}  (Phase 2 target)")
    fp_start = ANOMALY_FALSE_POSITIVE['start_minute']
    fp_end   = ANOMALY_FALSE_POSITIVE['end_minute']
    print(f"  [3] False positive  - {ANOMALY_FALSE_POSITIVE['fixture_id']:12}"
          f"  Day 1 {fp_start//60:02d}:{fp_start%60:02d} to {fp_end//60:02d}:{fp_end%60:02d}"
          f"  @ {ANOMALY_FALSE_POSITIVE['flow_lpm']} LPM, occ={ANOMALY_FALSE_POSITIVE['occupancy']}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KOHLER Facility — sensor data simulator"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    args = parser.parse_args()
    run_batch(random_seed=args.seed)


if __name__ == "__main__":
    main()
