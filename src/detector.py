"""
detector.py — Phase 1 detection: Section 4a (adaptive baseline) only.

Algorithm
---------
For each (fixture_id, hour_of_day) pair, maintain an EXPANDING history of
flow_rate_lpm values processed in chronological order.  A reading is flagged
as an outlier when:

    flow_rate_lpm  >  mean(prior_history) + BASELINE_SIGMA × max(std(prior_history), STD_FLOOR)

Key design choices (interview-ready explanations):

1. Expanding window, not rolling
   With only 48 h of data, each hour-of-day slot has at most ~60 prior
   readings (one hour from Day 1).  A rolling window over k readings would
   work fine in production (weeks of history), but here we use an expanding
   window so we always use all available prior data rather than an arbitrary
   k that we might not have enough rows to fill.

2. STD_FLOOR = 0.2
   Overnight (00:00–05:00) almost all readings are zero-flow.  This makes
   std ≈ 0, which would make the threshold 0 and flag any tiny drip.  A floor
   of 0.2 LPM means the minimum threshold is 0 + 2.5×0.2 = 0.5 LPM — enough
   to catch the 3.5 LPM sustained leak but not the 0.25 LPM slow drip.
   The slow drip is intentionally a Phase 2 (4c) catch.

3. Self-contamination prevention
   Each reading is added to history AFTER it has been evaluated against the
   existing baseline — so no reading is compared to a baseline that includes
   itself.

4. Session grouping
   Consecutive outlier readings (gap ≤ 2 min) are merged into one session /
   one ticket.  This prevents 240 individual tickets for a 4-hour leak.

Known Phase 1 limitations (by design — addressed in Phase 2):
  - Slow drip (0.25 LPM) NOT caught — below 0.5 LPM threshold at overnight hours
  - False positive (long handwash, occupancy=1) MAY be flagged — Phase 2 (4b)
    will suppress it using the occupancy signal
  - All tickets labelled anomaly_type="sustained_leak" — Phase 2 differentiates
  - severity_score and estimated_cost_impact are None — Phase 2 fills these
  - explanation is blank — Phase 3 LLM fills this

Usage:
    python src/detector.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    BASELINE_SIGMA, MIN_BASELINE_SAMPLES, STD_FLOOR, DB_PATH,
)
from src.database import get_readings_df, get_tickets_df, insert_ticket


# ── Step 1: Compute per-reading outlier flag ───────────────────────────────────

def compute_outlier_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'is_outlier', 'baseline_mean', 'baseline_std', and 'threshold' columns
    to the readings DataFrame.

    Processes each fixture independently, iterating chronologically so that the
    baseline for each (fixture, hour_of_day) is built only from prior readings.
    """
    df = df.copy()
    df["timestamp"]   = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Pre-allocate result columns
    n = len(df)
    bl_mean  = np.full(n, np.nan)
    bl_std   = np.full(n, np.nan)
    bl_thresh = np.full(n, np.nan)
    is_out   = np.zeros(n, dtype=bool)

    for fixture_id, group in df.groupby("fixture_id", sort=False):
        group = group.sort_values("timestamp")
        # Separate history per hour-of-day bucket
        hour_history: dict[int, list[float]] = {h: [] for h in range(24)}

        for idx, row in group.iterrows():
            h       = int(row["hour_of_day"])
            history = hour_history[h]

            if len(history) >= MIN_BASELINE_SAMPLES:
                mean_v  = float(np.mean(history))
                std_v   = float(np.std(history))
                eff_std = max(std_v, STD_FLOOR)   # prevent degenerate zero-variance case
                thresh  = mean_v + BASELINE_SIGMA * eff_std

                bl_mean[idx]   = mean_v
                bl_std[idx]    = std_v
                bl_thresh[idx] = thresh

                if row["flow_rate_lpm"] > thresh:
                    is_out[idx] = True

            # Add AFTER checking — prevents self-contamination of baseline
            hour_history[h].append(float(row["flow_rate_lpm"]))

    df["baseline_mean"] = bl_mean
    df["baseline_std"]  = bl_std
    df["threshold"]     = bl_thresh
    df["is_outlier"]    = is_out

    return df


# ── Step 2: Group consecutive outliers into sessions ───────────────────────────

def group_into_sessions(df: pd.DataFrame, max_gap_minutes: int = 2) -> list[dict]:
    """
    Merge consecutive outlier readings (gap ≤ max_gap_minutes) into sessions.
    Returns a list of session dicts summarising each anomaly window.
    """
    sessions = []

    for fixture_id, fix_df in df.groupby("fixture_id", sort=False):
        outliers = fix_df[fix_df["is_outlier"]].sort_values("timestamp")
        if outliers.empty:
            continue

        current: list = [outliers.iloc[0]]

        for i in range(1, len(outliers)):
            prev_ts = current[-1]["timestamp"]
            curr_ts = outliers.iloc[i]["timestamp"]
            gap_min = (curr_ts - prev_ts).total_seconds() / 60.0

            if gap_min <= max_gap_minutes:
                current.append(outliers.iloc[i])
            else:
                sessions.append(_summarise_session(fixture_id, current))
                current = [outliers.iloc[i]]

        sessions.append(_summarise_session(fixture_id, current))   # flush last

    return sessions


