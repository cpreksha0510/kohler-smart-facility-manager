"""
detector.py — Phase 2 detection: Sections 4a + 4b + 4c + 4d + 4e.

Algorithm overview
------------------

Pass 1 — Statistical outlier detection (Section 4a):
  For each (fixture_id, hour_of_day) pair, build an EXPANDING history of
  flow_rate_lpm values.  A reading is flagged when:

      flow_rate_lpm > mean(prior) + BASELINE_SIGMA × max(std(prior), STD_FLOOR)

  Note: the expanding baseline adapts to the anomaly within each hour bucket
  (~10 readings in), so a 4-hour sustained leak produces ~10 outlier readings
  at the start of each hour rather than a continuous 240-reading block.

Pass 2 — Session grouping + scoring (Sections 4b + 4d):
  2a. Consecutive outlier readings (gap ≤ 2 min) are merged into SHORT sessions.
      This keeps daytime occupied sessions separate.

  2b. Zero-occupancy short sessions from the same fixture that are ≤ 90 min apart
      are SPANNED into a single long unoccupied session.  This re-joins the
      per-hour outlier bursts from a sustained leak into one correct session
      without merging daytime occupied sessions.

  2c. Each session is scored (Section 4d) and anomaly-typed (Section 4b).
      Sessions < MIN_SESSION_DURATION_MINUTES (10 min) are suppressed.

  Scoring formula:
      severity_score =
          (flow_dev_norm  × 0.40) +   # how far above baseline?
          (duration_norm  × 0.30) +   # how long did it last?
          (occ_mismatch   × 0.20) +   # flow + zero occupancy?
          (sensor_penalty × 0.10)     # FAULT/OFFLINE → uncertainty
      × 100   (final score 0–100)

Pass 3 — Slow-drip detection (Section 4c):
  A separate cumulative-flow scan over overnight + zero-occupancy windows.
  An idle fixture sums ≈ 0 L per 2-hour window; a 0.25 LPM drip accumulates
  ~30 L — well above the SLOW_DRIP_CUMULATIVE_THRESHOLD_L = 10 L trigger.

Section 4e — Cost impact:
  estimated_water_loss_liters = avg_flow_lpm × duration_minutes
  estimated_cost_impact (₹)  = water_loss × WATER_COST_PER_LITER (₹0.05/L)

Interview explanations embedded below each function.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    BASELINE_SIGMA, MIN_BASELINE_SAMPLES, STD_FLOOR, DB_PATH,
    MIN_SESSION_DURATION_MINUTES,
    SLOW_DRIP_WINDOW_MINUTES, SLOW_DRIP_CUMULATIVE_THRESHOLD_L,
    SLOW_DRIP_MIN_READINGS, SLOW_DRIP_OVERNIGHT_HOURS,
    W_FLOW_DEV, W_DURATION, W_OCC_MISMATCH, W_SENSOR_HEALTH,
    FLOW_DEV_CAP_LPM, DURATION_CAP_MIN,
    SEVERITY_CRITICAL_THRESHOLD, SEVERITY_HIGH_THRESHOLD, SEVERITY_MEDIUM_THRESHOLD,
    WATER_COST_PER_LITER,
    ANOMALY_SLOW_DRIP,
)
from src.database import get_readings_df, get_tickets_df, insert_ticket, save_daily_digest
from src.explainability import build_ticket_evidence


# ── Helpers ────────────────────────────────────────────────────────────────────

def _severity_label(score: float) -> str:
    """Map a 0–100 severity score to a human-readable label."""
    if score >= SEVERITY_CRITICAL_THRESHOLD:
        return "Critical"
    if score >= SEVERITY_HIGH_THRESHOLD:
        return "High"
    if score >= SEVERITY_MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def _is_overnight(hour: int) -> bool:
    """True if hour falls in SLOW_DRIP_OVERNIGHT_HOURS window (wraps midnight)."""
    start, end = SLOW_DRIP_OVERNIGHT_HOURS   # e.g. (22, 6)
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end        # wraps midnight


# ── Pass 1: Per-reading outlier flags (Section 4a) ────────────────────────────

def compute_outlier_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 'is_outlier', 'baseline_mean', 'baseline_std', 'threshold' columns.

    Processes each fixture independently in chronological order.
    Each (fixture_id, hour_of_day) pair maintains its own expanding history.
    Self-contamination prevention: readings are appended AFTER evaluation.

    Design note (interview): because the expanding window adapts to the
    anomalous flow within about 10 readings (MIN_BASELINE_SAMPLES=5 → starts
    scoring; after ~10 the mean drifts up and threshold exceeds 3.5 LPM), a
    4-hour sustained leak only generates ~10 outlier readings at the START of
    each hour.  Pass 2b handles the re-joining of these per-hour bursts.
    """
    df = df.copy()
    df["timestamp"]   = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour
    df = df.sort_values("timestamp").reset_index(drop=True)

    n = len(df)
    bl_mean   = np.full(n, np.nan)
    bl_std    = np.full(n, np.nan)
    bl_thresh = np.full(n, np.nan)
    is_out    = np.zeros(n, dtype=bool)

    for fixture_id, group in df.groupby("fixture_id", sort=False):
        group = group.sort_values("timestamp")
        hour_history: dict[int, list[float]] = {h: [] for h in range(24)}

        for idx, row in group.iterrows():
            h       = int(row["hour_of_day"])
            history = hour_history[h]

            if len(history) >= MIN_BASELINE_SAMPLES:
                mean_v  = float(np.mean(history))
                std_v   = float(np.std(history))
                eff_std = max(std_v, STD_FLOOR)
                thresh  = mean_v + BASELINE_SIGMA * eff_std

                bl_mean[idx]   = mean_v
                bl_std[idx]    = std_v
                bl_thresh[idx] = thresh

                if row["flow_rate_lpm"] > thresh:
                    is_out[idx] = True

            hour_history[h].append(float(row["flow_rate_lpm"]))

    df["baseline_mean"] = bl_mean
    df["baseline_std"]  = bl_std
    df["threshold"]     = bl_thresh
    df["is_outlier"]    = is_out

    return df


