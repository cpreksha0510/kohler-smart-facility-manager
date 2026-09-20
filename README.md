# KOHLER Smart Facility Monitor — Airport Restroom Operations

> **Scenario:** Terminal 2 Restroom Block, International Airport  
> **Telemetry:** 4 Zones · 17 Smart Fixtures · 7-Day / 168-Hour Continuous Sensor Stream (1-min cadence, 171,360 readings)  
> **Backend Stack:** Python 3.10+ · FastAPI · Uvicorn · SQLite · Pandas · NumPy · Google Gemini API (`gemini-2.5-flash`)  
> **Frontend Stack:** Next.js 16 (Turbopack) · React 19 · TypeScript 5 · Tailwind CSS v4 · Recharts 3.10 · Lucide Icons  

---

## Demo Video

Watch the 1-3 minute walkthrough here:  
https://drive.google.com/file/d/16Xk0pKtHjQkwvdTcGfrMe5nFSJK2VV_I/view?usp=sharing

---

## Architecture Overview

The platform uses a decoupled industrial control-room architecture designed for high-throughput operational monitoring:

1. **Simulation & Ingestion Engine (`src/simulator.py`):** Generates 7 days (168 hours) of 1-minute water-sensor telemetry (flow rate, occupancy, pressure, temperature, sensor health) across 17 smart fixtures in 4 airport zones with diurnal passenger distributions, airport peak waves, and realistic distributed anomalies (sustained leaks, slow drips, stuck flush valves, and sensor noise traps).
2. **Deterministic 3-Pass Detection Engine (`src/detector.py`):**
   - *Pass 1:* Adaptive statistical baseline per `(fixture, hour_of_day)`.
   - *Pass 2:* Multi-signal correlation (zero occupancy validation, 10-min duration filter, sensor fault isolation, session coalescing).
   - *Pass 3:* Cumulative slow-drip scanner (0.25 LPM overnight drift detection).
   - *Composite Severity Scorer:* Weighted ranking (`Critical`, `High`, `Medium`, `Low`) and municipal water loss cost quantification.
3. **AI Explainability & Copilot Layer (`src/llm.py`):** Google Gemini generates plain-English, telemetry-cited incident explanations for flagged tickets and powers the conversational **AI Facility Copilot**.
4. **Fixture Health & Degradation Engine (`src/fixture_health.py`):** Computes per-fixture and facility-wide health scores (0–100) and historical degradation trends (`Deteriorating`, `Stable`, `Improving`) by evaluating recent vs. older anomaly frequency.
5. **Sustainability & Conservation Engine (`src/sustainability.py`):** Tracks total water waste, water saved through timely resolution, avoided municipal utility costs (₹), 24-hour projected unresolved loss, and zone-level conservation metrics aligned with Kohler EPA WaterSense benchmarks.
6. **FastAPI REST Service (`src/api.py`):** Exposes high-performance REST endpoints for summary metrics, downsampled time-series telemetry, occupancy heatmaps, ticket status updates with audit notes, fixture health degradation, sustainability summaries, and AI copilot queries.
7. **Modern Next.js Frontend (`frontend/`):** Enterprise command center with a unified `#080808` background and `#101010` surfaces, 4 dedicated tabs (Dashboard, Tickets, Sustainability, Fixture Health), 60 FPS Replay Simulator with rolling window telemetry, and slide-over AI Copilot drawer.

---

## Fresh Clone Setup & Run Instructions

Follow these steps in order to run both the Python backend and Next.js frontend from a fresh clone.

### Prerequisites
- **Python 3.10+** (with `pip`)
- **Node.js 18+** (with `npm`)
- *(Optional)* A Google Gemini API key (the system includes deterministic fallbacks if no key is provided).

---

### Step 1: Clone and Set Up Environment Variables

```bash
git clone <repo-url>
cd "kohler case study"
```

Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(If you do not have a key, the system runs with built-in deterministic fallback explanations).*

---

### Step 2: Install Python Backend Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3: Generate Telemetry Data & Run Anomaly Detection

```bash
# Generate 7 days (168 hours / 171,360 readings) across 17 fixtures into SQLite (facility.db)
python src/simulator.py

# Run the 3-pass multi-signal detector and generate LLM incident explanations
python src/detector.py
```

---

### Step 4: Launch the FastAPI Backend Server

In your first terminal window, start the REST API:
```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```
*API docs will be available at: `http://127.0.0.1:8000/docs`*

---

### Step 5: Install Frontend Dependencies & Start Next.js

In a **second terminal window**, navigate to the `frontend/` directory and start the dev server:

```bash
cd frontend
npm install
npm run dev
```

---

### Step 6: Open the Dashboard

Open your browser to:
```text
http://localhost:3000
```

---

## Platform Features Tour

### 1. Executive Dashboard (`Dashboard` Tab)
- **4 Real-Time KPI Cards:** Sensor Readings (171,360), Flagged Tickets, Facility Health Index (0–100), and Estimated Water Loss with utility cost impact (₹).
- **Flow Rate Telemetry (Recharts):** Aggregated Zone Totals and Per-Fixture Breakdown with distinct line styles (solid for sinks, dashed for toilets, dotted for urinals) and active anomaly highlights.
- **Occupancy Heatmap Matrix:** 17 fixtures monitored across 24 hours displaying diurnal traffic density with collapsible drawer.

