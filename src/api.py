"""
api.py — FastAPI REST API for KOHLER Smart Facility Manager.

Exposes endpoints for the modern frontend:
- Summary metrics
- Downsampled time-series flow readings
- 24-hour occupancy heatmap matrix
- Anomaly tickets & status updates
- End-of-day digests
- AI Facility Copilot conversational query endpoint (Google Gemini)
"""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pydantic import BaseModel

from src.config import (
    DB_PATH, SIM_START, SIM_DURATION_HOURS,
    FIXTURES,
)
from src.database import (
    get_connection, get_readings_df, get_tickets_df,
    get_daily_digests, update_ticket_status,
)
from src.explainability import build_ticket_evidence
from src.sustainability import (
    calculate_facility_sustainability_summary,
    calculate_incident_projection,
    calculate_intervention_impact,
)
from src.llm import get_gemini_model, get_copilot_model

app = FastAPI(
    title="KOHLER Smart Facility Manager API",
    version="1.0.0",
    description="REST backend for industrial facility telemetry, anomaly tickets, and AI explainability.",
)

# Enable CORS for frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zone metadata & color tokens
ZONE_COLORS = {
    "T2_Restroom_A":  "#6B8CAE",
    "T2_Restroom_B":  "#789A8B",
    "T2_Family_Room": "#B08D57",
    "T2_Staff_WC":    "#847E9C",
}


# ── Pydantic Request/Response Models ──────────────────────────────────────────

class TicketStatusUpdate(BaseModel):
    status: str  # "open", "dispatched", "resolved"
    resolution_note: Optional[str] = None


class ChatMessage(BaseModel):
    role: str    # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = []


# ── Health & Overview ─────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "database": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "timestamp": datetime.datetime.now().isoformat(),
    }


@app.get("/api/overview")
def get_overview():
    """Return top-level metric card data and facility configuration."""
    readings = get_readings_df(str(DB_PATH))
    tickets = get_tickets_df(str(DB_PATH))

    total_readings = len(readings)
    total_tickets = len(tickets)
    open_tickets = len(tickets[tickets["status"].isin(["open", "dispatched", "in_progress"])]) if not tickets.empty else 0
    dispatched_tickets = len(tickets[tickets["status"].isin(["dispatched", "in_progress"])]) if not tickets.empty else 0
    resolved_tickets = len(tickets[tickets["status"] == "resolved"]) if not tickets.empty else 0
    monitored_zones = readings["zone_id"].nunique() if not readings.empty else len(ZONE_COLORS)

    water_loss = (
        float(tickets["estimated_water_loss_liters"].sum())
        if not tickets.empty and "estimated_water_loss_liters" in tickets.columns
        else 0.0
    )
    cost_impact = (
        float(tickets["estimated_cost_impact"].sum())
        if not tickets.empty and "estimated_cost_impact" in tickets.columns
        else 0.0
    )

    sim_end = SIM_START + datetime.timedelta(hours=SIM_DURATION_HOURS)

    return {
        "sensor_readings_count": total_readings,
        "total_tickets_count": total_tickets,
        "open_tickets_count": open_tickets,
        "dispatched_tickets_count": dispatched_tickets,
        "in_progress_tickets_count": dispatched_tickets,
        "resolved_tickets_count": resolved_tickets,
        "zones_monitored_count": monitored_zones,
        "estimated_water_loss_liters": round(water_loss, 1),
        "estimated_cost_impact_inr": round(cost_impact, 2),
        "sim_start": SIM_START.isoformat(),
        "sim_end": sim_end.isoformat(),
        "sim_duration_hours": SIM_DURATION_HOURS,
        "zones": [
            {"zone_id": zid, "color": color, "name": zid.replace("T2_", "").replace("_", " ")}
            for zid, color in ZONE_COLORS.items()
        ],
        "total_fixtures": len(FIXTURES),
    }


# ── Readings & Flow Rate Telemetry ─────────────────────────────────────────────

