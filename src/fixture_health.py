"""
fixture_health.py — Predictive Fixture Health scoring model for KOHLER Facility Monitor.

Implements Section 1 of the Track 2 Feature Implementation Plan:
- Transparent 6-factor weighted risk formula (Section 1.3)
- Health score: 100 - risk
- Status labels: Healthy, Watch, Degrading, High Risk
- Trend analysis: Deteriorating, Stable, Improving (Section 1.4)
- Deterministic, rule-based maintenance recommendations (Section 1.7 & Section 9 Rule 11)
- SQLite database persistence in `fixture_health` table (Section 1.5)
"""

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import (
    DB_PATH,
    FIXTURES,
    SIM_START,
    SIM_DURATION_HOURS,
    WATER_COST_PER_LITER,
)
from src.database import (
    get_connection,
    init_db,
    get_readings_df,
    get_tickets_df,
    save_fixture_health_records,
    get_fixture_health_records,
)


def calculate_fixture_risk_components(
    fixture_id: str,
    fixture_tickets: list[dict],
    readings_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Calculate the 6 transparent risk components (0-100 each) per Section 1.3.
    Strictly deterministic and traceable to real telemetry events.
    """
    anomaly_count = len(fixture_tickets)
    slow_drip_count = sum(1 for t in fixture_tickets if t.get("anomaly_type") == "slow_drip")
    sensor_fault_count = sum(1 for t in fixture_tickets if t.get("anomaly_type") == "sensor_fault")

    # If readings_df provided, check sensor status in telemetry as well
    if readings_df is not None and not readings_df.empty:
        fix_readings = readings_df[readings_df["fixture_id"] == fixture_id]
        if not fix_readings.empty and "sensor_status" in fix_readings.columns:
            non_ok = fix_readings[fix_readings["sensor_status"] != "OK"]
            sensor_fault_count = max(sensor_fault_count, len(non_ok))

    # 1. Anomaly Frequency Score (weight: 0.30)
    # Scaled by number of incidents and highest severity score
    max_severity = max([float(t.get("severity_score") or 0.0) for t in fixture_tickets], default=0.0)
    if anomaly_count == 0:
        anomaly_frequency_score = 0.0
    else:
        # Base count impact + severity scaling
        count_factor = min(60.0, anomaly_count * 25.0)
        severity_factor = (max_severity / 100.0) * 40.0
        anomaly_frequency_score = min(100.0, count_factor + severity_factor)

    # 2. Recurrence Score (weight: 0.20)
    # Measures whether anomalies occurred repeatedly across distinct time sessions
    if anomaly_count <= 1:
        recurrence_score = 0.0
    elif anomaly_count == 2:
        recurrence_score = 55.0
    elif anomaly_count == 3:
        recurrence_score = 85.0
    else:
        recurrence_score = 100.0

    # 3. Flow Drift Score (weight: 0.20)
    # Measures baseline elevation or flow drift over time
    flow_drift_score = 0.0
    if readings_df is not None and not readings_df.empty:
        fix_readings = readings_df[readings_df["fixture_id"] == fixture_id].sort_values("timestamp")
        if len(fix_readings) >= 120:
            half = len(fix_readings) // 2
            first_half_flow = fix_readings.iloc[:half]["flow_rate_lpm"].mean()
            second_half_flow = fix_readings.iloc[half:]["flow_rate_lpm"].mean()
            drift_lpm = max(0.0, second_half_flow - first_half_flow)
            flow_drift_score = min(100.0, drift_lpm * 50.0)
    if flow_drift_score == 0.0 and anomaly_count > 0:
        # Fallback to observed flow deviation from tickets
        avg_flow = max([float(t.get("avg_flow_lpm") or 0.0) for t in fixture_tickets], default=0.0)
        base_flow = max([float(t.get("avg_baseline_mean") or 0.0) for t in fixture_tickets], default=0.0)
        if base_flow > 0:
            dev_ratio = max(0.0, (avg_flow - base_flow) / max(0.1, base_flow))
            flow_drift_score = min(100.0, dev_ratio * 20.0)

    # 4. Slow Drip Score (weight: 0.15)
    # Specifically penalizes persistent overnight creep/micro-leaks
    if slow_drip_count == 0:
        slow_drip_score = 0.0
    elif slow_drip_count == 1:
        slow_drip_score = 80.0
    else:
        slow_drip_score = 100.0

    # 5. Sensor Health Score (weight: 0.10)
    # Penalizes faulty/erratic sensor behavior
    if sensor_fault_count == 0:
        sensor_health_score = 0.0
    else:
        sensor_health_score = min(100.0, sensor_fault_count * 20.0)

    # 6. Unresolved Status Score (weight: 0.05)
    # Current active ticket status penalty
    open_tickets = [t for t in fixture_tickets if str(t.get("status", "")).lower() == "open"]
    dispatched_tickets = [t for t in fixture_tickets if str(t.get("status", "")).lower() == "dispatched"]
    if open_tickets:
        unresolved_score = 100.0
    elif dispatched_tickets:
        unresolved_score = 50.0
    else:
        unresolved_score = 0.0

    # Weighted risk formula per Section 1.3
    risk = (
        anomaly_frequency_score * 0.30
        + recurrence_score * 0.20
        + flow_drift_score * 0.20
        + slow_drip_score * 0.15
        + sensor_health_score * 0.10
        + unresolved_score * 0.05
    )
    risk_score = round(max(0.0, min(100.0, risk)), 1)
    health_score = round(max(0.0, min(100.0, 100.0 - risk_score)), 1)

    return {
        "anomaly_frequency_score": round(anomaly_frequency_score, 1),
        "recurrence_score": round(recurrence_score, 1),
        "flow_drift_score": round(flow_drift_score, 1),
        "slow_drip_score": round(slow_drip_score, 1),
        "sensor_health_score": round(sensor_health_score, 1),
        "unresolved_score": round(unresolved_score, 1),
        "risk_score": risk_score,
        "health_score": health_score,
    }


def map_health_label(health_score: float) -> str:
    """Map health score to product status label per Section 1.3."""
    if health_score >= 80.0:
        return "Healthy"
    elif health_score >= 60.0:
        return "Watch"
    elif health_score >= 40.0:
        return "Degrading"
    else:
        return "High Risk"


def calculate_fixture_trend(
    fixture_id: str,
    fixture_tickets: list[dict],
    readings_df: Optional[pd.DataFrame] = None,
) -> str:
    """
    Calculate trend by comparing recent vs older anomaly frequency per Section 1.4:
    - Deteriorating: Accelerating incidents or active failures in the recent window.
    - Improving: Prior historical incidents successfully resolved with no active leaks.
    - Stable: Nominal operating condition with no active anomalies.
    """
    if not fixture_tickets:
        return "Stable"

    # For 7-day (168h) timespan: Days 1-4 (0-96h) is historical baseline,
    # Days 5-7 (96-168h) is recent window.
    split_hours = 96 if SIM_DURATION_HOURS >= 96 else SIM_DURATION_HOURS // 2
    split_dt = SIM_START + datetime.timedelta(hours=split_hours)
    split_iso = split_dt.isoformat()

    older_tickets = [t for t in fixture_tickets if str(t.get("timestamp_flagged", "")) < split_iso]
    recent_tickets = [t for t in fixture_tickets if str(t.get("timestamp_flagged", "")) >= split_iso]

    older_count = len(older_tickets)
    recent_count = len(recent_tickets)

    active_recent = [t for t in recent_tickets if str(t.get("status", "")).lower() != "resolved"]
    all_resolved = all(str(t.get("status", "")).lower() == "resolved" for t in fixture_tickets)

    # 1. If there are active unresolved anomalies in the recent window -> Deteriorating
    if active_recent:
        return "Deteriorating"
    # 2. If recent anomaly rate exceeds older rate -> Deteriorating
    elif recent_count > older_count:
        return "Deteriorating"
    # 3. If historical anomalies were resolved and recent window is clean -> Improving
    elif all_resolved and older_count > 0 and recent_count == 0:
        return "Improving"
    # 4. If all resolved and overall anomaly frequency decreased -> Improving
    elif all_resolved and len(fixture_tickets) > 0:
        return "Improving"
    # 5. Otherwise, stable
    return "Stable"


def generate_deterministic_recommendation(
    health_score: float,
    risk_factors: dict,
    fixture_tickets: list[dict],
) -> str:
    """
    Generate transparent, deterministic, rule-based recommendation per Section 1.7 & Section 9 Rule 11.
    """
    anomaly_types = {t.get("anomaly_type") for t in fixture_tickets}

    if "sustained_leak" in anomaly_types:
        return "Inspect solenoid valve, shutoff cartridge, and supply line immediately."
    elif "slow_drip" in anomaly_types:
        return "Inspect valve seal and diaphragm for overnight micro-seepage during next round."
    elif "sensor_fault" in anomaly_types:
        return "Check transducer wiring, clean optical sensor, and recalibrate flow signal."
    elif health_score < 40.0:
        return "Prioritize immediate preventive fixture overhaul before full valve failure."
    elif health_score < 60.0:
        return "Schedule preventive inspection and pressure test within 24 hours."
    elif health_score < 80.0:
        return "Monitor telemetry closely for recurring flow drift during low-occupancy windows."
    else:
        return "Operating within normal parameters. Continue standard routine inspection."


def compute_all_fixture_health(db_path: str = None) -> List[Dict[str, Any]]:
    """
    Compute health metrics for all 17 fixtures and persist to SQLite `fixture_health` table.
    Can be called dynamically or as Pass 6 in `run_detection()`.
    """
    if db_path is None:
        db_path = str(DB_PATH)

    init_db(db_path)
    tickets_df = get_tickets_df(db_path)
    readings_df = get_readings_df(db_path)

    # Group tickets by fixture
    tickets_by_fixture: Dict[str, list[dict]] = {}
    if not tickets_df.empty:
        for _, row in tickets_df.iterrows():
            fix = str(row["fixture_id"])
            if fix not in tickets_by_fixture:
                tickets_by_fixture[fix] = []
            tickets_by_fixture[fix].append(row.to_dict())

    now_iso = datetime.datetime.now().isoformat()
    health_records: List[Dict[str, Any]] = []

    for zone_id, fixture_id, fixture_type in FIXTURES:
        fix_tickets = tickets_by_fixture.get(fixture_id, [])
        risk_data = calculate_fixture_risk_components(fixture_id, fix_tickets, readings_df)
        trend = calculate_fixture_trend(fixture_id, fix_tickets, readings_df)
        recommendation = generate_deterministic_recommendation(risk_data["health_score"], risk_data, fix_tickets)

        last_incident = None
        if fix_tickets:
            # Sort tickets by timestamp_flagged descending
            sorted_t = sorted(fix_tickets, key=lambda x: str(x.get("timestamp_flagged", "")), reverse=True)
            last_incident = sorted_t[0].get("timestamp_flagged")

        slow_drips = sum(1 for t in fix_tickets if t.get("anomaly_type") == "slow_drip")
        sensor_faults = sum(1 for t in fix_tickets if t.get("anomaly_type") == "sensor_fault")

        rec = {
            "fixture_id": fixture_id,
            "zone_id": zone_id,
            "fixture_type": fixture_type,
            "health_score": risk_data["health_score"],
            "risk_score": risk_data["risk_score"],
            "status": map_health_label(risk_data["health_score"]),
            "trend": trend,
            "anomaly_count": len(fix_tickets),
            "slow_drip_count": slow_drips,
            "sensor_fault_count": sensor_faults,
            "last_incident_at": last_incident,
            "calculated_at": now_iso,
            "recommendation": recommendation,
            "risk_factors": {
                "anomaly_frequency_score": risk_data["anomaly_frequency_score"],
                "recurrence_score": risk_data["recurrence_score"],
                "flow_drift_score": risk_data["flow_drift_score"],
                "slow_drip_score": risk_data["slow_drip_score"],
                "sensor_health_score": risk_data["sensor_health_score"],
                "unresolved_score": risk_data["unresolved_score"],
            },
            "risk_factors_json": json.dumps({
                "anomaly_frequency_score": risk_data["anomaly_frequency_score"],
                "recurrence_score": risk_data["recurrence_score"],
                "flow_drift_score": risk_data["flow_drift_score"],
                "slow_drip_score": risk_data["slow_drip_score"],
                "sensor_health_score": risk_data["sensor_health_score"],
                "unresolved_score": risk_data["unresolved_score"],
            }),
        }
        health_records.append(rec)

    # Persist to SQLite
    save_fixture_health_records(db_path, health_records)
    return health_records


def get_facility_health_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute top-level KPI metrics across all fixtures."""
    if not records:
        return {
            "average_health_score": 100.0,
            "healthy_count": 0,
            "watch_count": 0,
            "degrading_count": 0,
            "high_risk_count": 0,
            "deteriorating_count": 0,
            "total_fixtures": 0,
        }

    avg_health = sum(r["health_score"] for r in records) / len(records)
    healthy = sum(1 for r in records if r["health_score"] >= 80.0)
    watch = sum(1 for r in records if 60.0 <= r["health_score"] < 80.0)
    degrading = sum(1 for r in records if 40.0 <= r["health_score"] < 60.0)
    high_risk = sum(1 for r in records if r["health_score"] < 40.0)
    deteriorating = sum(1 for r in records if r["trend"] == "Deteriorating")

    return {
        "average_health_score": round(avg_health, 1),
        "healthy_count": healthy,
        "watch_count": watch,
        "degrading_count": degrading,
        "high_risk_count": high_risk,
        "deteriorating_count": deteriorating,
        "total_fixtures": len(records),
    }
