# KOHLER Smart Facility — Feature Implementation Plan
## Track 2 | Execution Specification

This document specifies the five additions selected for the existing KOHLER Smart Facility & Sustainability Manager:

1. Predictive Fixture Health
2. Water-Savings / Sustainability Impact
3. AI Facility Copilot — Operational Actions
4. Explainable Anomaly Detection ("Why was this flagged?")
5. Detection Performance / Ground-Truth Evaluation

The goal is to extend the existing architecture, not replace it.

---

# 0. Existing System — DO NOT BREAK

The current system already contains:

- 48-hour simulated fixture telemetry
- SQLite database
- Adaptive baseline anomaly detection
- Multi-pass session grouping/coalescing
- Multi-signal severity scoring
- Slow-drip cumulative detection
- Water-loss and cost estimation
- Ticket lifecycle: Open → Dispatched → Resolved
- Resolution notes
- Daily operational digest
- Next.js dashboard
- Telemetry charts
- Occupancy heatmap
- Replay scrubber
- Gemini-grounded AI Copilot
- Deterministic fallback when Gemini is unavailable

Important architectural rule:

> Extend the existing detection and ticket systems. Do not rewrite working systems.

The anomaly detector remains deterministic and authoritative. The LLM should explain data and recommend actions; it should NOT become the anomaly classifier.

---

# 1. FEATURE: PREDICTIVE FIXTURE HEALTH

## 1.1 Goal

Move the platform from:

    "Something is wrong now."

to:

    "This fixture is showing degradation and may require preventive attention."

This is NOT a claim that the system can accurately predict real-world mechanical failure from the current simulated dataset. For the MVP, implement a transparent risk/health model based on historical behavior.

## 1.2 User Experience

Add a "Fixture Health" section/page.

Each fixture should have:

- Health Score: 0–100
- Failure Risk: 0–100
- Health status
- Trend
- Number of historical anomalies
- Recent anomaly types
- Last incident
- Last resolution
- Recommended action

Example:

    Sink_07

    Health
    ████████░░ 82/100

    Failure Risk: 18%
    Trend: Deteriorating

    Incidents: 3
    Recent: sustained_leak, slow_drip
    Last incident: 2 days ago

    Recommendation:
    "Inspect valve/seal during next maintenance round."

## 1.3 Suggested Calculation

Do NOT use an opaque ML model initially.

Calculate a transparent risk score:

    risk =
        anomaly_frequency_score * 0.30
      + recurrence_score         * 0.20
      + flow_drift_score         * 0.20
      + slow_drip_score          * 0.15
      + sensor_health_score      * 0.10
      + unresolved_score         * 0.05

Normalize every component to 0–100.

Then:

    health_score = 100 - risk

Suggested interpretation:

    80–100 → Healthy
    60–79  → Watch
    40–59  → Degrading
    0–39   → High Risk

These labels are product states, not medical/physical certainty.

## 1.4 Trend

Calculate a simple trend by comparing recent behavior with older behavior.

Example:

    recent anomaly rate > previous anomaly rate
        → Deteriorating

    recent anomaly rate ≈ previous anomaly rate
        → Stable

    recent anomaly rate < previous anomaly rate
        → Improving

Also calculate flow drift where possible.

## 1.5 Database

Add a fixture-health table rather than bloating tickets.

Suggested schema:

    fixture_health
    -----------------------------
    fixture_id
    health_score
    risk_score
    trend
    anomaly_count
    slow_drip_count
    sensor_fault_count
    last_incident_at
    calculated_at
    recommendation

The health record can be recalculated whenever detection runs.

## 1.6 API

Add:

    GET /api/fixture-health

Optional:

    GET /api/fixture-health/{fixture_id}

Response example:

    {
      "fixture_id": "Sink_07",
      "health_score": 82,
      "risk_score": 18,
      "trend": "deteriorating",
      "anomaly_count": 3,
      "slow_drip_count": 1,
      "sensor_fault_count": 0,
      "recommendation": "Inspect valve/seal during next maintenance round."
    }

## 1.7 UI

