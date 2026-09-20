import os
import time
from pathlib import Path
import dotenv

dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

from src.config import DB_PATH
from src.database import get_tickets_df
from src.sustainability import calculate_facility_sustainability_summary
from src.explainability import build_ticket_evidence
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

df = get_tickets_df(str(DB_PATH))
tickets_list = []
for _, r in df.iterrows():
    t_dict = r.to_dict()
    t_dict["evidence"] = build_ticket_evidence(t_dict)
    tickets_list.append(t_dict)

sust = calculate_facility_sustainability_summary(tickets_list)
open_tickets = [t for t in tickets_list if t.get("status") != "resolved"]
open_tickets.sort(key=lambda x: float(x.get("estimated_water_loss_liters") or 0.0), reverse=True)

open_summary = []
for t in open_tickets[:6]:
    ev = t.get("evidence") or {}
    open_summary.append(
        f"- {t.get('fixture_id')} ({t.get('zone_id')}): {t.get('anomaly_type')}, "
        f"Severity: {t.get('severity_label')} (score {t.get('severity_score')}), "
        f"Water lost: {float(t.get('estimated_water_loss_liters') or 0.0):.1f} L, "
        f"Flow: {float(ev.get('observed_flow_lpm') or 0.0):.2f} LPM (baseline {float(ev.get('expected_flow_lpm') or 0.0):.2f} LPM), "
        f"Status: {t.get('status')}"
    )

prompt = f"""You are the KOHLER Smart Facility Assistant, an intelligent operational copilot for airport restroom facility managers at Terminal 2.

GROUNDING CONTEXT FROM FACILITY DATABASE & TELEMETRY:
Facility Sustainability & Water Impact:
- Total Water Wasted: {sust.get('water_waste_liters', 0.0):.1f} Litres (approx ₹{sust.get('cost_impact_inr', 0.0):.2f})
- Total Water Saved via Interventions: {sust.get('water_saved_liters', 0.0):.1f} Litres (Avoided: ₹{sust.get('avoided_cost_inr', 0.0):.2f})
- Highest Waste Fixture: {sust.get('highest_waste_fixture', {}).get('fixture_id')} ({sust.get('highest_waste_fixture', {}).get('zone_id')}) with {sust.get('highest_waste_fixture', {}).get('water_waste_liters', 0.0):.1f} Litres lost
- Highest Waste Zone: {sust.get('highest_waste_zone', {}).get('zone_id')} with {sust.get('highest_waste_zone', {}).get('water_waste_liters', 0.0):.1f} Litres lost
- Projected 24h Unresolved Waste: {sust.get('projected_unresolved_loss_24h_liters', 0.0):.1f} Litres

Active Open Tickets (ranked by water loss):
{chr(10).join(open_summary)}

User Query: Which fixture has the worst water waste right now?

GROUNDING INSTRUCTIONS:
1. Do not invent telemetry values, fixture names, or numbers. Base all answers strictly on the supplied grounding context.
2. Provide a concise, professional, actionable response in 2-4 sentences.
3. Cite specific fixture IDs, zones, water loss (litres), and cost estimates when relevant. Use bold formatting for fixture names (e.g., **Sink_01**) and severity levels (e.g., **High**).
"""

print("Sending prompt to gemini-3.5-flash-lite...")
m = genai.GenerativeModel(
    "gemini-3.5-flash-lite",
    generation_config={
        "temperature": 0.2,
        "max_output_tokens": 400,
    },
)
t0 = time.time()
res = m.generate_content(prompt)
dt = time.time() - t0
print(f"Time taken: {dt:.2f} seconds")
print("\nResponse:")
print(res.text)
