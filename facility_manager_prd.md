# Commercial Smart Facility & Sustainability Manager — Project Spec

## 1. Project Overview

**One-line goal:** Build a system that monitors simulated water/occupancy sensor data from a commercial facility, detects abnormal usage patterns (leaks, hygiene threshold breaches) using multi-signal reasoning (not flat thresholds), and auto-generates prioritized maintenance tickets — displayed on a live dashboard with an LLM-generated natural-language summary layer.

**Scenario context (use this in your simulated data and demo):** A KOHLER-equipped commercial facility (pick one: airport restroom block, hospital ward, university building) with multiple restroom zones, each with flow sensors, occupancy sensors, flush counters, and diagnostic status per fixture.

**Why this matters (ties to grading criteria):**
- Approach & Innovation (45%): the detection logic (Section 4) is the core of this — multi-signal reasoning, adaptive baselines, severity scoring, not a single if-then rule.
- Technical Execution (25%): working simulator → detection → storage → dashboard pipeline.
- UX & Feasibility (20%): live dashboard, clear tickets, real-world deployable logic.
- Business & Sustainability Impact (10%): water/cost savings estimation tied to KOHLER's water-conservation mission.

---

## 2. Tech Stack (kept deliberately simple to reduce build risk)

| Layer | Choice | Why |
|---|---|---|
| Data simulation | Python script | Generates synthetic sensor readings + injected anomalies |
| Storage | SQLite | Zero setup, good enough for demo scale |
| Detection logic | Python (pandas + plain arithmetic, no ML required) | See Section 4 |
| Backend/API | FastAPI (optional if dashboard needs an API layer) or direct SQLite reads from Streamlit | Simplicity first |
| Dashboard | Streamlit | Fastest way to get a live-updating, good-looking UI without frontend overhead |
| LLM layer | Claude or GPT API | Natural-language summaries + explanation of why a ticket was flagged |
| Docs | This file + a running prompts log | Required submission artifact |

No WebSockets, no time-series DB (InfluxDB/Timescale), no ML model required for the core build. These are optional Stage 4 upgrades only, never required for a complete submission.

---

## 3. Data Model

### Sensor reading (one row per timestamp per fixture)
```
timestamp: datetime
zone_id: string          # e.g. "Terminal2_Restroom_A"
fixture_id: string        # e.g. "Sink_03", "Toilet_01"
flow_rate_lpm: float       # liters per minute
occupancy: int             # 0 or 1 (is someone in the zone)
flush_count_cumulative: int
sensor_status: string      # "OK", "FAULT", "OFFLINE"
```

### Ticket (generated when anomaly detected)
```
ticket_id: string
timestamp_flagged: datetime
zone_id: string
fixture_id: string
anomaly_type: string       # "sustained_leak", "slow_drip", "hygiene_threshold", "sensor_fault"
severity_score: float      # 0-100
severity_label: string     # Low / Medium / High / Critical
explanation: string        # LLM-generated plain-English reason
estimated_water_loss_liters: float
estimated_cost_impact: float
status: string             # "open", "dispatched", "resolved"
```

---

## 4. Detection Logic (the core innovation — build this carefully)

Do NOT use a single fixed threshold. Use the following layered approach:

### 4a. Adaptive baseline (per fixture, per hour-of-day)
- Maintain rolling mean + standard deviation of flow_rate_lpm, computed separately for each hour-of-day bucket, per fixture.
- A reading is a "statistical outlier" if it's more than 2.5 standard deviations above that fixture's own baseline for that time of day.
- Rationale: a bathroom at 8am has different normal usage than at 2am — a fixed threshold can't capture this, but a per-fixture, per-hour baseline can.

### 4b. Multi-signal correlation (combine at least 3 signals)
Combine the statistical outlier flag with:
- **Occupancy mismatch**: high flow + occupancy = 0 → strong leak signal. High flow + occupancy = 1 → likely normal use, suppress or downgrade alert.
- **Duration**: outlier must persist for a minimum sustained window (e.g., >10 minutes) to avoid flagging brief normal spikes (e.g., a flush).
- **Sensor health**: if sensor_status = "FAULT" or "OFFLINE" during the anomaly window, flag it as a "possible sensor fault" ticket type instead of a leak ticket, and lower confidence accordingly.

### 4c. Rate-of-change / slow-drip detection
- Separately track cumulative water usage per fixture over a rolling 2-hour window during known unoccupied periods (e.g., overnight).
- If cumulative usage is climbing steadily (positive slope) when it should be flat (zero occupancy the whole window), flag as "slow_drip" — this catches leaks too small to cross the Section 4a threshold.