def _summarise_session(fixture_id: str, rows: list) -> dict:
    """Build a summary dict from a list of outlier row Series."""
    first = rows[0]
    last  = rows[-1]
    flows = [float(r["flow_rate_lpm"]) for r in rows]

    return {
        "fixture_id":       fixture_id,
        "zone_id":          str(first["zone_id"]),
        "start_ts":         first["timestamp"],
        "end_ts":           last["timestamp"],
        "duration_minutes": len(rows),          # 1 row = 1 minute at our sampling rate
        "avg_flow_lpm":     round(float(np.mean(flows)), 3),
        "max_flow_lpm":     round(float(np.max(flows)), 3),
        "occupancy_values": [int(r["occupancy"]) for r in rows],
    }


# ── Step 3: Convert sessions → tickets ────────────────────────────────────────

def session_to_ticket(session: dict) -> dict:
    """
    Map a session summary dict to the ticket schema from Section 3.
    Phase 1 placeholders: anomaly_type fixed, severity/cost deferred.
    """
    duration  = session["duration_minutes"]
    avg_flow  = session["avg_flow_lpm"]
    water_loss = round(avg_flow * duration, 2)  # flow_rate_lpm × duration_minutes = litres

    ts_str = session["start_ts"]
    if hasattr(ts_str, "strftime"):
        ts_fmt = ts_str.strftime("%Y%m%d%H%M")
        ts_iso = ts_str.isoformat()
    else:
        ts_fmt = str(ts_str).replace("-", "").replace(":", "").replace(" ", "")[:12]
        ts_iso = str(ts_str)

    return {
        "ticket_id":                   f"TKT-{session['fixture_id']}-{ts_fmt}",
        "timestamp_flagged":           ts_iso,
        "zone_id":                     session["zone_id"],
        "fixture_id":                  session["fixture_id"],
        "anomaly_type":                "sustained_leak",   # Phase 1 placeholder; Phase 2 refines
        "severity_score":              None,               # Phase 2 (Section 4d)
        "severity_label":              "Flagged",          # Phase 2 buckets this
        "explanation":                 "",                 # Phase 3 LLM
        "estimated_water_loss_liters": water_loss,
        "estimated_cost_impact":       None,               # Phase 2 (Section 4e)
        "status":                      "open",
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def run_detection() -> None:
    print("=" * 60)
    print("KOHLER Smart Facility Manager — Detector (Phase 1 / 4a)")
    print("=" * 60)

    print("\nLoading readings from database...")
    df = get_readings_df(str(DB_PATH))
    if df.empty:
        print("  [!] No readings found. Run simulator first:\n    python src/simulator.py")
        return
    print(f"  Loaded {len(df):,} rows across {df['fixture_id'].nunique()} fixtures.")

    print("\nComputing adaptive baselines and outlier flags...")
    flagged = compute_outlier_flags(df)
    n_outliers = int(flagged["is_outlier"].sum())
    print(f"  Individual outlier readings : {n_outliers:,}")

    if n_outliers == 0:
        print("  [!] No outliers detected. Check STD_FLOOR and BASELINE_SIGMA in config.py")
        return

    print("\nGrouping consecutive outliers into sessions...")
    sessions = group_into_sessions(flagged)
    print(f"  Sessions found : {len(sessions)}")
    print()

    for s in sessions:
        occ_mean = round(sum(s["occupancy_values"]) / len(s["occupancy_values"]), 2)
        print(
            f"  {s['fixture_id']:<12}  "
            f"{s['start_ts'].strftime('%b %d %H:%M')} -> {s['end_ts'].strftime('%H:%M')}  "
            f"({s['duration_minutes']:>4} min)  "
            f"avg {s['avg_flow_lpm']:.2f} LPM  "
            f"occ={occ_mean}"
        )

    print(f"\nWriting {len(sessions)} ticket(s) to database…")
    for session in sessions:
        ticket = session_to_ticket(session)
        insert_ticket(str(DB_PATH), ticket)

    print("\n[OK] Detection complete.")

    # ── Sanity check: verify sustained-leak ticket exists ─────────────────────
    tickets_df = get_tickets_df(str(DB_PATH))
    sink01_tickets = tickets_df[tickets_df["fixture_id"] == "Sink_01"]
    if not sink01_tickets.empty:
        print(f"\n  [OK] Definition of Done check: Sink_01 ticket(s) found -> {len(sink01_tickets)}")
    else:
        print("\n  [!] Warning: No Sink_01 tickets found - sustained leak may not have been caught.")


if __name__ == "__main__":
    run_detection()
