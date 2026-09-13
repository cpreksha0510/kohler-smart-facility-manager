# KOHLER Smart Facility Manager — Phase 1

> **Scenario:** Terminal 2 Restroom Block, International Airport  
> **Stack:** Python · SQLite · Streamlit · Pandas · NumPy · Plotly

---

## What This Does

Simulates 48 hours of water-sensor data from a commercial airport restroom block (2 zones, 5 fixtures), detects abnormal water usage using an adaptive per-fixture baseline (no fixed thresholds), and displays flagged anomalies on a live Streamlit dashboard.

This is **Phase 1 of 3**. Detection logic in this phase uses only the statistical baseline (Section 4a of the PRD). Phases 2 and 3 add multi-signal correlation, severity scoring, and an LLM explanation layer.

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate 48h of sensor data (writes facility.db at project root)
python src/simulator.py

# 3. Run anomaly detection (writes tickets to facility.db)
python src/detector.py

# 4. Launch dashboard
streamlit run src/dashboard.py
```

---

## Project Structure

```
├── facility_manager_prd.md   ← Full spec
├── prompts_log.md            ← Running prompts log (submission artifact)
├── README.md                 ← This file
├── requirements.txt
├── facility.db               ← Created by simulator (not committed to git)
└── src/
    ├── config.py             ← All constants: zones, fixtures, anomaly windows, thresholds
    ├── database.py           ← SQLite schema + query helpers
    ├── simulator.py          ← 48h batch data generator + anomaly injection
    ├── detector.py           ← Section 4a: adaptive baseline detection
    └── dashboard.py          ← Streamlit UI (Full Dataset + Replay Demo modes)
```

---

## Injected Anomalies

| # | Fixture | Type | Window | Expected Phase 1 Result |
|---|---|---|---|---|
| 1 | `Sink_01` / `T2_Restroom_A` | Sustained leak | Day 2, 02:00–06:00 (zero occ.) | **CAUGHT** — 3.5 LPM vs ~0 LPM baseline |
| 2 | `Toilet_02` / `T2_Restroom_B` | Slow drip | Day 2, 00:00–08:00 (zero occ.) | **NOT caught** (by design) — 0.25 LPM too small for 4a; Phase 2 catches it |
| 3 | `Sink_02` / `T2_Restroom_A` | False positive | Day 1, 08:15–08:28 (occupancy=1) | May be flagged — Phase 2 multi-signal will suppress |

---

## Dashboard Modes

- **Full Dataset** — Shows all 48h of data and all detected tickets. Auto-refreshes every 5 seconds.
- **Replay Demo** — Steps through the pre-generated data on a simulated timer. Use this for the demo video.

---

## Detection Logic (Phase 1 — Section 4a)

For each `(fixture_id, hour_of_day)` pair, the system maintains an expanding history of `flow_rate_lpm` values. A reading is flagged as an outlier if:

```
flow_rate_lpm > mean(prior_history) + 2.5 × std(prior_history)
```

Consecutive outlier readings (gap ≤ 2 minutes) are grouped into a single session/ticket.

**Why expanding window, not rolling?** With only 48h of data, each hour-of-day slot has at most ~60 prior readings. An expanding window builds history as it progresses — this avoids using future data to compute past thresholds (a real-world deployment would use weeks of history).

---

## Water Cost Assumption

`₹0.05 per liter` — based on Indian municipal commercial tariff schedules (mid-range estimate across BWSSB/MCGM rates for commercial facilities). Stored in `src/config.py` as a named constant. Not used in Phase 1 calculations; wired in for Phase 2.

---

## Phase Roadmap

| Phase | Scope | Status |
|---|---|---|
| Phase 1 | Simulator + SQLite + 4a detection + Streamlit dashboard | ✅ This build |
| Phase 2 | 4b multi-signal + 4c slow-drip + 4d severity scoring + 4e cost impact | ⏳ Next |
| Phase 3 | LLM explanation layer + dashboard polish + end-of-day digest | ⏳ |
| Phase 4 | Optional: TimescaleDB, WebSocket, IsolationForest, chat interface | ⏳ |
