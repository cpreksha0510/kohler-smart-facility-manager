import time
import os
import dotenv
dotenv.load_dotenv()
from src.api import get_tickets_df, DB_PATH, get_gemini_model

tickets_df = get_tickets_df(str(DB_PATH))
tickets_summary = ""
for _, r in tickets_df.head(5).iterrows():
    tickets_summary += f"- {r['ticket_id']}: {r['fixture_id']} ({r['zone_id']}), {r['anomaly_type']}, Severity: {r['severity_label']} ({r['severity_score']}), Water lost: {r['estimated_water_loss_liters']} L\n"

model = get_gemini_model()
prompt = f"""You are the KOHLER Smart Facility Assistant, an intelligent operational copilot for airport restroom managers at Terminal 2.
Current telemetry context from SQLite database:
{tickets_summary}

User Query: what needs my attention right now?

Provide a concise, professional, actionable response in 2-4 sentences. Cite specific fixture IDs, zones, water loss (litres), and cost estimates when relevant. Use bold formatting for fixture names and severity levels."""

print("Calling generate_content...")
t0 = time.time()
res = model.generate_content(prompt)
elapsed = round(time.time() - t0, 2)
print("Generate time:", elapsed, "seconds")
print("Response text:", res.text)
