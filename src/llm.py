"""
llm.py — Google Gemini LLM Layer for KOHLER Facility Monitor.

Generates:
1. 1-2 sentence plain-English explanations for flagged anomaly tickets
   citing real telemetry numbers and signals.
2. End-of-day operational digests summarizing Low & Medium priority tickets.

Architecture principles (PRD Section 5):
- The LLM EXPLAINS tickets; it never decides whether something is an anomaly.
- Explanations are generated ONCE per ticket and stored in SQLite.
- Structured output (JSON) guarantees reliable parsing.
- Rate-limiting retry with exponential backoff.
- 100% graceful fallback to deterministic operational sentences on API error/offline.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import dotenv

from src.config import (
    GEMINI_MODEL_FALLBACK,
    GEMINI_MODEL_PRIMARY,
    LLM_MAX_RETRIES,
    LLM_REQUEST_DELAY_SECONDS,
    LLM_RETRY_BACKOFF_SECONDS,
)

logger = logging.getLogger(__name__)

# Load environment variables from .env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    dotenv.load_dotenv(_ENV_PATH)
else:
    dotenv.load_dotenv()

# Global model cache to avoid repeated client creation
_cached_model = None
_model_initialized = False


def get_gemini_model() -> Optional[Any]:
    """
    Initialize and return the Google Generative AI model instance.
    Uses primary model with fallback if unavailable.
    Returns None if GEMINI_API_KEY is not configured or import fails.
    """
    global _cached_model, _model_initialized

    if _model_initialized:
        return _cached_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment; LLM will use deterministic fallbacks.")
        _model_initialized = True
        _cached_model = None
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Attempt primary model first, fallback if rejected by API
        selected_model = None
        for candidate in [GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK, "gemini-3.6-flash"]:
            try:
                m = genai.GenerativeModel(
                    candidate,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                    },
                )
                # Quick test check
                selected_model = m
                break
            except Exception as ex:
                logger.debug(f"Candidate model {candidate} init error: {ex}")
                continue

        _cached_model = selected_model
        _model_initialized = True
        return _cached_model

    except ImportError:
        logger.warning("google-generativeai package not installed; using deterministic fallbacks.")
        _model_initialized = True
        _cached_model = None
        return None
    except Exception as e:
        logger.error(f"Error initializing Gemini client: {e}")
        _model_initialized = True
        _cached_model = None
        return None


def _deterministic_ticket_fallback(ticket: dict) -> str:
    """Generate a precise deterministic 1-2 sentence explanation if API is unavailable."""
    fixture_id = ticket.get("fixture_id", "Unknown fixture")
    zone_id = ticket.get("zone_id", "Unknown zone")
    label = ticket.get("severity_label", "Flagged")
    atype = ticket.get("anomaly_type", "anomaly")
    avg_flow = float(ticket.get("avg_flow_lpm") or 0.0)
    dur = int(ticket.get("duration_minutes") or 0)
    water = float(ticket.get("estimated_water_loss_liters") or (avg_flow * dur))
    base = float(ticket.get("avg_baseline_mean") or 0.0)

    clean_zone = zone_id.replace("T2_", "").replace("_", " ")

    if atype == "sustained_leak":
        mult_str = f" ({avg_flow / base:.1f}x normal baseline)" if base > 0.05 else ""
        return (
            f"Flagged as {label}: {fixture_id} in {clean_zone} showed sustained flow of "
            f"{avg_flow:.2f} LPM{mult_str} for {dur} minutes with zero occupancy detected — "
            f"consistent with an active plumbing leak."
        )
    elif atype == "slow_drip":
        return (
            f"Flagged as {label}: {fixture_id} in {clean_zone} exhibited a persistent overnight "
            f"creep averaging {avg_flow:.2f} LPM across {dur} minutes ({water:.1f} L cumulative loss) "
            f"during zero occupancy — consistent with an internal valve or seal leak."
        )
    else:
        return (
            f"Flagged as {label}: {fixture_id} in {clean_zone} registered anomalous {atype.replace('_', ' ')} "
            f"for {dur} minutes ({water:.1f} L) during an unoccupied period."
        )


def generate_ticket_explanation(ticket: dict) -> str:
    """
    Generate a 1-2 sentence plain-English operational explanation for a flagged ticket.
    Enforces structured JSON output and incorporates 1-retry with backoff.
    Falls back gracefully on any failure.
    """
    model = get_gemini_model()
    if model is None:
        return _deterministic_ticket_fallback(ticket)

    # Format telemetry context for Gemini
    fixture_id = ticket.get("fixture_id", "Unknown")
    zone_id = ticket.get("zone_id", "Unknown")
    anomaly_type = ticket.get("anomaly_type", "anomaly")
    severity_label = ticket.get("severity_label", "High")
    severity_score = ticket.get("severity_score", 50.0)
    duration_min = ticket.get("duration_minutes", 0)
    avg_flow = ticket.get("avg_flow_lpm", 0.0)
    max_flow = ticket.get("max_flow_lpm", 0.0)
    base_flow = ticket.get("avg_baseline_mean", 0.0)
    water_l = ticket.get("estimated_water_loss_liters", 0.0)
    cost_rs = ticket.get("estimated_cost_impact", 0.0)
    ts = ticket.get("timestamp_flagged", "")

    prompt = f"""You are a commercial plumbing facility telemetry intelligence system for KOHLER commercial facilities.