### 2. Dedicated Tickets Tab (`Tickets` Tab)
- **Strict Severity Hierarchy:** Active tickets (`Open` / `Dispatched`) sorted strictly by severity tier (`Critical` → `High` → `Medium` → `Low`), and within tier by most recently flagged.
- **Status Progression Workflow:** One-click transitions (`Open` → `Dispatched` → `Resolved`) persisted directly to SQLite.
- **Audit Trail Resolution Notes:** Marking a ticket resolved prompts for an audit note with quick suggestion chips (*"Valve replaced"*, *"False alarm — sensor recalibrated"*, *"Supply fitting tightened"*, *"Flapper seal cleaned and tested"*).
- **Resolved Tickets History:** Collapsible audit log displaying past resolutions, technician notes, intervention impact, and reopen capability.
- **AI Telemetry Explainability & Evidence Breakdown:** Plain-English Google Gemini incident breakdown with an interactive evidence panel displaying telemetry baseline vs. observed flow, duration, and confidence.

### 3. Dedicated Sustainability Tab (`Sustainability` Tab)
- **Water Conservation Impact:** Quantifies cumulative water waste, water saved through prompt maintenance interventions, and municipal utility cost avoidance (₹).
- **Projected Unresolved Loss:** Projected 24-hour waste from currently open anomalies if left unaddressed.
- **Zone Breakdown:** Water conservation metrics and loss attribution per airport terminal zone.
- **Methodology Notice:** Grounded in standard municipal water rates (₹50 / kL) and Kohler commercial fixture baselines.

### 4. Dedicated Fixture Health Tab (`Fixture Health` Tab)
- **Facility Health Score:** 0–100 health gauge reflecting operational status across all 17 fixtures.
- **Status Tier Distribution:** Fixtures categorized into Optimal, Fair, and Needs Attention.
- **7-Day Trend Analysis:** Identifies fixtures as `Deteriorating`, `Stable`, or `Improving` based on recent vs. historical anomaly frequency.
- **Proactive Maintenance Actions:** Plain-English maintenance guidance for high-risk fixtures before catastrophic failures occur.

### 5. Replay Simulator (60 FPS Interactive Scrubbing)
- **168-Hour Timeline Scrubber:** Full 7-day timeline slider (`0h` to `168h`) with Play / Pause, Reset (`00:00`), Speed multipliers (`0.5x` to `8x`), and live Replay Clock.
- **Rolling Window Telemetry:** Zooms in on a readable recent window (`2h`, `4h`, `6h`) that smoothly auto-scrolls forward with the playback position.
- **Unified REPLAY JUMP Day Selector:** Single `D1` through `D7` selector toolbar that synchronizes playback position, scrubber position, and the rolling window chart simultaneously.
- **Dynamic Y-Axis Auto-Scaling:** Automatically adjusts chart scale (e.g. 0–2 L/min during quiet nocturnal hours to reveal micro-drips, expanding to 0–14 L/min during daytime peak waves).

### 6. Conversational AI Facility Copilot
- Slide-over sheet drawer powered by Google Gemini connected to live SQLite telemetry.
- Ask natural-language operational questions (e.g., *"Which fixture has the worst water waste right now?"*, *"What maintenance should I prioritize today?"*) for instant data-backed recommendations.

---

## Project Structure

```
├── facility_manager_prd.md       ← Full product specification
├── prompts_log.md                ← Comprehensive prompt-by-prompt build history
├── README.md                     ← Project documentation & setup guide
├── requirements.txt              ← Python backend dependencies
├── facility.db                   ← SQLite database (telemetry, tickets, digests)
├── src/
│   ├── api.py                    ← FastAPI REST API server
│   ├── config.py                 ← Constants: zones, fixtures, costs, thresholds
│   ├── database.py               ← SQLite schema migrations & query helpers
│   ├── detector.py               ← 3-pass multi-signal anomaly detector
│   ├── explainability.py         ← Telemetry-cited incident evidence builder
│   ├── fixture_health.py         ← Fixture health scoring & degradation trends
│   ├── llm.py                    ← Google Gemini explainability & copilot service
│   ├── simulator.py              ← 7-day telemetry generator & anomaly injector
│   └── sustainability.py         ← Water conservation & financial loss engine
└── frontend/                     ← Next.js 16 Web Application
    ├── package.json              ← Node.js dependencies
    ├── next.config.ts            ← API rewrites proxying to FastAPI (:8000)
    ├── app/
    │   ├── page.tsx              ← Main dashboard, tab routing & state manager
    │   ├── layout.tsx            ← Root layout & Geist font styling
    │   └── globals.css           ← Centralized #080808 / #101010 theme tokens
    └── components/
        ├── Header.tsx            ← Brand lockup, tab navigation & mode toggle
        ├── MetricCards.tsx       ← Glassmorphic KPI metric summary cards
        ├── FlowRateChart.tsx     ← Rolling window & full timeline Recharts canvas
        ├── OccupancyHeatmap.tsx  ← 24-hour occupancy matrix with accordion
        ├── TicketsView.tsx       ← Dedicated Tickets tab with resolution modal
        ├── EvidencePanel.tsx     ← Telemetry evidence breakdown panel
        ├── SustainabilityPanel.tsx ← Dedicated Sustainability & Conservation tab
        ├── FixtureHealthView.tsx ← Dedicated Fixture Health & Degradation tab
        ├── ReplayScrubber.tsx    ← 60 FPS timeline scrubber & clock
        ├── AiCopilotDrawer.tsx   ← Conversational Gemini AI drawer
        └── types.ts              ← Shared TypeScript data interfaces
```