Add:

- Fixture Health KPI
- Health table/grid
- Sort by risk
- Filter by zone
- Fixture detail drawer/modal
- Health trend indicator

Do not create a giant ML dashboard.

---

# 2. FEATURE: WATER-SAVINGS / SUSTAINABILITY IMPACT

## 2.1 Goal

The existing system already estimates water loss and cost.

Extend this into:

    "How much waste did the system prevent?"

and:

    "What would happen if this incident remained unresolved?"

This turns telemetry into measurable sustainability impact.

## 2.2 Incident Projection

For every active incident, calculate projected loss.

Current loss:

    observed_flow_lpm * elapsed_minutes

Projected:

    projected_loss =
        observed_flow_lpm * projection_duration_minutes

Useful horizons:

- 1 hour
- 6 hours
- 24 hours
- 7 days

Example:

    Current loss: 136 L

    If unresolved:
      +1 hour  → 210 L
      +6 hours → 1,260 L
      +24 hrs  → 5,040 L

## 2.3 Prevented Waste

When a ticket is resolved:

    potential_loss_without_intervention
      -
    actual_loss_before_resolution
      =
    estimated_water_saved

For a demo, clearly label this as:

    "Estimated water saved"

because it is a simulation-based counterfactual.

## 2.4 Facility-Level Metrics

Add:

- Total water wasted
- Estimated water saved
- Cost impact
- Estimated avoided cost
- Projected unresolved waste
- Highest-waste fixture
- Highest-waste zone

Example:

    SUSTAINABILITY IMPACT

    Water waste       1,420 L
    Water saved       6,280 L
    Cost impact       ₹710
    Avoided cost      ₹3,140

## 2.5 Database

Add an optional sustainability/impact table:

    sustainability_events
    -----------------------------
    ticket_id
    actual_loss_liters
    projected_loss_liters
    estimated_saved_liters
    cost_impact
    avoided_cost
    calculated_at

Or calculate these dynamically from tickets if the current schema already contains sufficient fields.

Prefer the simpler approach if possible.

## 2.6 API

Suggested:

    GET /api/sustainability/summary

Response:

    {
      "water_waste_liters": 1420,
      "water_saved_liters": 6280,
      "cost_impact": 710,
      "avoided_cost": 3140,
      "projected_unresolved_loss_liters": 9200
    }

## 2.7 UI

Add a Sustainability panel.

Include:

- water waste
- water saved
- money impact
- projected waste
- top water-wasting fixtures
- top zones

Also add an "Intervention Impact" section to resolved tickets.

Example:

    Incident resolved after 18 minutes

    Water lost:       63 L
    Estimated avoided: 73 L
    Estimated saving: ₹3.65

---

# 3. FEATURE: AI COPILOT — OPERATIONAL ACTIONS

## 3.1 Current State

The current Copilot already receives context such as:

- open tickets
- high-severity alerts
- cumulative water loss
- worst offenders

Keep this architecture.

The improvement is to make Copilot operational rather than purely conversational.

## 3.2 New Questions

Support questions such as:

    "What should I deal with first?"

    "Which fixture needs immediate attention?"

    "Why is this ticket critical?"

    "What maintenance should happen today?"

    "Which zone is wasting the most water?"

    "Which fixtures are deteriorating?"

## 3.3 Structured Response

Instead of returning only prose, make the backend request a structured response.

Suggested:

    {
      "summary": "...",
      "priority_actions": [
        {
          "ticket_id": "TKT-001",
          "priority": 1,
          "reason": "...",
          "recommended_action": "Dispatch plumbing team"
        }
      ]
    }

The frontend can render action cards.

## 3.4 Quick Actions

Add buttons:

    [View Ticket]
    [View Telemetry]
    [View Fixture]
    [Dispatch]
    [Schedule Inspection]

For the MVP, these can navigate to existing UI states.

Avoid letting the LLM directly mutate database state.

If you implement an actual action, route it through an explicit backend API and validate the ticket ID/action.

## 3.5 Grounding Rules

The Copilot must only use verified system data.

