"""
sustainability.py — Water-Savings & Sustainability Impact Engine (Feature 2).

Implements Section 2 of the KOHLER Smart Facility Plan:
1. Incident Projection (Section 2.2):
   Calculates runaway unresolved water loss across 1h, 6h, 24h, and 7d horizons
   based on observed flow telemetry.
2. Counterfactual Prevented Waste (Section 2.3):
   When a ticket is resolved, calculates:
     estimated_water_saved = potential_loss_without_intervention - actual_loss_before_resolution
   Strictly labeled as "Estimated water saved (simulation-based counterfactual model)"
   per Section 9 Rules 5 & 6 — never called "actual savings".
3. Facility-Level Sustainability Summary (Section 2.4 & 2.6):
   Aggregates total waste, estimated water saved, avoided cost, projected unresolved loss,
   and hotspot fixtures/zones.
"""

from typing import Any, Dict, List, Optional
import numpy as np

WATER_COST_PER_LITER: float = 0.05  # ₹0.05 per Litre (midpoint commercial tariff)
COUNTERFACTUAL_UNRESOLVED_HOURS: float = 24.0  # standard unassisted leak discovery baseline


def calculate_incident_projection(observed_flow_lpm: float) -> Dict[str, Any]:
    """
    Calculate projected runaway water loss for an unresolved incident across
    1 hour, 6 hours, 24 hours, and 7 days (Section 2.2).
    """
    flow = max(float(observed_flow_lpm), 0.0)
    
    horizons = {
        "1h": 60,
        "6h": 360,
        "24h": 1440,
        "7d": 10080,
    }

    projections = {}
    for key, minutes in horizons.items():
        loss_liters = round(flow * minutes, 1)
        cost_inr = round(loss_liters * WATER_COST_PER_LITER, 2)
        projections[key] = {
            "duration_minutes": minutes,
            "projected_loss_liters": loss_liters,
            "projected_cost_inr": cost_inr,
        }

    return projections


def calculate_intervention_impact(
    actual_loss_liters: float,
    observed_flow_lpm: float,
    duration_min: int = 0,
) -> Dict[str, Any]:
    """
    Calculate counterfactual prevented waste when a ticket is resolved (Section 2.3).
    Model: In the absence of automated detection and maintenance dispatch,
    the failure would continue unabated until standard 24-hour cycle inspection.
    """
    actual_loss = max(float(actual_loss_liters), 0.0)
    flow = max(float(observed_flow_lpm), 0.0)
    
    # Counterfactual benchmark: 24 hours unassisted runtime or 1.5x observed duration
    unassisted_minutes = max(COUNTERFACTUAL_UNRESOLVED_HOURS * 60, duration_min * 1.5)
    potential_unassisted_loss = round(flow * unassisted_minutes, 1)

    # Ensure counterfactual potential loss is at least the actual loss
    potential_unassisted_loss = max(potential_unassisted_loss, actual_loss)

    # Estimated water saved (counterfactual counter-model)
    water_saved = round(max(potential_unassisted_loss - actual_loss, 0.0), 1)
    avoided_cost = round(water_saved * WATER_COST_PER_LITER, 2)

    return {
        "actual_loss_liters": round(actual_loss, 1),
        "potential_unassisted_loss_liters": potential_unassisted_loss,
        "estimated_water_saved_liters": water_saved,
        "avoided_cost_inr": avoided_cost,
        "counterfactual_horizon_hours": COUNTERFACTUAL_UNRESOLVED_HOURS,
        "model_label": "Simulation-derived counterfactual model (24h unassisted baseline)",
    }