### 4d. Severity scoring (weighted composite, not binary)
```
severity_score = 
    (flow_deviation_normalized * 0.4) +
    (duration_factor * 0.3) +
    (occupancy_mismatch_flag * 0.2) +
    (sensor_health_penalty * 0.1)
```
- Normalize each component to a 0-1 scale before weighting.
- Bucket final score into: Low (0-25), Medium (26-50), High (51-75), Critical (76-100).
- Critical/High tickets should be flagged for immediate dispatch; Low/Medium can be batched into a daily digest.

### 4e. Water/cost impact estimation (for Business Impact criterion)
- `estimated_water_loss_liters = flow_rate_lpm * duration_minutes` (for the anomalous window)
- `estimated_cost_impact = estimated_water_loss_liters * local_water_cost_per_liter` (use a reasonable assumed rate, state your assumption clearly in the prompts doc)

### 4f. (Optional, Stage 4 only) ML upgrade
- Train a lightweight `sklearn.IsolationForest` on simulated "normal" multivariate data (flow, occupancy, hour-of-day) to catch combined anomalies the rules above might miss. Only attempt this after 4a-4e are working and you fully understand what the model is doing — you must be able to explain it in the interview.

---

## 5. LLM Layer (separate from detection — LLM explains, doesn't decide)

The LLM does NOT decide whether something is an anomaly — the rules/logic above do that deterministically so it's explainable and auditable. The LLM's job:
1. Given a flagged ticket's raw data (severity score, signals that triggered it), generate a 1-2 sentence plain-English explanation for the facility manager.
   - Example: "Flagged as Critical: Sink_03 in Terminal2_Restroom_A showed sustained flow 40 min above its normal 2am baseline with zero occupancy detected — consistent with an active leak."
2. Generate an end-of-day digest summarizing all Low/Medium tickets in natural language.
3. (Optional) Simple chat interface: "any leaks today?" → queries the ticket database and responds in natural language.

---

## 6. Build Phases (build in this order — each phase is a fully working, submittable checkpoint)

### Phase 1 (Days 1-3): Core loop, simplest working version
- [ ] Python simulator generating sensor readings for 3-5 fixtures across 2 zones, over a simulated 48-hour period, with 3-4 injected anomalies (mix of sustained leak, slow drip, one false-positive-prone scenario like a long normal shower)
- [ ] SQLite schema (Section 3) populated by the simulator
- [ ] Basic detection: implement 4a (adaptive baseline) only at this stage
- [ ] Streamlit dashboard: table/chart of readings + flagged tickets, auto-refresh every few seconds
- **Definition of done:** you can run the simulator, see readings populate, see at least one ticket get flagged and displayed.

### Phase 2 (Days 4-5): Strengthen the detection logic (this is where most of your "innovation" score comes from)
- [ ] Add 4b (multi-signal correlation: occupancy + duration + sensor health)
- [ ] Add 4c (slow-drip rate-of-change detection)
- [ ] Add 4d (severity scoring, replace binary flag with Low/Medium/High/Critical)
- [ ] Add 4e (water/cost impact estimation)
- **Definition of done:** your false-positive scenario (long normal shower) is correctly NOT flagged (or flagged low severity), while your slow-drip scenario IS caught.

### Phase 3 (Day 6): LLM layer + dashboard polish
- [ ] Add LLM explanation generation for each ticket (Section 5.1)
- [ ] Add end-of-day digest (Section 5.2)
- [ ] Polish dashboard: severity color-coding, ticket list sorted by priority, simple charts of flow over time per zone
- **Definition of done:** dashboard tells a clear story a judge can follow in under a minute.

### Phase 4 (Day 7, optional upgrades only — do NOT start these unless Phases 1-3 are solid and working):
- [ ] Swap SQLite → TimescaleDB/InfluxDB if time allows
- [ ] Swap polling → WebSocket real-time push
- [ ] Add IsolationForest ML layer (Section 4f)
- [ ] Simple chat interface for querying tickets in natural language

### Day 8: Submission prep
- [ ] Record 1-3 min demo video walking through: simulator running → anomaly occurring → ticket flagged with severity + explanation → dashboard view
- [ ] Compile Prompts Documentation PDF from your running prompts log
- [ ] Build 4-slide deck: (1) problem + approach, (2) architecture diagram, (3) detection logic explained, (4) tech stack + business impact
- [ ] Push everything to a single GitHub repo with README + run instructions

---

## 7. Instructions for Antigravity (how to use this doc)

When starting each phase, paste the relevant Phase section (Section 6) along with the corresponding detail sections (3, 4, 5) into the agent panel. Use **Planning Mode**, not Fast mode, so the agent proposes an implementation plan before writing code — review and adjust that plan in plain language before approving execution. Do not move to the next phase until the current phase's "Definition of done" is met and you can personally explain how the detection logic works without looking at the code.

Keep a running log of every prompt given to Antigravity in a separate file (`prompts_log.md`) — this becomes the basis for the required Prompts Documentation PDF.
