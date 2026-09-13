# Prompts Log — KOHLER Smart Facility Manager

> Running log of every prompt given to Antigravity during this project build.
> Required submission artifact → will become the Prompts Documentation PDF.

---

## Phase 1 — Core Loop (Days 1–3)

### Prompt 1 — Project Kickoff & Clarification
**Date:** 2024-01-15  
**Prompt given:**
> Read this spec fully. I want to build this in phases, exactly as laid out in Section 6. Do not skip ahead to later phases. Confirm you understand Phase 1's scope and "Definition of done" before writing any code. Ask me any clarifying questions first.

**Decisions made from response:**
- Scenario: Airport restroom block (Terminal 2)
- Simulation: Batch-first (all 48h at once), then replay mode in dashboard for demo video
- LLM key: Deferred to Phase 3 — `explanation` field left blank in Phase 1
- Folder structure: `src/` for code, root-level for docs
- Water cost: ₹0.05/liter (Indian municipal commercial rate, mid-range estimate) — stored as a named constant with source comment; not used until Phase 2

---

### Prompt 2 — Phase 1 Build
**Date:** 2024-01-15  
**Prompt given:**
> Build Phase 1 only (Section 6, Phase 1). Follow the data model in Section 3 exactly.
> [Full anomaly spec, detection scope, and dashboard requirements]

**What was built:**
- `src/simulator.py` — 48h batch generator, 5 fixtures, 2 zones, 3 anomalies injected
- `src/database.py` — SQLite schema helpers matching Section 3 exactly
- `src/detector.py` — Section 4a adaptive baseline detection (expanding window per fixture/hour-of-day)
- `src/dashboard.py` — Streamlit dashboard with Full Dataset and Replay Demo modes

**Key design choices made (and why):**
1. Expanding window baseline (not a true rolling window): with only 48h of data, each hour-of-day slot has at most ~60 prior readings. An expanding window builds history as it goes — this is the honest approach rather than using future data to compute past thresholds.
2. STD_FLOOR = 0.2: at overnight hours, virtually all readings are zero-flow (no one is using the sink). This makes std ≈ 0, which would make the threshold 0 and flag any tiny drip. A floor of 0.2 ensures the threshold is 0.5 LPM minimum — enough to catch a 3.5 LPM sustained leak but not the 0.25 LPM slow drip (which is intentionally left for Phase 2's 4c detector).
3. Session grouping (consecutive outliers → 1 ticket): flagging every individual minute as a separate ticket would create noise. Grouping consecutive outlier readings (gap ≤ 2 min = same session) into one ticket is cleaner and more actionable.

**Known Phase 1 limitations (by design):**
- Slow drip (0.25 LPM) NOT caught — needs Phase 2's rate-of-change detector (4c)
- False positive (long handwash, occupancy=1) MAY be flagged — Phase 2's multi-signal correlation (4b) will suppress it
- All tickets labelled "sustained_leak" — Phase 2 will differentiate anomaly types
- No severity scoring — Phase 2 adds the weighted composite scorer (4d)
- `explanation` field is blank — Phase 3 LLM will fill this

---

### Prompt 3 — Dashboard UI Redesign (Control Room Aesthetic)
**Date:** 2024-01-15  
**Prompt given:**
> I want to redesign the dashboard UI. Don't use emojis anywhere — replace them with a consistent outline icon set (pick one, e.g. Phosphor or Feather icons, and use it everywhere, not mixed styles). Icons should only appear where they add real meaning (severity level, sensor status, zone type), not decoratively.
> 
> Use this color system instead of default Streamlit/generic AI colors:
> - Background: #12161A (deep graphite)
> - Card/surface: #1B2127
> - Primary accent (water): #3FA9A0 — use for primary actions, active states, water-related charts
> - Secondary accent (brass): #B98D4F — use sparingly, only for highlights, not backgrounds
> - Text primary: #E7ECEE, muted text: #8A97A0
> - Severity colors (keep these visually distinct from the brand accents above):
>   Critical #E4572E, High #F0A202, Medium #D9B44A, Low #5B6770
> 
> Typography: use a serif font for headers/titles (e.g. Fraunces or Newsreader) paired with a clean sans-serif for data, labels, and body text (e.g. IBM Plex Sans or Inter). Don't use all-caps for labels — use sentence case or small caps.
> 
> Layout & component hierarchy: Pick ONE element to be visually bold and keep everything else quiet and secondary. Give the dashboard a specific layout structure. Don't vary border-radius component to component. Replace default Streamlit component aesthetics.

**What was built:**
- `.streamlit/config.toml` — Theme configuration mapping primaryColor, backgroundColor, secondaryBackgroundColor, textColor to the specified hex palette.
- `src/icons.py` — Self-contained Phosphor outline SVG dictionary (pulse, drop, list, grid, alert-triangle, alert-circle, minus-circle, circle, clock) avoiding CDN fragility.
- `src/dashboard.py` — Complete UI overhaul:
  - Two-layer styling architecture: `.streamlit/config.toml` handles slider thumbs, radio selected states, and native inputs; scoped CSS injection handles custom components, typography, and layout.
  - Typography pairing: Fraunces serif for headings paired with IBM Plex Sans for body, labels, and metric numbers; IBM Plex Mono for IDs/timestamps. Sentence case used throughout.
  - Zero decorative emojis; Phosphor outline SVGs used only for semantic status indicators and metric labels.
  - Custom HTML metric cards replacing standard `st.metric()` for consistent 1px border and typography.
  - Custom HTML tickets table with 3px left-border severity stripes (`#E4572E`, `#F0A202`, `#D9B44A`, `#5B6770`) acting as the "one bold element".
  - Plotly flow chart styled with transparent background, muted gridlines, and cool water palette anchored on `#3FA9A0`.
  - Replay mode with custom monospace simulation clock and styled progress bar.

---

*(Add Phase 2 entries here when Phase 2 begins)*