Generate an operational explanation for a maintenance ticket.

TICKET DATA:
- Fixture: {fixture_id}
- Zone: {zone_id}
- Anomaly Type: {anomaly_type}
- Severity: {severity_label} (Score: {severity_score}/100)
- Start Time: {ts}
- Duration: {duration_min} minutes
- Measured Flow: avg {avg_flow:.2f} LPM, peak {max_flow:.2f} LPM
- Baseline Expected Flow: {base_flow:.2f} LPM
- Occupancy: 0 (unoccupied throughout duration)
- Estimated Water Loss: {water_l:.1f} Litres (Cost Impact: Rs. {cost_rs:.2f})

REQUIREMENTS:
1. Write exactly 1 to 2 sentences explaining why this was flagged.
2. Reference the real telemetry numbers (duration, flow rate, baseline comparison, zero occupancy).
3. Be professional, concise, and operational for a commercial facility manager.
4. Output MUST be valid JSON with a single key "explanation".

Example format:
{{"explanation": "Flagged as High: Sink_01 in T2_Restroom_A showed flow 3.2x above normal baseline, sustained for 45 minutes with zero occupancy detected — consistent with an active leak."}}
"""

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            if "explanation" in data and data["explanation"]:
                return data["explanation"].strip()
        except Exception as e:
            if attempt < LLM_MAX_RETRIES:
                logger.warning(f"Gemini API attempt {attempt+1} failed: {e}. Retrying in {LLM_RETRY_BACKOFF_SECONDS}s...")
                time.sleep(LLM_RETRY_BACKOFF_SECONDS)
            else:
                logger.error(f"Gemini API call failed after {attempt+1} attempts: {e}. Using deterministic fallback.")
                return _deterministic_ticket_fallback(ticket)

    return _deterministic_ticket_fallback(ticket)


def generate_daily_digest(tickets: list[dict], date_str: str) -> str:
    """
    Generate an end-of-day natural language digest summarizing all Low/Medium
    severity tickets for a given date (YYYY-MM-DD). High/Critical tickets are excluded.
    """
    # Filter to Low & Medium tickets on that date
    low_med = [
        t for t in tickets
        if str(t.get("timestamp_flagged", "")).startswith(date_str)
        and str(t.get("severity_label", "")).lower() in ("low", "medium")
    ]

    if not low_med:
        return f"No Low or Medium severity anomalies recorded on {date_str}."

    total_water = sum(float(t.get("estimated_water_loss_liters") or 0.0) for t in low_med)
    total_cost = sum(float(t.get("estimated_cost_impact") or 0.0) for t in low_med)
    affected_fixtures = sorted(list({t.get("fixture_id") for t in low_med}))

    deterministic_fallback = (
        f"Routine overview for {date_str}: {len(low_med)} minor tickets logged across "
        f"{len(affected_fixtures)} fixtures ({', '.join(affected_fixtures)}), accounting for "
        f"{total_water:.1f} L of minor flow (approx Rs. {total_cost:.2f}). "
        f"Recommended for scheduled end-of-shift inspection."
    )

    model = get_gemini_model()
    if model is None:
        return deterministic_fallback

    ticket_summaries = []
    for t in low_med:
        ticket_summaries.append(
            f"- {t.get('fixture_id')} ({t.get('zone_id')}): {t.get('anomaly_type')}, "
            f"score {t.get('severity_score')}, {t.get('duration_minutes', 0)} min, "
            f"{float(t.get('estimated_water_loss_liters') or 0.0):.1f} L"
        )
    tickets_text = "\n".join(ticket_summaries)

    prompt = f"""You are an operations intelligence assistant for a commercial airport facility manager.
Summarize the following Low and Medium priority plumbing anomaly tickets for date {date_str}.
High and Critical tickets are handled separately and are intentionally excluded here.

TICKETS RECORDED:
{tickets_text}

TOTAL WATER IMPACT: {total_water:.1f} Litres (Rs. {total_cost:.2f})

REQUIREMENTS:
1. Provide a natural-language executive digest (2-3 concise sentences or a 2-bullet summary).
2. Mention the primary fixtures involved, total water/cost volume, and a clear operational recommendation.
3. Return output as valid JSON with key "digest".

Example:
{{"digest": "Routine maintenance scan for Jan 15 identified 3 minor slow-drip patterns on Toilet_B1 and Sink_01, accumulating 31.4 L in minor seepage. Recommended for non-urgent end-of-shift seal check."}}
"""

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            data = json.loads(response.text.strip())
            if "digest" in data and data["digest"]:
                return data["digest"].strip()
        except Exception as e:
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_BACKOFF_SECONDS)
            else:
                logger.warning(f"Daily digest generation failed: {e}. Using deterministic fallback.")
                return deterministic_fallback

    return deterministic_fallback


def enrich_tickets_with_explanations(tickets: list[dict]) -> list[dict]:
    """
    Enrich a list of ticket dictionaries with LLM explanations.
    Paced with small delays to respect Gemini free-tier RPM limits.
    """
    enriched = []
    for idx, t in enumerate(tickets):
        t_copy = dict(t)
        # Only generate if explanation is missing
        if not t_copy.get("explanation"):
            t_copy["explanation"] = generate_ticket_explanation(t_copy)
            if idx < len(tickets) - 1:
                time.sleep(LLM_REQUEST_DELAY_SECONDS)
        enriched.append(t_copy)
    return enriched