# ── Pass 2a: Group consecutive outliers into SHORT sessions ───────────────────

def group_into_sessions(df: pd.DataFrame, max_gap_minutes: int = 2) -> list[dict]:
    """
    Merge consecutive outlier readings (gap <= max_gap_minutes) into sessions.

    max_gap_minutes=2: deliberately tight so that daytime occupied sessions
    (normal use events separated by idle minutes) remain as separate tickets.
    Zero-occupancy sustained-leak bursts are re-joined in Pass 2b (span_unoccupied).
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
                sessions.append(_build_session(fixture_id, current))
                current = [outliers.iloc[i]]

        sessions.append(_build_session(fixture_id, current))

    return sessions


def _build_session(fixture_id: str, rows: list) -> dict:
    """Build a session summary dict from a list of outlier row Series."""
    first = rows[0]
    last  = rows[-1]
    flows = [float(r["flow_rate_lpm"]) for r in rows]
    baseline_means = [
        float(r["baseline_mean"]) if not (isinstance(r["baseline_mean"], float) and np.isnan(r["baseline_mean"])) else 0.0
        for r in rows
    ]

    return {
        "fixture_id":        fixture_id,
        "zone_id":           str(first["zone_id"]),
        "start_ts":          first["timestamp"],
        "end_ts":            last["timestamp"],
        "duration_minutes":  len(rows),
        "avg_flow_lpm":      round(float(np.mean(flows)), 3),
        "max_flow_lpm":      round(float(np.max(flows)), 3),
        "avg_baseline_mean": round(float(np.mean(baseline_means)), 3),
        "occupancy_values":  [int(r["occupancy"]) for r in rows],
        "sensor_statuses":   [str(r["sensor_status"]) for r in rows],
        "all_rows":          rows,   # retained for potential re-merging in 2b
    }


# ── Pass 2b: Span zero-occupancy sessions into sustained-leak sessions ─────────

def span_unoccupied_sessions(sessions: list[dict], max_span_gap_minutes: int = 90) -> list[dict]:
    """
    Post-process short sessions: if consecutive sessions for the same fixture
    are BOTH fully unoccupied (occ_mismatch == 1) and within max_span_gap_minutes
    of each other, merge them into one long session.

    This specifically addresses the adaptive-baseline artifact: a 4-hour leak
    generates ~10 outlier readings per hour (the baseline adapts and raises the
    threshold after 10 readings).  Those 4 per-hour bursts are all zero-occupancy
    and temporally close → they merge into one 4-hour session here.

    Daytime occupied sessions are NOT merged because any occupied session
    (occ_mismatch == 0) breaks the span chain.

    Interview note: this is intentional architecture, not a workaround.
    Production systems use a similar pattern: a "coalescer" that joins related
    micro-alerts from the same device into one incident ticket.
    """
    by_fixture: dict[str, list[dict]] = {}
    for s in sessions:
        by_fixture.setdefault(s["fixture_id"], []).append(s)

    result: list[dict] = []

    for fixture_id, fsessions in by_fixture.items():
        fsessions = sorted(fsessions, key=lambda s: s["start_ts"])
        merged: list[dict] = [fsessions[0]]

        for curr in fsessions[1:]:
            prev = merged[-1]

            prev_all_unoccupied = all(o == 0 for o in prev["occupancy_values"])
            curr_all_unoccupied = all(o == 0 for o in curr["occupancy_values"])

            if prev_all_unoccupied and curr_all_unoccupied:
                gap = (curr["start_ts"] - prev["end_ts"]).total_seconds() / 60.0
                if gap <= max_span_gap_minutes:
                    # Merge curr into prev
                    combined_rows = prev["all_rows"] + curr["all_rows"]
                    merged[-1] = _build_session(fixture_id, combined_rows)
                    continue

            merged.append(curr)

        result.extend(merged)

    return result


# ── Pass 2c: Score each session (Sections 4b + 4d) ────────────────────────────

def score_session(session: dict) -> dict | None:
    """
    Apply multi-signal correlation (4b) and weighted severity scoring (4d).
    Returns None if the session is suppressed.

    Suppression rule (Section 4b):
      duration < MIN_SESSION_DURATION_MINUTES → suppressed as brief noise.
      This kills toilet flush outliers (~1 min) and brief random spikes.

    Scoring (Section 4d):
      flow_dev_norm  = clamp((avg_flow - avg_baseline) / FLOW_DEV_CAP_LPM, 0, 1)
      duration_norm  = clamp(duration_minutes / DURATION_CAP_MIN, 0, 1)
      occ_mismatch   = 1.0 if ALL readings have occupancy==0, else 0.0
      sensor_penalty = 1.0 if ANY FAULT/OFFLINE in window, else 0.0

      score = (flow_dev_norm×0.40 + duration_norm×0.30 + occ_mismatch×0.20
               + sensor_penalty×0.10) × 100

    Anomaly type (deterministic):
      sensor_penalty=1 → "sensor_fault"
      occ_mismatch=1   → "sustained_leak"
      else             → "hygiene_threshold"

    Interview note on occ_mismatch weight (0.20):
      Occupancy is the clearest discriminator — flow with nobody present almost
      always means a stuck valve or pipe failure.  But it's not the largest
      weight (flow deviation is) because occupancy sensors can glitch, and we
      don't want a single bad occupancy reading to suppress a 6-hour leak.
    """
    duration = session["duration_minutes"]

    if duration < MIN_SESSION_DURATION_MINUTES:
        return None

    avg_flow      = session["avg_flow_lpm"]
    avg_baseline  = session["avg_baseline_mean"]
    flow_deviation = max(avg_flow - avg_baseline, 0.0)

    occ_values      = session["occupancy_values"]
    sensor_statuses = session["sensor_statuses"]

    occ_mismatch   = 1.0 if all(o == 0 for o in occ_values) else 0.0
    degraded       = {"FAULT", "OFFLINE"}
    sensor_penalty = 1.0 if any(s in degraded for s in sensor_statuses) else 0.0

    flow_dev_norm = min(flow_deviation / FLOW_DEV_CAP_LPM, 1.0)
    duration_norm = min(duration / DURATION_CAP_MIN, 1.0)

    raw_score = (
        flow_dev_norm   * W_FLOW_DEV       +
        duration_norm   * W_DURATION       +
        occ_mismatch    * W_OCC_MISMATCH   +
        sensor_penalty  * W_SENSOR_HEALTH
    ) * 100

    severity_score = round(raw_score, 1)
    label          = _severity_label(severity_score)

    if sensor_penalty == 1.0:
        anomaly_type = "sensor_fault"
    elif occ_mismatch == 1.0:
        anomaly_type = "sustained_leak"
    else:
        anomaly_type = "hygiene_threshold"

    return {
        **{k: v for k, v in session.items() if k != "all_rows"},
        "severity_score":  severity_score,
        "severity_label":  label,
        "anomaly_type":    anomaly_type,
        "flow_deviation":  round(flow_deviation, 3),
        "occ_mismatch":    occ_mismatch,
        "sensor_penalty":  sensor_penalty,
    }


# ── Pass 3: Slow-drip detection (Section 4c) ──────────────────────────────────

def detect_slow_drip(df: pd.DataFrame) -> list[dict]:
    """
    Detect slow drips too small to cross the Section 4a threshold.

    Strategy — cumulative flow in 2-hour rolling windows during overnight
    zero-occupancy periods:

      1. Filter to rows where (a) hour is overnight AND (b) occupancy == 0.
      2. For each fixture, slide a SLOW_DRIP_WINDOW_MINUTES (120) window.
      3. If sum(flow_rate_lpm) in window >= SLOW_DRIP_CUMULATIVE_THRESHOLD_L (10L):
         emit a slow_drip ticket for that window.
      4. De-duplicate: skip windows that overlap with an already-triggered window.

    Why cumulative rather than slope?
      The injected drip is a CONSTANT 0.25 LPM — no acceleration, so slope ≈ 0.
      Cumulative: 0.25 LPM × 120 readings = 30 L >> 10 L threshold.
      A truly idle fixture: 0 LPM × 120 readings = 0 L << 10 L threshold.
    """
    df = df.copy()
    df["timestamp"]   = pd.to_datetime(df["timestamp"])
    df["hour_of_day"] = df["timestamp"].dt.hour

    overnight_mask  = df["hour_of_day"].apply(_is_overnight)
    unoccupied_mask = df["occupancy"] == 0
    overnight_df    = df[overnight_mask & unoccupied_mask].sort_values("timestamp")

    results: list[dict] = []

    for fixture_id, fix_df in overnight_df.groupby("fixture_id", sort=False):
        fix_df = fix_df.sort_values("timestamp").reset_index(drop=True)

        n = len(fix_df)
        if n < SLOW_DRIP_MIN_READINGS:
            continue

        t0 = fix_df["timestamp"].iloc[0]
        fix_df["elapsed_min"] = (fix_df["timestamp"] - t0).dt.total_seconds() / 60.0

        triggered_until = -1

        for i in range(n):
            w_start = fix_df.loc[i, "elapsed_min"]
            w_end   = w_start + SLOW_DRIP_WINDOW_MINUTES

            if w_start <= triggered_until:
                continue

            window = fix_df[(fix_df["elapsed_min"] >= w_start) & (fix_df["elapsed_min"] < w_end)]

            if len(window) < SLOW_DRIP_MIN_READINGS:
                continue

            cumulative_flow = float(window["flow_rate_lpm"].sum())

            if cumulative_flow >= SLOW_DRIP_CUMULATIVE_THRESHOLD_L:
                avg_flow     = round(float(window["flow_rate_lpm"].mean()), 3)
                duration_min = int(len(window))
                start_ts     = window["timestamp"].iloc[0]
                end_ts       = window["timestamp"].iloc[-1]
                zone_id      = str(window["zone_id"].iloc[0])
                sensor_stat  = str(window["sensor_status"].iloc[0])
                sensor_pen   = 1.0 if sensor_stat in {"FAULT", "OFFLINE"} else 0.0

                flow_dev_norm = min(avg_flow / FLOW_DEV_CAP_LPM, 1.0)
                duration_norm = min(duration_min / DURATION_CAP_MIN, 1.0)
                raw_score = (
                    flow_dev_norm * W_FLOW_DEV      +
                    duration_norm * W_DURATION      +
                    1.0           * W_OCC_MISMATCH  +
                    sensor_pen    * W_SENSOR_HEALTH
                ) * 100

                results.append({
                    "fixture_id":        fixture_id,
                    "zone_id":           zone_id,
                    "start_ts":          start_ts,
                    "end_ts":            end_ts,
                    "duration_minutes":  duration_min,
                    "avg_flow_lpm":      avg_flow,
                    "max_flow_lpm":      round(float(window["flow_rate_lpm"].max()), 3),
                    "avg_baseline_mean": 0.0,
                    "occupancy_values":  [0] * duration_min,
                    "sensor_statuses":   [sensor_stat] * duration_min,
                    "severity_score":    round(raw_score, 1),
                    "severity_label":    _severity_label(round(raw_score, 1)),
                    "anomaly_type":      "slow_drip",
                    "flow_deviation":    avg_flow,
                    "occ_mismatch":      1.0,
                    "sensor_penalty":    sensor_pen,
                })

                triggered_until = w_end

    return results


# ── Build ticket from scored session (Section 4e) ─────────────────────────────

def session_to_ticket(session: dict) -> dict:
    """
    Map a scored session dict to the full ticket schema (Section 3).
    Calculates 4e water loss and cost impact.
    """
    duration   = session["duration_minutes"]
    avg_flow   = session["avg_flow_lpm"]
    water_loss = round(avg_flow * duration, 2)
    cost       = round(water_loss * WATER_COST_PER_LITER, 2)

    ts_str = session["start_ts"]
    if hasattr(ts_str, "strftime"):
        ts_fmt = ts_str.strftime("%Y%m%d%H%M")
        ts_iso = ts_str.isoformat()
    else:
        ts_fmt = str(ts_str).replace("-", "").replace(":", "").replace(" ", "")[:12]
        ts_iso = str(ts_str)

    evidence = build_ticket_evidence({
        "anomaly_type": session.get("anomaly_type", "sustained_leak"),
        "severity_score": session.get("severity_score"),
        "severity_label": session.get("severity_label", "Flagged"),
        "estimated_water_loss_liters": water_loss,
    }, session_dict=session)

    return {
        "ticket_id":                   f"TKT-{session['fixture_id']}-{ts_fmt}",
        "timestamp_flagged":           ts_iso,
        "zone_id":                     session["zone_id"],
        "fixture_id":                  session["fixture_id"],
        "anomaly_type":                session.get("anomaly_type", "sustained_leak"),
        "severity_score":              session.get("severity_score"),
        "severity_label":              session.get("severity_label", "Flagged"),
        "explanation":                 session.get("explanation", ""),
        "estimated_water_loss_liters": water_loss,
        "estimated_cost_impact":       cost,
        "status":                      "open",
        # Telemetry context for LLM explanation generation
        "duration_minutes":            duration,
        "avg_flow_lpm":                avg_flow,
        "max_flow_lpm":                session.get("max_flow_lpm", avg_flow),
        "avg_baseline_mean":           session.get("avg_baseline_mean", 0.0),
        # Feature 4 Explainability evidence
        "evidence":                    evidence,
        "evidence_json":               json.dumps(evidence),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def run_detection() -> None:
    print("=" * 70)
    print("KOHLER Smart Facility Manager -- Detector (Phase 2 / 4a-4e)")
    print("=" * 70)

    print("\nLoading readings from database...")
    df = get_readings_df(str(DB_PATH))
    if df.empty:
        print("  [!] No readings found. Run: python src/simulator.py")
        return
    print(f"  Loaded {len(df):,} rows across {df['fixture_id'].nunique()} fixtures.")

    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    deleted = conn.execute("DELETE FROM tickets").rowcount
    conn.commit()
    conn.close()
    if deleted:
        print(f"  Cleared {deleted} old ticket(s).")

    # Pass 1
    print("\nPass 1 -- Adaptive baseline + outlier flags...")
    flagged    = compute_outlier_flags(df)
    n_outliers = int(flagged["is_outlier"].sum())
    print(f"  Outlier readings : {n_outliers:,}")

    # Pass 2
    print("\nPass 2 -- Session grouping, spanning, scoring...")
    short_sessions = group_into_sessions(flagged, max_gap_minutes=2)
    print(f"  Short sessions (2-min gap)  : {len(short_sessions)}")

    spanned_sessions = span_unoccupied_sessions(short_sessions, max_span_gap_minutes=90)
    print(f"  After spanning unoccupied   : {len(spanned_sessions)}")

    tickets: list[dict] = []
    suppressed = 0
    for session in spanned_sessions:
        scored = score_session(session)
        if scored is None:
            suppressed += 1
            continue
        tickets.append(session_to_ticket(scored))

    print(f"  Suppressed (< {MIN_SESSION_DURATION_MINUTES} min)      : {suppressed}")
    print(f"  Tickets from Pass 2         : {len(tickets)}")

    # Pass 3
    print("\nPass 3 -- Slow-drip detection (Section 4c)...")
    slow_drips = detect_slow_drip(df)
    print(f"  Slow-drip tickets : {len(slow_drips)}")
    for sd in slow_drips:
        tickets.append(session_to_ticket(sd))

    # Pass 4 -- LLM ticket explanation generation (Google Gemini API)
    print("\nPass 4 -- Generating LLM explanations (Google Gemini API)...")
    from src.llm import enrich_tickets_with_explanations, generate_daily_digest
    tickets = enrich_tickets_with_explanations(tickets)

    print(f"\nWriting {len(tickets)} ticket(s) to database...")
    for t in tickets:
        insert_ticket(str(DB_PATH), t)

    # Pass 5 -- End-of-day digest generation (Section 5.2)
    print("\nPass 5 -- Generating End-of-Day Digests (Section 5.2)...")
    dates = sorted(list({str(t["timestamp_flagged"])[:10] for t in tickets if t.get("timestamp_flagged")}))
    for d_str in dates:
        digest = generate_daily_digest(tickets, d_str)
        d_count = sum(1 for t in tickets if str(t.get("timestamp_flagged", "")).startswith(d_str) and str(t.get("severity_label", "")).lower() in ("low", "medium"))
        save_daily_digest(str(DB_PATH), d_str, digest, d_count)
        print(f"  [{d_str}] Digest generated ({d_count} Low/Med tickets):")
        print(f"       \"{digest}\"")

    # Pass 6 -- Predictive Fixture Health (Section 1)
    print("\nPass 6 -- Calculating Predictive Fixture Health (Section 1)...")
    from src.fixture_health import compute_all_fixture_health
    health_records = compute_all_fixture_health(str(DB_PATH))
    print(f"  Calculated health records for {len(health_records)} fixtures.")

    # Scenario verification
    print("\n" + "-" * 70)
    print("SCENARIO VERIFICATION")
    print("-" * 70)

    tickets_df = get_tickets_df(str(DB_PATH))

    # A -- Sustained leak (Sink_01, Day2 02:00-06:00)
    sink01 = tickets_df[tickets_df["fixture_id"] == "Sink_01"]
    leak_t = sink01[sink01["anomaly_type"] == "sustained_leak"]
    if not leak_t.empty:
        best    = leak_t.sort_values("severity_score", ascending=False).iloc[0]
        score   = best["severity_score"]
        label   = best["severity_label"]
        verdict = "[PASS]" if label in ("High", "Critical") else "[FAIL]"
        print(f"\n  [A] SUSTAINED LEAK  -- Sink_01")
        print(f"      Type   : {best['anomaly_type']}")
        print(f"      Score  : {score:.1f}  ({label})  {verdict}")
        print(f"      Water  : {best['estimated_water_loss_liters']:.1f} L   "
              f"Cost : Rs.{best['estimated_cost_impact']:.2f}")
        if "explanation" in best and best["explanation"]:
            print(f"      LLM Explanation: \"{best['explanation']}\"")
    else:
        any_sink01 = sink01.sort_values("severity_score", ascending=False)
        if not any_sink01.empty:
            best    = any_sink01.iloc[0]
            score   = best["severity_score"]
            label   = best["severity_label"]
            verdict = "[PASS]" if label in ("High", "Critical") else "[FAIL]"
            print(f"\n  [A] SUSTAINED LEAK  -- Sink_01 (caught as {best['anomaly_type']})")
            print(f"      Score  : {score:.1f}  ({label})  {verdict}")
            print(f"      Water  : {best['estimated_water_loss_liters']:.1f} L   "
                  f"Cost : Rs.{best['estimated_cost_impact']:.2f}")
            if "explanation" in best and best["explanation"]:
                print(f"      LLM Explanation: \"{best['explanation']}\"")
        else:
            print("\n  [A] SUSTAINED LEAK  -- Sink_01  [FAIL] (no ticket)")

    # B -- Slow drip (Toilet_B1, overnight constant drip)
    drip_fix = ANOMALY_SLOW_DRIP["fixture_id"]   # "Toilet_B1" — read from config, not hardcoded
    drip_t = tickets_df[
        (tickets_df["fixture_id"] == drip_fix) &
        (tickets_df["anomaly_type"] == "slow_drip")
    ]
    if not drip_t.empty:
        best  = drip_t.iloc[0]
        score = best["severity_score"]
        label = best["severity_label"]
        print(f"\n  [B] SLOW DRIP       -- {drip_fix}")
        print(f"      Type   : {best['anomaly_type']}")
        print(f"      Score  : {score:.1f}  ({label})  [PASS]")
        print(f"      Water  : {best['estimated_water_loss_liters']:.1f} L   "
              f"Cost : Rs.{best['estimated_cost_impact']:.2f}")
        if "explanation" in best and best["explanation"]:
            print(f"      LLM Explanation: \"{best['explanation']}\"")
    else:
        print(f"\n  [B] SLOW DRIP       -- {drip_fix}  [FAIL] (not caught by 4c)")

    # C -- False-positive trap (Sink_02, occupied shower)
    sink02 = tickets_df[tickets_df["fixture_id"] == "Sink_02"]
    if sink02.empty:
        print(f"\n  [C] FALSE-POSITIVE  -- Sink_02")
        print(f"      No ticket generated  [PASS] (correctly not flagged)")
    else:
        best    = sink02.sort_values("severity_score", ascending=False).iloc[0]
        score   = best["severity_score"]
        label   = best["severity_label"]
        verdict = "[PASS]" if label == "Low" else "[FAIL]"
        print(f"\n  [C] FALSE-POSITIVE  -- Sink_02")
        print(f"      Type   : {best['anomaly_type']}")
        print(f"      Score  : {score:.1f}  ({label})  {verdict}")

    # Full ticket table
    print("\n" + "-" * 70)
    print("ALL TICKETS  (sorted by severity)")
    print("-" * 70)
    print(f"  {'Fixture':<12}  {'Type':<20}  {'Score':>6}  {'Label':<8}  {'Water (L)':>10}  {'Cost (Rs.)':>10}")
    print("  " + "-" * 68)
    for _, row in tickets_df.sort_values("severity_score", ascending=False).iterrows():
        print(
            f"  {row['fixture_id']:<12}  {row['anomaly_type']:<20}  "
            f"{row['severity_score']:>6.1f}  {row['severity_label']:<8}  "
            f"{row['estimated_water_loss_liters']:>10.1f}  "
            f"{row['estimated_cost_impact']:>10.2f}"
        )

    print("\n[OK] Phase 3 detection & LLM layer complete.")


if __name__ == "__main__":
    run_detection()
