import os
import time
from pathlib import Path
import dotenv
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

candidates = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash"
]

prompt = "Hello! Confirm you work in one short sentence."

for c in candidates:
    try:
        m = genai.GenerativeModel(c, generation_config={"max_output_tokens": 50, "temperature": 0.2})
        t0 = time.time()
        # Request without retry loop to see immediate result
        res = m.generate_content(prompt, request_options={"timeout": 10})
        dt = time.time() - t0
        print(f"SUCCESS: {c} ({dt:.2f}s) -> {res.text.strip()}")
    except Exception as e:
        print(f"FAILED: {c} -> {type(e).__name__}: {e}")