The prompt should include:

- current open tickets
- fixture health
- water impact
- anomaly details
- timestamps
- occupancy
- severity

Instruction:

    "Do not invent telemetry values.
     If information is unavailable, say so.
     Base recommendations on supplied system context."

## 3.6 Example

User:

    "What should I deal with first?"

Copilot:

    PRIORITY ACTIONS

    1. Sink_07 — Critical
       Continuous 3.5 L/min flow during zero occupancy.
       Estimated current waste: 136 L.

       Recommended:
       Inspect/repair plumbing immediately.

    2. Toilet_B3 — High
       Repeated valve anomalies.

       Recommended:
       Schedule inspection within the next maintenance round.

Each item can have:

    [Open Ticket]

---

# 4. FEATURE: EXPLAINABLE ANOMALY DETECTION

## 4.1 Goal

Make the detection engine explain:

    "Why did the system flag this?"

This is especially important because the existing detector uses multiple signals.

Do NOT replace the current severity calculation.

Expose its evidence.

## 4.2 Evidence to Show

For each ticket show:

- Expected flow
- Observed flow
- Flow deviation
- Duration
- Occupancy
- Occupancy mismatch
- Baseline
- Severity score
- Severity label
- Anomaly type
- Sensor health
- Estimated water loss

## 4.3 Evidence Breakdown

Example:

    WHY WAS THIS FLAGGED?

    Flow deviation       92%
    Duration             81%
    Occupancy mismatch  100%
    Sensor health        90%

    Expected flow:       0.00 L/min
    Observed flow:       3.50 L/min
    Duration:            39 min
    Occupancy:           0%

    Detection confidence: 96%

Important:
The "confidence" should only be shown if you define how it is calculated. Do not fabricate statistical confidence.

A safer MVP label is:

    Evidence Strength: Strong

calculated from the existing detection signals.

## 4.4 Evidence Strength

Create a transparent evidence score based on the detector's existing components.

Example:

    evidence_strength =
        normalized_flow_deviation * 0.30
      + normalized_duration        * 0.25
      + occupancy_mismatch          * 0.25
      + sensor_health               * 0.20

Then map:

    80–100 → Strong
    60–79  → Moderate
    <60    → Weak

Do not call this statistical confidence.

## 4.5 Database

Prefer adding fields to tickets only if necessary.

Possible:

    evidence_summary
    evidence_strength

But ideally derive the evidence breakdown from existing ticket/readings data so there is no duplicated source of truth.

## 4.6 UI

On ticket detail:

    WHY THIS ALERT?

    ┌─────────────────────────────┐
    │ Sustained Leak              │
    │                             │
    │ Observed  3.50 L/min        │
    │ Expected  0.00 L/min        │
    │ Duration  39 min             │
    │ Occupancy 0%                 │
    │                             │
    │ Evidence: STRONG             │
    └─────────────────────────────┘

Then:

    "Continuous flow while the fixture
     remained unoccupied is inconsistent
     with normal usage."

The explanation can be generated by the existing Gemini layer, but all numeric facts must come from telemetry.

---

# 5. FEATURE: DETECTION PERFORMANCE / GROUND-TRUTH EVALUATION

## 5.1 Goal

Prove that the detector works.

The simulator already knows which anomalies were intentionally injected.

Use this ground truth to calculate:

- True Positive
- False Positive
- False Negative
- Precision
- Recall
- F1

This is one of the most technically valuable additions because it lets you defend the system with numbers.

## 5.2 Ground Truth

The simulator should maintain or expose:

    anomaly_id
    fixture_id
    anomaly_type
    start_time
    end_time

Examples:

    sustained_leak
    slow_drip
    sensor_fault
    hygiene_threshold

Do not infer ground truth from the detector's own output.

The simulator is the source of truth.

## 5.3 Matching Logic

A detected ticket should match a ground-truth event when:

1. Fixture IDs match
2. Anomaly types are compatible
3. Time intervals overlap sufficiently

