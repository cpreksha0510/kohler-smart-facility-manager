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
        for candidate in [GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK, "gemini-flash-latest"]:
            try:
                m = genai.GenerativeModel(
                    candidate,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                    },
                )
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


# Global copilot model cache
_cached_copilot_model = None


def get_copilot_model() -> Optional[Any]:
    """
    Initialize and return a Generative AI model instance configured for facility copilot chat.
    Uses text format (without forcing JSON MIME type) with low temperature and bounded tokens
    for low-latency, grounded conversational responses.
    """
    global _cached_copilot_model

    if _cached_copilot_model is not None:
        return _cached_copilot_model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        for candidate in [GEMINI_MODEL_PRIMARY, GEMINI_MODEL_FALLBACK, "gemini-flash-latest"]:
            try:
                m = genai.GenerativeModel(
                    candidate,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 400,
                    },
                )
                _cached_copilot_model = m
                return _cached_copilot_model
            except Exception:
                continue

        return None
    except Exception as e:
        logger.error(f"Error initializing Copilot model: {e}")
        return None


def _deterministic_ticket_fallback(ticket: dict) -> str:
    """Generate a concise operational root-cause diagnosis without repeating UI metrics."""
    atype = ticket.get("anomaly_type", "anomaly")
    fixture_id = ticket.get("fixture_id", "Fixture")

    if atype == "sustained_leak":
        return (
            f"Probable solenoid diaphragm failure or supply line rupture causing unseated flow. "
            f"Immediate isolation of supply stop valve and cartridge inspection recommended."
        )
    elif atype == "slow_drip":
        return (
            f"Persistent continuous creep indicates internal seal wear, cartridge debris, or flush valve seating failure. "
            f"Inspect and reseat valve seals."
        )
    elif atype == "sensor_fault":
        return (
            f"Telemetry inconsistency detected against physical baselines. "
            f"Perform sensor recalibration and verify optical flow transducer connection."
        )
    else:
        return (
            f"Anomalous flow profile inconsistent with passenger usage. "
            f"Dispatch technician to inspect physical valve assembly and check for obstruction."
        )


def generate_ticket_explanation(ticket: dict) -> str:
    """
    Generate a 1-2 sentence plain-English operational explanation for a flagged ticket.
    Focuses strictly on root-cause diagnosis and maintenance action, avoiding repetition
    of metrics already visible in the UI telemetry row and evidence bars.
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

    prompt = f"""You are a commercial plumbing intelligence system for KOHLER commercial facilities.
Generate a concise root-cause diagnostic hypothesis and recommended maintenance action for an anomaly ticket.

TICKET TELEMETRY CONTEXT (Already displayed in UI):
- Fixture: {fixture_id} ({zone_id})
- Anomaly Type: {anomaly_type}
- Severity: {severity_label} (Score: {severity_score}/100)
- Measured Flow: avg {avg_flow:.2f} LPM, peak {max_flow:.2f} LPM vs {base_flow:.2f} LPM baseline
- Duration: {duration_min} minutes during zero occupancy
- Estimated Water Loss: {water_l:.1f} Litres

REQUIREMENTS:
1. Write exactly 1 to 2 sentences focusing STRICTLY on the probable mechanical root cause and recommended technician action.
2. DO NOT repeat numbers already visible in the UI (do NOT repeat duration in minutes, flow in LPM, liters lost, zone name, or severity labels).
3. Focus on practical commercial plumbing diagnoses (e.g., solenoid diaphragm tear, worn cartridge seal, mineral scale preventing valve seating, stuck flapper).
4. Output MUST be valid JSON with a single key "explanation".

Example format:
{{"explanation": "Probable internal solenoid valve failure or cartridge seal wear causing unseated flow during unoccupied hours. Dispatch technician to isolate supply stop valve and replace cartridge."}}
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
