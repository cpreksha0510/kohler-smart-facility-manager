# KOHLER Smart Facility Monitor — Airport Restroom Operations

> **Scenario:** Terminal 2 Restroom Block, International Airport  
> **Telemetry:** 4 Zones · 17 Smart Fixtures · 48-Hour Continuous Sensor Stream (1-min cadence)  
> **Backend Stack:** Python 3.10+ · FastAPI · Uvicorn · SQLite · Pandas · NumPy · Google Gemini API (`gemini-2.5-flash`)  
> **Frontend Stack:** Next.js 15 (Turbopack) · React 19 · TypeScript · Tailwind CSS v4 · Recharts · Lucide Icons  

---

## Architecture Overview

The platform uses a decoupled industrial control-room architecture:
1. **Simulation & Ingestion Engine (`src/simulator.py`):** Generates 48 hours of 1-minute water-sensor telemetry (flow rate, occupancy, pressure, temperature, sensor health) across 17 smart fixtures in 4 airport zones with realistic diurnal traffic distributions and injected anomalies.
2. **Deterministic 3-Pass Detection Engine (`src/detector.py`):** 
   - *Pass 1:* Adaptive statistical baseline per `(fixture, hour_of_day)`.
   - *Pass 2:* Multi-signal correlation (zero occupancy validation, 10-min duration filter, sensor fault isolation, session coalescing).
   - *Pass 3:* Cumulative slow-drip scanner (0.25 LPM overnight drift detection).
   - *Composite Severity Scorer:* Weighted composite ranking (`Critical`, `High`, `Medium`, `Low`) and municipal water loss cost quantification.
3. **AI Explainability & Copilot Layer (`src/llm.py`):** Google Gemini generates plain-English, telemetry-cited incident explanations for flagged tickets and powers the conversational **AI Facility Copilot**.
4. **FastAPI REST Service (`src/api.py`):** Exposes high-performance REST endpoints for summary metrics, time-series telemetry, occupancy heatmaps, ticket status updates with resolution notes, and AI copilot queries.
5. **Modern Next.js Frontend (`frontend/`):** Dark/brass executive command center with 4 KPI cards, Recharts flow telemetry, 24-hour occupancy heatmap, dedicated **Tickets Queue** with resolution notes modal, 60 FPS Replay Simulator, and slide-over AI Copilot drawer.

---

## Fresh Clone Setup & Run Instructions

Follow these steps in order to run both the Python backend and Next.js frontend from a fresh clone.

### Prerequisites
- **Python 3.10+** (with `pip`)
- **Node.js 18+** (with `npm`)
- *(Optional)* A Google Gemini API key (the system includes graceful deterministic fallbacks if no key is provided).

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
*(If you do not have a key, the system runs with deterministic fallback explanations).*

---

### Step 2: Install Python Backend Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 3: Generate Telemetry Data & Run Anomaly Detection

```bash
# Generate 48 hours of sensor readings across 17 fixtures into SQLite (facility.db)
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

### 1. Executive Dashboard (`/`)
- **4 Real-Time KPI Cards:** Sensor readings (48,960), active tickets requiring attention, monitored zones (4 zones), and cumulative water loss in liters with utility cost impact (₹).
- **Flow Rate Telemetry (Recharts):** Aggregated Zone Totals and Per-Fixture Breakdown with distinct line styles (solid for sinks, dashed for toilets, dotted for urinals) and Sink_01 hero leak highlighting.
- **Occupancy Heatmap Matrix:** 17 fixtures monitored across 24 hours displaying diurnal traffic density.
- **Daily Operational Digest:** Summary of Low/Medium priority maintenance items.

### 2. Dedicated Tickets Queue Tab
- **Strict Severity Hierarchy:** Active tickets (`Open` / `Dispatched`) sorted strictly by severity tier (`Critical` → `High` → `Medium` → `Low`), and within tier by most recently flagged.
- **Status Progression:** One-click transition (`Open` → `Dispatched` → `Resolved`) persisted directly to SQLite.
- **Audit Trail Resolution Notes:** Marking a ticket resolved prompts for an audit note with quick suggestion chips (*"Valve replaced"*, *"Sensor recalibrated"*, etc.).
- **Resolved Tickets Section:** Collapsible audit log displaying past resolutions, technician notes, and reopen capability.
- **AI Telemetry Explainability:** Responsive multi-line Google Gemini incident breakdown on every ticket.

### 3. Replay Simulator (60 FPS Client-Side Scrubbing)
- 48-hour timeline scrubber slider with Play / Pause, Reset, and speed controls (`0.5x` to `8x`).
- Complete 48-hour canvas with streaming telemetry lines advancing dynamically up to the scrubber position.

### 4. Conversational AI Facility Copilot
- Slide-over sheet drawer powered by Google Gemini connected to live SQLite telemetry.
- Ask natural-language operational questions (e.g., *"Which fixture has the worst water waste right now?"*) for instant data-backed maintenance recommendations.

---

## Project Structure

```
├── facility_manager_prd.md   ← Full product specification
├── prompts_log.md            ← Comprehensive prompt-by-prompt build history
├── README.md                 ← This file
├── requirements.txt          ← Python backend dependencies
├── facility.db               ← SQLite database (telemetry, tickets, digests)
├── src/
│   ├── api.py                ← FastAPI REST API server
│   ├── config.py             ← Constants: zones, fixtures, costs, thresholds
│   ├── database.py           ← SQLite schema migrations & query helpers
│   ├── detector.py           ← 3-pass multi-signal anomaly detector
│   ├── llm.py                ← Google Gemini explainability & copilot service
│   ├── simulator.py          ← 48-hour telemetry generator & anomaly injector
│   └── icons.py              ← SVG outline icon definitions
└── frontend/                 ← Next.js 15 Web Application
    ├── package.json          ← Node.js dependencies
    ├── next.config.ts        ← API rewrites proxying to FastAPI (:8000)
    ├── app/
    │   ├── page.tsx          ← Main dashboard & tab controller
    │   └── layout.tsx        ← Root layout & styling
    └── components/
        ├── Header.tsx         ← Brand lockup, tab navigation & mode toggle
        ├── MetricCards.tsx    ← Glassmorphic KPI metric summary cards
        ├── FlowRateChart.tsx  ← Recharts flow telemetry with 48h replay canvas
        ├── OccupancyHeatmap.tsx ← 24-hour occupancy matrix
        ├── TicketsView.tsx    ← Dedicated Tickets Queue with resolution modal
        ├── TicketsTable.tsx   ← Dashboard ticket table preview
        ├── DailyDigestCard.tsx← Operational daily digest
        ├── ReplayScrubber.tsx ← 60 FPS timeline scrubber & clock
        └── AiCopilotDrawer.tsx← Conversational Gemini AI drawer
```
