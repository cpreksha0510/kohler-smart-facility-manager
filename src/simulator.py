"""
simulator.py — 48-hour batch sensor data generator, v2 (discrete event model).

Generates realistic sensor readings for 16 fixtures across 4 zones (Terminal 2
airport restroom block), then overlays three precisely-specified anomalies.

Key change from v1: discrete event model
-----------------------------------------
In v1, each fixture generated a continuous noisy flow stream.  Real fixtures are
idle (flow = 0.0) nearly all the time and produce short sharp bursts on use.
This version models each use as a discrete Poisson-distributed event:

  1. For each minute, sample n_events from Poisson(rate_per_minute).
  2. If n_events > 0, compute the flow for that row:
       flow_lpm = event_volume_L / (event_duration_sec / 60)
     occupancy is set to 1 for the event minute, with optional pre/post buffers.
  3. If n_events == 0, flow = 0.0, occupancy = 0.

Event rates are calibrated to a realistic airport departure/arrival traffic curve.
Zone traffic multipliers scale per-zone busyness relative to the busy departure
restroom (T2_Restroom_A).

Anomaly injection (unchanged from v1):
  [1] Sustained leak  : Sink_01,   Day 2 02:00–06:00, 3.5 LPM, occ=0
  [2] Slow drip       : Toilet_B1, Day 2 00:00–08:00, 0.25 LPM, occ=0
  [3] False-positive  : Sink_02,   Day 1 08:15–08:28, 7.5 LPM, occ=1

Usage:
    python src/simulator.py            # batch mode (default)
    python src/simulator.py --seed 99  # change random seed
    python src/simulator.py --preview  # 6-hour preview, 3 fixtures only

Output:
    facility.db at the project root, sensor_readings table populated.
    (~46,080 rows = 48 h × 60 min × 16 fixtures)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    SIM_START, SIM_DURATION_HOURS, READING_INTERVAL_MINUTES,
    FIXTURES, EVENT_PARAMS, BASE_EVENTS_PER_HOUR, ZONE_TRAFFIC_MULTIPLIER,
    ANOMALY_SCHEDULE,
    DB_PATH,
)
from src.database import init_db, insert_readings_df


# ── Helpers ────────────────────────────────────────────────────────────────────

def build_timestamps(duration_hours: int = SIM_DURATION_HOURS) -> list:
    """Return list of datetimes for every minute of the simulation window."""
    total_minutes = duration_hours * 60 // READING_INTERVAL_MINUTES
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
    Simulate one fixture's readings using a discrete event model.

    Algorithm
    ---------
    For each 1-minute slot:
      1. Check anomaly windows (takes priority over normal simulation).
      2. Sample n_events ~ Poisson(rate_per_minute × zone_multiplier).
      3. If n_events > 0:
           - Sample event volume and duration for each event.
           - flow_lpm = total_volume / (total_duration_sec / 60)
           - Set occupancy = 1 for this minute ± pre/post buffer minutes.
      4. Else: flow = 0.0, occupancy = 0.

    Why Poisson?
    The Poisson distribution naturally models the number of independent events
    in a fixed time interval, which is exactly what foot traffic to a fixture is.
    At low rates (overnight), Poisson(0.001) ≈ almost always 0.  At peak hours,
    Poisson(0.04) gives ~2.4 events per hour per fixture — realistic for a busy
    commercial restroom.

    Occupancy buffers (pre/post minutes)
    Occupancy = 1 during the use event.  Sinks also set occupancy = 1 for 1 min
    before (person walking in) and 1 min after (drying hands).  Toilets set
    occupancy = 1 for 1 min before the flush.  This creates realistic occupancy
    patterns where the sensor reads 1 slightly before and after actual flow.
    """
    n = len(timestamps)
    flows      = np.zeros(n, dtype=float)
    occupancy  = np.zeros(n, dtype=int)
    flush_cnt  = np.zeros(n, dtype=int)
    status_arr = ["OK"] * n

    params           = EVENT_PARAMS[fixture_type]
    zone_multiplier  = ZONE_TRAFFIC_MULTIPLIER.get(zone_id, 1.0)
    flush_count      = 0

    # Pre-compute occupancy buffer indices (set after main loop)
    occ_buffer_indices: set[int] = set()

    for i, ts in enumerate(timestamps):
        minute_offset = i
        hour = ts.hour

        # ── Anomaly injection (priority over normal simulation) ────────────────
        injected = False
        for anomaly in ANOMALY_SCHEDULE:
            if fixture_id != anomaly["fixture_id"]:
                continue

            match = False
            if "start_hour" in anomaly and "end_hour" in anomaly:
                match = in_hour_window(minute_offset, anomaly["start_hour"], anomaly["end_hour"])
            elif "start_minute" in anomaly and "end_minute" in anomaly:
                match = in_minute_window(minute_offset, anomaly["start_minute"], anomaly["end_minute"])

            if match:
                noise_scale = 0.02 if anomaly["flow_lpm"] < 1.0 else 0.05
                flows[i]     = max(0.0, anomaly["flow_lpm"] + rng.normal(0, noise_scale))
                occupancy[i] = anomaly["occupancy"]
                flush_cnt[i] = flush_count
                injected = True
                break

        if injected:
            continue

        # ── Normal discrete-event simulation ──────────────────────────────────

        # Poisson rate for this minute
        base_rate  = BASE_EVENTS_PER_HOUR.get(hour, 0.05) / 60.0
        rate       = base_rate * zone_multiplier
        n_events   = int(rng.poisson(rate))

        if n_events > 0:
            total_volume_L = 0.0
            for _ in range(n_events):
                vol = rng.uniform(params["volume_L"]["min"], params["volume_L"]["max"])
                # duration sampled for physical realism but not used in flow calc
                _dur = rng.uniform(params["duration_sec"]["min"], params["duration_sec"]["max"])
                total_volume_L += vol
                flush_count    += 1

            # Flow rate = volume delivered in this 1-minute slot (L/min = L per row).
            # "Average over the slot" representation:
            #   - 5L toilet flush in 1-min slot  -> 5.0 LPM
            #   - 1.5L handwash                  -> 1.5 LPM
            #   - Sustained leak at 3.5 LPM      -> clearly above normal range
            # Avoids the misleading instantaneous rate (e.g. 40 LPM for a 10-sec
            # flush) that makes anomaly lines hard to distinguish visually.
            noise      = rng.normal(0, total_volume_L * 0.04)
            flows[i]   = round(max(0.0, total_volume_L + noise), 3)
            occupancy[i] = 1

            # Occupancy buffer: mark surrounding minutes
            pre  = params.get("occ_pre_min",  0)
            post = params.get("occ_post_min", 0)
            for delta in range(-pre, post + 1):
                idx = i + delta
                if 0 <= idx < n and idx != i:
                    occ_buffer_indices.add(idx)
        # else: flow = 0.0, occupancy = 0 (already zeroed by np.zeros)

        flush_cnt[i] = flush_count

    # Apply occupancy buffers (only where not already set by an event or anomaly)
    for idx in occ_buffer_indices:
        if occupancy[idx] == 0:
            occupancy[idx] = 1

    return pd.DataFrame({
        "timestamp":              [ts.isoformat() for ts in timestamps],
        "zone_id":                zone_id,
        "fixture_id":             fixture_id,
        "flow_rate_lpm":          flows.round(3),
        "occupancy":              occupancy,
        "flush_count_cumulative": flush_cnt,
        "sensor_status":          status_arr,
    })


