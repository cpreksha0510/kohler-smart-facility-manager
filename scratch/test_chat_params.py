import time
import os
import dotenv
from pathlib import Path

dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
import google.generativeai as genai

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Testing different generation configs for chat...")

prompt = """You are the KOHLER Smart Facility Assistant for Terminal 2.
Current telemetry context:
- Total tickets: 3, Open tickets: 3.
- Worst anomalies:
  - TICKET-2024-0001: Sink_01 (T2_Restroom_A), sustained_leak, Severity: High (72.0), Water lost: 555.3 L, Status: open
  - TICKET-2024-0002: Toilet_B1 (T2_Restroom_B), slow_drip, Severity: High (58.0), Water lost: 48.9 L, Status: open

User Query: Which fixture has the worst water waste right now?

Provide a concise, professional, actionable response in 2-4 sentences. Cite specific fixture IDs, zones, water loss (litres), and cost estimates when relevant. Use bold formatting for fixture names and severity levels."""

configs = [
    {"name": "Standard text (no json)", "config": {"temperature": 0.2, "max_output_tokens": 300}},
]

for item in configs:
    m = genai.GenerativeModel("gemini-3.6-flash", generation_config=item["config"])
    t0 = time.time()
    res = m.generate_content(prompt)
    dt = time.time() - t0
    print(f"\n[{item['name']}] Elapsed: {dt:.2f}s")
    print(res.text[:200] + "...")
