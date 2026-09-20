import os
import time
from pathlib import Path
import dotenv
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

candidates = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.6-flash"
]

prompt = "Hello! Give me a one-sentence reply confirming you work."

for c in candidates:
    try:
        m = genai.GenerativeModel(c, generation_config={"max_output_tokens": 50, "temperature": 0.2})
        t0 = time.time()
        res = m.generate_content(prompt)
        dt = time.time() - t0
        print(f"SUCCESS: {c} ({dt:.2f}s) -> {res.text.strip()}")
    except Exception as e:
        print(f"FAILED: {c} -> {e}")