# ── Preview mode (sample only) ─────────────────────────────────────────────────

def run_preview(random_seed: int = 42) -> None:
    """
    Generate 6 hours of data for 3 representative fixtures and print a sample.
    Used to validate the discrete event model before full 48h generation.
    """
    print("=" * 70)
    print("KOHLER Simulator — PREVIEW MODE (6h, 3 fixtures)")
    print("=" * 70)

    preview_fixtures = [
        ("T2_Restroom_A", "Sink_01",   "sink"),      # departure zone sink
        ("T2_Restroom_A", "Toilet_A1", "toilet"),    # departure zone toilet
        ("T2_Family_Room", "Sink_06",  "sink"),      # low-traffic zone sink
    ]

    # Use hours 06:00–12:00 (straddles the morning peak — most interesting)
    preview_start = SIM_START + pd.Timedelta(hours=6)
    preview_ts = [
        preview_start + pd.Timedelta(minutes=i)
        for i in range(6 * 60)
    ]

    rng = np.random.default_rng(random_seed)

    for zone_id, fixture_id, fixture_type in preview_fixtures:
        print(f"\n{'-' * 60}")
        print(f"  {fixture_id}  ({fixture_type})  in  {zone_id}")
        print(f"{'-' * 60}")

        df = simulate_fixture(fixture_id, zone_id, fixture_type, preview_ts, rng)

        # Stats
        flows = df["flow_rate_lpm"]
        events = df[df["flow_rate_lpm"] > 0.1]
        print(f"  Rows         : {len(df)}")
        print(f"  Use events   : {len(events)}  (minutes with flow > 0.1 LPM)")
        print(f"  Flow range   : {flows.min():.3f} – {flows.max():.3f} LPM")
        print(f"  Mean (all)   : {flows.mean():.3f} LPM  (most mins = 0)")
        print(f"  Mean (events): {events['flow_rate_lpm'].mean():.2f} LPM")
        print(f"  Total volume : {flows.sum():.1f} L  over 6 hours")

        # Show 20 rows spanning 08:00–08:20 (peak period)
        peak_start = preview_start + pd.Timedelta(hours=2)  # = 08:00
        sample = df[
            pd.to_datetime(df["timestamp"]) >= peak_start
        ].head(20)

        print(f"\n  Sample — 08:00 to 08:20 (peak window):")
        print(f"  {'Timestamp':<22} {'Flow (LPM)':>10} {'Occ':>5} {'Flush#':>7}")
        print(f"  {'─'*22} {'─'*10} {'─'*5} {'─'*7}")
        for _, row in sample.iterrows():
            ts_str = str(row["timestamp"])[-8:-3]   # HH:MM
            flow   = row["flow_rate_lpm"]
            occ    = row["occupancy"]
            fl     = row["flush_count_cumulative"]
            marker = " <-- event" if flow > 0.1 else ""
            print(f"  {ts_str:<22} {flow:>10.3f} {occ:>5} {fl:>7}{marker}")

    print("\n[OK] Preview complete.")
    print("\nIf this looks realistic, approve to run the full 48-hour simulation.")