@app.get("/api/readings")
def get_readings(
    downsample_mins: int = Query(5, ge=1, le=60),
    zone_id: Optional[str] = None,
    fixture_id: Optional[str] = None,
    up_to_ts: Optional[str] = None,
):
    """
    Return time-series flow rate readings downsampled to regular intervals
    for responsive chart rendering.
    """
    df = get_readings_df(str(DB_PATH))
    if df.empty:
        return []

    if zone_id:
        df = df[df["zone_id"] == zone_id]
    if fixture_id:
        df = df[df["fixture_id"] == fixture_id]
    if up_to_ts:
        ts_limit = pd.to_datetime(up_to_ts)
        df = df[df["timestamp"] <= ts_limit]

    # Downsample by minute interval
    if downsample_mins > 1:
        df = df[df["timestamp"].dt.minute % downsample_mins == 0]

    # Aggregate zone totals as well for fast zone-view rendering
    df["timestamp_str"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    
    records = df[[
        "timestamp_str", "zone_id", "fixture_id", "flow_rate_lpm", "occupancy", "sensor_status"
    ]].to_dict(orient="records")

    return records


@app.get("/api/readings/zone-totals")
def get_zone_totals(downsample_mins: int = Query(5, ge=1, le=60), up_to_ts: Optional[str] = None):
    """Return pre-aggregated flow rate sums per zone per timestamp."""
    df = get_readings_df(str(DB_PATH))
    if df.empty:
        return []

    if up_to_ts:
        ts_limit = pd.to_datetime(up_to_ts)
        df = df[df["timestamp"] <= ts_limit]

    if downsample_mins > 1:
        df = df[df["timestamp"].dt.minute % downsample_mins == 0]

    agg = df.groupby(["timestamp", "zone_id"], as_index=False)["flow_rate_lpm"].sum()
    agg["timestamp_str"] = agg["timestamp"].dt.strftime("%Y-%m-%d %H:%M")

    records = agg[["timestamp_str", "zone_id", "flow_rate_lpm"]].to_dict(orient="records")
    return records


# ── Occupancy Heatmap ──────────────────────────────────────────────────────────

@app.get("/api/occupancy-heatmap")
def get_occupancy_heatmap():
    """Return 24-hour occupancy average matrix across all 17 fixtures."""
    df = get_readings_df(str(DB_PATH))
    if df.empty:
        return {"fixtures": [], "hours": list(range(24)), "matrix": []}

    df["hour"] = df["timestamp"].dt.hour
    agg = df.groupby(["fixture_id", "hour"])["occupancy"].mean().reset_index()
    pivot = agg.pivot(index="fixture_id", columns="hour", values="occupancy").fillna(0)

    fixtures = list(pivot.index)
    hours = list(pivot.columns)
    # Matrix of shape [len(fixtures)][24]
    matrix = [[round(float(val), 3) for val in row] for row in pivot.values]

    return {
        "fixtures": fixtures,
        "hours": hours,
        "matrix": matrix,
    }


# ── Tickets & Status Management ────────────────────────────────────────────────

@app.get("/api/tickets")
def get_tickets():
    """Return all anomaly tickets with severity and AI explanation."""
    df = get_tickets_df(str(DB_PATH))
    if df.empty:
        return []

    df["timestamp_flagged_str"] = df["timestamp_flagged"].dt.strftime("%Y-%m-%d %H:%M")
    tickets = df.to_dict(orient="records")

    for t in tickets:
        # Convert timestamp to string if it's a Timestamp object
        if isinstance(t.get("timestamp_flagged"), (pd.Timestamp, datetime.datetime)):
            t["timestamp_flagged"] = t["timestamp_flagged"].isoformat()

        # Feature 4: Explainable Anomaly Detection evidence breakdown
        ev_json = t.get("evidence_json")
        if ev_json and isinstance(ev_json, str) and ev_json.strip():
            try:
                t["evidence"] = json.loads(ev_json)
            except Exception:
                t["evidence"] = build_ticket_evidence(t)
        else:
            t["evidence"] = build_ticket_evidence(t)

        # Feature 2: Sustainability Impact (Incident projections or intervention impact)
        flow_lpm = float(t["evidence"].get("observed_flow_lpm") or 0.0)
        dur_min = int(t["evidence"].get("duration_minutes") or 0)
        actual_loss = float(t.get("estimated_water_loss_liters") or (flow_lpm * dur_min))
        status = str(t.get("status", "open")).lower()

        if status == "resolved":
            t["sustainability"] = {
                "type": "resolved",
                "intervention_impact": calculate_intervention_impact(actual_loss, flow_lpm, dur_min),
            }
        else:
            t["sustainability"] = {
                "type": "active",
                "projections": calculate_incident_projection(flow_lpm),
            }

    return tickets


@app.patch("/api/tickets/{ticket_id}/status")
def patch_ticket_status(ticket_id: str, body: TicketStatusUpdate):
    """Update ticket status ('open', 'dispatched', 'resolved') and optional resolution note in SQLite."""
    status = body.status.lower()
    if status == "in_progress":
        status = "dispatched"

    valid_statuses = {"open", "dispatched", "resolved"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of {valid_statuses}",
        )

    updated = update_ticket_status(
        str(DB_PATH), ticket_id, status, resolution_note=body.resolution_note
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")

    return {
        "ticket_id": ticket_id,
        "status": status,
        "resolution_note": body.resolution_note or "",
        "updated_at": datetime.datetime.now().isoformat(),
    }


@app.get("/api/tickets/{ticket_id}/evidence")
def get_ticket_evidence_endpoint(ticket_id: str):
    """Return Section 4 explainability evidence breakdown for a specific ticket."""
    df = get_tickets_df(str(DB_PATH))
    if df.empty:
        raise HTTPException(status_code=404, detail="No tickets found.")
    
    match = df[df["ticket_id"] == ticket_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_id}' not found.")
    
    t = match.iloc[0].to_dict()
    ev_json = t.get("evidence_json")
    if ev_json and isinstance(ev_json, str) and ev_json.strip():
        try:
            return json.loads(ev_json)
        except Exception:
            pass
    return build_ticket_evidence(t)


@app.get("/api/sustainability/summary")
def get_sustainability_summary_endpoint():
    """Return facility-level sustainability and water-conservation impact summary (Section 2.4 & 2.6)."""
    tickets = get_tickets()
    return calculate_facility_sustainability_summary(tickets)


# ── Daily Digests ─────────────────────────────────────────────────────────────

@app.get("/api/digests")
def get_digests():
    """Return stored end-of-day operational digests keyed by date."""
    return get_daily_digests(str(DB_PATH))


# ── AI Facility Copilot Chat ──────────────────────────────────────────────────

@app.post("/api/chat")
def chat_with_copilot(req: ChatRequest):
    """
    Conversational assistant for facility managers powered by Google Gemini.
    Strictly grounded in SQLite database metrics, ticket telemetry, and sustainability intelligence.
    """
    tickets = get_tickets()
    sust = calculate_facility_sustainability_summary(tickets)

    open_tickets = [t for t in tickets if str(t.get("status", "")).lower() != "resolved"]
    open_tickets.sort(key=lambda x: float(x.get("estimated_water_loss_liters") or 0.0), reverse=True)

    open_summary = []
    for t in open_tickets[:8]:
        ev = t.get("evidence") or {}
        flow_obs = float(ev.get("observed_flow_lpm") or (float(t.get("estimated_water_loss_liters") or 0.0) / 30.0 if float(t.get("estimated_water_loss_liters") or 0.0) > 0 else 0.0))
        flow_exp = float(ev.get("expected_flow_lpm") or 0.0)
        open_summary.append(
            f"- Fixture {t.get('fixture_id')} in {t.get('zone_id')}: {t.get('anomaly_type')} "
            f"[{t.get('severity_label')} Severity, score {t.get('severity_score')}/100], "
            f"Water lost: {float(t.get('estimated_water_loss_liters') or 0.0):.1f} L (cost: ₹{float(t.get('estimated_cost_impact') or 0.0):.2f}), "
            f"Flow: {flow_obs:.2f} LPM (baseline {flow_exp:.2f} LPM), Status: {t.get('status')}"
        )

    hw_fix = sust.get("highest_waste_fixture") or {}
    hw_zone = sust.get("highest_waste_zone") or {}

    grounding_context = f"""FACILITY DATABASE & TELEMETRY GROUNDING CONTEXT:
Sustainability & Conservation Overview:
- Total Water Wasted Across Facility: {sust.get('water_waste_liters', 0.0):.1f} Litres (utility cost: ₹{sust.get('cost_impact_inr', 0.0):.2f})
- Total Water Saved via Interventions: {sust.get('water_saved_liters', 0.0):.1f} Litres (avoided cost: ₹{sust.get('avoided_cost_inr', 0.0):.2f})
- Highest Waste Fixture: {hw_fix.get('fixture_id', 'None')} in {hw_fix.get('zone_id', 'None')} ({hw_fix.get('water_waste_liters', 0.0):.1f} Litres lost, ₹{hw_fix.get('cost_impact_inr', 0.0):.2f})
- Highest Waste Zone: {hw_zone.get('zone_id', 'None')} ({hw_zone.get('water_waste_liters', 0.0):.1f} Litres lost, ₹{hw_zone.get('cost_impact_inr', 0.0):.2f})
- Projected 24h Unresolved Water Loss: {sust.get('projected_unresolved_loss_24h_liters', 0.0):.1f} Litres

Active Open Tickets (ranked by water loss impact):
{chr(10).join(open_summary) if open_summary else "No active open tickets."}
"""

    model = get_copilot_model()
    if model:
        try:
            prompt = f"""You are the KOHLER Smart Facility Assistant, an intelligent operational copilot for airport restroom facility managers at Terminal 2.

{grounding_context}

User Query: {req.message}

GROUNDING RULES (STRICT):
1. Do not invent telemetry values, fixture names, or numbers. Base all answers strictly on the supplied grounding context.
2. If information is unavailable, say so clearly.
3. Provide a concise, professional, actionable response in 2-4 sentences.
4. Cite specific fixture IDs, zones, water loss (litres), and cost estimates when relevant. Use bold formatting for fixture names (e.g., **Sink_01**) and severity levels (e.g., **High**)."""

            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            return {"reply": raw_text}
        except Exception as e:
            print(f"[ERROR] Copilot model generation error: {e}")

    # Grounded deterministic fallback in case API is offline or quota reached
    worst_fix_name = hw_fix.get("fixture_id", "Sink_01")
    worst_zone_name = hw_fix.get("zone_id", "T2_Restroom_A")
    worst_liters = hw_fix.get("water_waste_liters", 0.0)
    worst_cost = hw_fix.get("cost_impact_inr", 0.0)
    total_waste = sust.get("water_waste_liters", 0.0)
    total_cost = sust.get("cost_impact_inr", 0.0)

    msg_lower = req.message.lower()
    if "worst" in msg_lower or "highest" in msg_lower or "leak" in msg_lower:
        return {
            "reply": (
                f"The fixture with the worst water waste right now is **{worst_fix_name}** in **{worst_zone_name}**, "
                f"which has accumulated **{worst_liters:.1f} Litres** of water loss (approx ₹{worst_cost:.2f} utility impact). "
                f"It is flagged with active **High** severity anomalies and requires immediate valve inspection."
            )
        }
    elif "cost" in msg_lower or "sustainability" in msg_lower or "saved" in msg_lower:
        return {
            "reply": (
                f"Across Terminal 2, cumulative water waste is **{total_waste:.1f} Litres** (approx ₹{total_cost:.2f} direct cost). "
                f"Maintenance interventions have saved an estimated **{sust.get('water_saved_liters', 0.0):.1f} Litres** (₹{sust.get('avoided_cost_inr', 0.0):.2f} avoided). "
                f"The primary loss hotspot remains **{worst_zone_name}**."
            )
        }
    else:
        return {
            "reply": (
                f"Currently monitoring **4 zones** across Terminal 2 with **{len(open_tickets)} open tickets** needing attention. "
                f"Priority focus should be directed to **{worst_fix_name}** in **{worst_zone_name}**, which accounts for "
                f"the highest single-fixture water loss at **{worst_liters:.1f} Litres**."
            )
        }