def calculate_facility_sustainability_summary(tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate facility-level sustainability intelligence metrics (Section 2.4 & 2.6).
    Derived dynamically from active and resolved ticket records.
    """
    total_waste_liters = 0.0
    total_saved_liters = 0.0
    projected_24h_liters = 0.0
    projected_7d_liters = 0.0

    zone_stats: Dict[str, Dict[str, Any]] = {}
    fixture_stats: Dict[str, Dict[str, Any]] = {}

    for t in tickets:
        status = str(t.get("status", "open")).lower()
        zone_id = str(t.get("zone_id", "Unknown"))
        fixture_id = str(t.get("fixture_id", "Unknown"))
        loss = float(t.get("estimated_water_loss_liters") or 0.0)

        total_waste_liters += loss

        # Zone stats
        if zone_id not in zone_stats:
            zone_stats[zone_id] = {
                "zone_id": zone_id,
                "water_waste_liters": 0.0,
                "water_saved_liters": 0.0,
                "cost_impact_inr": 0.0,
                "avoided_cost_inr": 0.0,
                "open_count": 0,
                "resolved_count": 0,
            }
        zone_stats[zone_id]["water_waste_liters"] += loss
        zone_stats[zone_id]["cost_impact_inr"] += round(loss * WATER_COST_PER_LITER, 2)

        # Fixture stats
        if fixture_id not in fixture_stats:
            fixture_stats[fixture_id] = {
                "fixture_id": fixture_id,
                "zone_id": zone_id,
                "water_waste_liters": 0.0,
                "ticket_count": 0,
            }
        fixture_stats[fixture_id]["water_waste_liters"] += loss
        fixture_stats[fixture_id]["ticket_count"] += 1

        # Extract flow rate for projection or intervention impact
        evidence = t.get("evidence") or {}
        flow_lpm = float(evidence.get("observed_flow_lpm") or (loss / 30.0 if loss > 0 else 0.25))
        duration_min = int(evidence.get("duration_minutes") or 30)

        if status == "resolved":
            zone_stats[zone_id]["resolved_count"] += 1
            impact = calculate_intervention_impact(loss, flow_lpm, duration_min)
            saved = impact["estimated_water_saved_liters"]
            total_saved_liters += saved
            zone_stats[zone_id]["water_saved_liters"] += saved
            zone_stats[zone_id]["avoided_cost_inr"] += impact["avoided_cost_inr"]
        else:
            zone_stats[zone_id]["open_count"] += 1
            proj = calculate_incident_projection(flow_lpm)
            projected_24h_liters += proj["24h"]["projected_loss_liters"]
            projected_7d_liters += proj["7d"]["projected_loss_liters"]

    # Highest waste hotspot identification
    highest_fixture = None
    if fixture_stats:
        top_fix = max(fixture_stats.values(), key=lambda x: x["water_waste_liters"])
        highest_fixture = {
            "fixture_id": top_fix["fixture_id"],
            "zone_id": top_fix["zone_id"],
            "water_waste_liters": round(top_fix["water_waste_liters"], 1),
            "cost_impact_inr": round(top_fix["water_waste_liters"] * WATER_COST_PER_LITER, 2),
            "ticket_count": top_fix["ticket_count"],
        }

    highest_zone = None
    if zone_stats:
        top_zone = max(zone_stats.values(), key=lambda x: x["water_waste_liters"])
        highest_zone = {
            "zone_id": top_zone["zone_id"],
            "water_waste_liters": round(top_zone["water_waste_liters"], 1),
            "cost_impact_inr": round(top_zone["water_waste_liters"] * WATER_COST_PER_LITER, 2),
            "open_count": top_zone["open_count"],
            "resolved_count": top_zone["resolved_count"],
        }

    total_cost_impact = round(total_waste_liters * WATER_COST_PER_LITER, 2)
    total_avoided_cost = round(total_saved_liters * WATER_COST_PER_LITER, 2)

    return {
        "water_waste_liters": round(total_waste_liters, 1),
        "water_saved_liters": round(total_saved_liters, 1),
        "cost_impact_inr": total_cost_impact,
        "avoided_cost_inr": total_avoided_cost,
        "projected_unresolved_loss_24h_liters": round(projected_24h_liters, 1),
        "projected_unresolved_loss_7d_liters": round(projected_7d_liters, 1),
        "highest_waste_fixture": highest_fixture,
        "highest_waste_zone": highest_zone,
        "zone_breakdown": [
            {
                **z,
                "water_waste_liters": round(z["water_waste_liters"], 1),
                "water_saved_liters": round(z["water_saved_liters"], 1),
                "cost_impact_inr": round(z["cost_impact_inr"], 2),
                "avoided_cost_inr": round(z["avoided_cost_inr"], 2),
            }
            for z in zone_stats.values()
        ],
        "model_notice": "Prevented waste values are simulation-derived counterfactual estimates based on 24-hour unassisted runtimes.",
    }