Example:

    Ground truth:
    Sink_07
    02:00–02:39
    sustained_leak

    Detection:
    Sink_07
    02:01–02:40
    sustained_leak

    → MATCH / TRUE POSITIVE

Set a documented overlap rule, e.g.:

    overlap_ratio >= 0.5

Keep the rule consistent.

## 5.4 Metrics

For each anomaly class:

    precision = TP / (TP + FP)

    recall = TP / (TP + FN)

    F1 = 2 * precision * recall / (precision + recall)

Also calculate overall metrics.

Example UI:

    DETECTION PERFORMANCE

    Overall
    Precision    92%
    Recall       96%
    F1 Score     94%

    Sustained Leak
    Precision    91%
    Recall       94%

    Slow Drip
    Precision    95%
    Recall       100%

These numbers must be calculated from the actual simulation dataset.

Never hard-code them.

## 5.5 False Positive Analysis

Add a section:

    FALSE POSITIVES

    Sink_04 — 07:42
    High flow during rush hour

    Why detector rejected/flagged:
    ...

If the system suppresses the event correctly, show:

    SUPPRESSED NORMAL EVENT

    High flow
    High occupancy
    Normal duration

    Result:
    No ticket created

This is particularly valuable because false-positive suppression is a core part of the existing problem.

## 5.6 API

Suggested:

    GET /api/evaluation

Response:

    {
      "overall": {
        "true_positive": 23,
        "false_positive": 2,
        "false_negative": 1,
        "precision": 0.92,
        "recall": 0.96,
        "f1": 0.94
      },
      "by_type": {
        "sustained_leak": {...},
        "slow_drip": {...},
        "sensor_fault": {...}
      }
    }

## 5.7 UI

Create a small "Model Evaluation" section.

It does not need to be part of the main operator dashboard.

Possible locations:

- Analytics
- System Insights
- Evaluation
- Developer/Validation view

Keep it accessible for judges.

---

# 6. HOW THE FIVE FEATURES CONNECT

The final architecture should become:

                    SENSOR DATA
                         │
                         ▼
              EXISTING DETECTION ENGINE
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      ANOMALY        EXPLAINABILITY   GROUND TRUTH
      DETECTION        EVIDENCE       EVALUATION
          │              │              │
          ▼              ▼              ▼
       TICKET       "WHY FLAGGED?"   PRECISION/
          │                           RECALL/F1
          ▼
   FIXTURE HEALTH
          │
          ▼
   PREDICTIVE RISK
          │
          ├───────────────┐
          ▼               ▼
   COPILOT ACTIONS   SUSTAINABILITY
                         IMPACT
          │               │
          └───────┬───────┘
                  ▼
          OPERATIONAL DECISION

The important narrative is:

    Detect
      ↓
    Understand
      ↓
    Predict
      ↓
    Act
      ↓
    Measure impact

---

# 7. RECOMMENDED IMPLEMENTATION ORDER

Do not implement everything simultaneously.

## Phase 1 — Explainability

First expose existing detector evidence.

Why first:
- Uses data already available.
- Low risk.
- Helps debug later features.

Deliver:
- evidence breakdown
- evidence strength
- ticket explanation panel

---

## Phase 2 — Sustainability Impact

Use existing water-loss fields.

Deliver:
- current waste
- projected waste
- estimated saved water
- avoided cost
- sustainability dashboard

---

## Phase 3 — Fixture Health

Build the transparent risk model.

Deliver:
- health score
- risk score
- trend
- recommendation
- fixture health page

---

## Phase 4 — Copilot Actions

Feed fixture health + sustainability + ticket evidence into Copilot.

Deliver:
- priority recommendations
- action cards
- links to relevant ticket/fixture views

Keep mutations outside the LLM.

---

## Phase 5 — Evaluation

Use simulator ground truth.

Deliver:
- TP/FP/FN
- precision
- recall
- F1
- per-anomaly metrics
- false-positive examples

---

# 8. DEMO FLOW

Use this as the final judging/demo storyline.

## Scene 1 — Normal Operations

Show high water usage during occupancy rush.

System does NOT create a false alert.

