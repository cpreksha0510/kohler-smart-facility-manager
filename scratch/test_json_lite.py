import os
import time
from pathlib import Path
import dotenv

dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

m = genai.GenerativeModel(
    "gemini-3.5-flash-lite",
    generation_config={
        "response_mime_type": "application/json",
        "temperature": 0.2,
    },
)

prompt = """You are a commercial plumbing facility telemetry intelligence system for KOHLER commercial facilities.
Generate an operational explanation for a maintenance ticket.

TICKET DATA:
- Fixture: Sink_01
- Zone: T2_Restroom_A
- Anomaly Type: sustained_leak
- Severity: High (Score: 72.0/100)
- Start Time: 2024-01-15 03:00:00
- Duration: 39 minutes
- Measured Flow: avg 3.50 LPM, peak 4.20 LPM
- Baseline Expected Flow: 0.05 LPM
- Occupancy: 0 (unoccupied throughout duration)
- Estimated Water Loss: 136.5 Litres (Cost Impact: Rs. 6.83)

REQUIREMENTS:
1. Write exactly 1 to 2 sentences explaining why this was flagged.
2. Reference the real telemetry numbers (duration, flow rate, baseline comparison, zero occupancy).
3. Be professional, concise, and operational for a commercial facility manager.
4. Output MUST be valid JSON with a single key "explanation".
"""

t0 = time.time()
res = m.generate_content(prompt)
dt = time.time() - t0
print(f"Time taken: {dt:.2f}s")
print("Response:", res.text)