# ── Batch mode ─────────────────────────────────────────────────────────────────

def run_batch(random_seed: int = 42) -> None:
    """
    Generate all 48h of readings for all 16 fixtures and write to SQLite.
    Deterministic given the same seed.
    """
    print("=" * 70)
    print("KOHLER Smart Facility Manager -- Simulator v2 (discrete event model)")
    print("=" * 70)
    print(f"  Random seed   : {random_seed}")
    print(f"  Sim window    : {SIM_START}  ->  +{SIM_DURATION_HOURS}h")
    print(f"  Fixtures      : {len(FIXTURES)}")
    print(f"  Expected rows : {SIM_DURATION_HOURS * 60 * len(FIXTURES):,}")
    print()

    print("Initialising database (clearing old readings)...")
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("DELETE FROM sensor_readings")
    conn.execute("DELETE FROM tickets")
    conn.commit()
    conn.close()
    init_db(str(DB_PATH))

    print("Building timestamps...")
    timestamps = build_timestamps()

    rng    = np.random.default_rng(random_seed)
    frames = []

    for zone_id, fixture_id, fixture_type in FIXTURES:
        print(f"  Simulating  {fixture_id:<12} ({fixture_type:<7}) in {zone_id}...")
        df = simulate_fixture(fixture_id, zone_id, fixture_type, timestamps, rng)
        frames.append(df)

    combined = (
        pd.concat(frames, ignore_index=True)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    print(f"\nWriting {len(combined):,} rows to {DB_PATH}...")
    insert_readings_df(str(DB_PATH), combined)

    print("\n[OK] Done.")
    print(f"  Rows written : {len(combined):,}")
    print(f"  Date range   : {combined['timestamp'].iloc[0]}  ->  {combined['timestamp'].iloc[-1]}")

    # Event density summary
    print("\nEvent density check (rows with flow > 0.1 LPM):")
    event_rows = combined[combined["flow_rate_lpm"] > 0.1]
    print(f"  Total event rows  : {len(event_rows):,}  ({len(event_rows)/len(combined)*100:.1f}% of rows)")
    print(f"  Mean event flow   : {event_rows['flow_rate_lpm'].mean():.2f} LPM")
    print(f"  Max flow recorded : {combined['flow_rate_lpm'].max():.2f} LPM")

    print("\nInjected anomaly windows (Multi-zone 7-day schedule):")
    for idx, a in enumerate(ANOMALY_SCHEDULE, 1):
        fid = a["fixture_id"]
        zid = a["zone_id"]
        flow = a["flow_lpm"]
        atype = a["anomaly_type"]
        if "start_hour" in a:
            day = (a["start_hour"] // 24) + 1
            sh = a["start_hour"] % 24
            eh = a["end_hour"] % 24
            print(f"  [{idx}] {atype:<19} - {fid:<10} ({zid:<14}) Day {day} {sh:02d}:00->{eh:02d}:00 @ {flow} LPM")
        elif "start_minute" in a:
            day = (a["start_minute"] // 1440) + 1
            sm = a["start_minute"] % 1440
            em = a["end_minute"] % 1440
            print(f"  [{idx}] {atype:<19} - {fid:<10} ({zid:<14}) Day {day} {sm//60:02d}:{sm%60:02d}->{em//60:02d}:{em%60:02d} @ {flow} LPM")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KOHLER Facility — sensor data simulator v2"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Run 6-hour preview for 3 fixtures only (no DB write)"
    )
    args = parser.parse_args()

    if args.preview:
        run_preview(random_seed=args.seed)
    else:
        run_batch(random_seed=args.seed)


if __name__ == "__main__":
    main()