Explain:

    "High flow alone isn't enough.
     The detector contextualizes flow using
     occupancy and historical baseline."

## Scene 2 — Leak Appears

Replay reaches a zero-occupancy period.

A fixture continues flowing.

Ticket appears.

## Scene 3 — Explainability

Open the ticket.

Show:

    Expected: 0 L/min
    Actual: 3.5 L/min
    Occupancy: 0%
    Duration: 39 min

Then:

    Evidence: Strong

## Scene 4 — Sustainability

Show:

    Water already wasted: 136 L

    If unresolved:
      1 hour → ...
      6 hours → ...
      24 hours → ...

## Scene 5 — Fixture Health

Open fixture profile.

Show:

    Health: 61/100
    Risk: 39/100
    Trend: Deteriorating

Explain repeated incidents caused the score to fall.

## Scene 6 — Copilot

Ask:

    "What should I deal with first?"

Copilot identifies the incident and explains why.

## Scene 7 — Resolution

Resolve ticket.

Update:

    Estimated water saved
    Avoided cost

## Scene 8 — Evaluation

Show:

    Precision
    Recall
    F1

Finish with:

    "The system is not only detecting anomalies.
     It explains them, identifies deteriorating fixtures,
     quantifies sustainability impact, and provides
     evidence that the detection pipeline works."

---

# 9. ENGINEERING RULES

1. Do not rewrite the detector.
2. Do not move anomaly classification into Gemini.
3. Do not hard-code evaluation metrics.
4. Do not fabricate confidence values.
5. Do not call projected water savings actual savings.
6. Clearly label simulation-derived metrics.
7. Reuse existing database fields wherever possible.
8. Keep business logic outside React components.
9. Keep API calculations on the backend.
10. Keep Copilot grounded in database data.
11. Prefer deterministic calculations over LLM-generated numbers.
12. Keep existing fallback behavior.
13. Do not introduce a paid infrastructure dependency.
14. Preserve the current replay functionality.
15. Test each feature independently before integrating.

---

# 10. DEFINITION OF DONE

## Predictive Fixture Health

- [ ] Health score calculated for every fixture
- [ ] Risk score calculated
- [ ] Trend calculated
- [ ] Fixture health API works
- [ ] Health UI works
- [ ] Zone filtering works
- [ ] Recommendation displayed

## Sustainability

- [ ] Current water loss displayed
- [ ] Projected unresolved loss calculated
- [ ] Estimated water saved calculated
- [ ] Avoided cost calculated
- [ ] Facility summary displayed
- [ ] Resolved ticket shows intervention impact

## AI Copilot

- [ ] Receives ticket context
- [ ] Receives fixture-health context
- [ ] Receives sustainability context
- [ ] Can identify priorities
- [ ] Returns structured action recommendations
- [ ] Does not invent values
- [ ] Existing fallback still works

## Explainability

- [ ] Ticket evidence visible
- [ ] Expected vs observed flow visible
- [ ] Duration visible
- [ ] Occupancy visible
- [ ] Severity evidence visible
- [ ] Evidence strength calculated
- [ ] Explanation grounded in telemetry

## Evaluation

- [ ] Simulator exposes ground truth
- [ ] Detection/ground-truth matching implemented
- [ ] TP/FP/FN calculated
- [ ] Precision calculated
- [ ] Recall calculated
- [ ] F1 calculated
- [ ] Per-anomaly metrics available
- [ ] Metrics are generated dynamically
- [ ] At least one false-positive/suppression example is demonstrable

---

# 11. FINAL PRODUCT POSITIONING

Do not describe the project as:

    "A dashboard that monitors restroom sensors."

Describe it as:

    "An intelligent facility operations platform that
     detects abnormal water usage, explains the evidence,
     identifies fixtures showing degradation, quantifies
     sustainability impact, and gives operators
     context-aware actions."

The five additions should make the product feel like a closed-loop system:

    MONITOR
       ↓
    DETECT
       ↓
    EXPLAIN
       ↓
    PREDICT
       ↓
    ACT
       ↓
    MEASURE

That is the core implementation target.
