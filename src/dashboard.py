"""
dashboard.py — KOHLER Smart Facility Manager, redesigned.

Design system:
  Background     #12161A   deep graphite
  Surface        #1B2127   cards, table rows, sidebar
  Surface-2      #222830   table header, hover state
  Primary UI     #6B8CAE   muted slate-blue: active states, charts, buttons
  Secondary      #B08D57   muted warm brass: flagged tickets attention
  Text primary   #E7ECEE
  Text muted     #8A97A0
  Severity       Critical #E4572E / High #F0A202 / Medium #D9B44A / Low #5B6770

Typography:
  Headers/titles Fraunces (variable-weight serif)
  Data/body      IBM Plex Sans
  IDs/mono       IBM Plex Mono

Icons: src/icons.py — outline SVG set, used only where semantically meaningful.
No emojis anywhere.

Theming strategy:
  config.toml  controls: slider thumb, radio selected state, progress bar fill.
  CSS injection controls: everything else. See _CSS below.
"""

import datetime
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    DB_PATH, SIM_START, SIM_DURATION_HOURS,
    DASHBOARD_REFRESH_SECONDS, REPLAY_REFRESH_SECONDS,
)
from src.database import get_readings_df, get_tickets_df
from src.icons import icon

# ── Streamlit page config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="KOHLER Facility Monitor",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design constants ──────────────────────────────────────────────────────────

# Zone colors: one distinct muted color per zone.
# Chosen for clear differentiation while staying within the dark control-room
# palette — no primaries or neons, all desaturated to ~40–55% lightness.
ZONE_COLORS: dict[str, str] = {
    "T2_Restroom_A":  "#6B8CAE",   # muted slate blue   — departure restroom (busiest)
    "T2_Restroom_B":  "#789A8B",   # muted sage green   — arrival restroom
    "T2_Family_Room": "#B08D57",   # muted warm brass   — family/accessible room
    "T2_Staff_WC":    "#847E9C",   # muted dusty violet — staff WC (lowest traffic)
}

# Fixture type → Plotly dash style.
# Viewers can pattern-match on two visual dimensions (color + style):
#   solid = sink, dash = toilet, dot = urinal
TYPE_DASH: dict[str, str] = {
    "sink":   "solid",
    "toilet": "dash",
    "urinal": "dot",
}

# Legacy: kept for any code that still references FIXTURE_COLORS
FIXTURE_COLORS: dict[str, str] = ZONE_COLORS

# Severity → icon name
SEV_ICON: dict[str, str] = {
    "Critical": "alert-triangle",
    "High":     "alert-circle",
    "Medium":   "minus-circle",
    "Low":      "circle",
    "Flagged":  "circle",
}

# Severity → CSS custom property
SEV_COLOR: dict[str, str] = {
    "Critical": "var(--sev-critical)",
    "High":     "var(--sev-high)",
    "Medium":   "var(--sev-medium)",
    "Low":      "var(--sev-low)",
    "Flagged":  "var(--text-muted)",
}

# Severity → stripe CSS class
SEV_STRIPE: dict[str, str] = {
    "Critical": "stripe-critical",
    "High":     "stripe-high",
    "Medium":   "stripe-medium",
    "Low":      "stripe-low",
    "Flagged":  "stripe-flagged",
}

MAX_TICKETS_SHOWN = 100   # cap table rows to avoid DOM overload

# ── CSS bundle ────────────────────────────────────────────────────────────────
# One comprehensive style block injected once on every render.
# Uses CSS custom properties at :root so all component styles reference tokens,
# not hardcoded values.
#
# Components that resist external CSS and how they're handled:
#   st.dataframe()   → replaced with custom HTML <table>
#   st.metric()      → replaced with custom HTML metric cards
#   st.plotly_chart  → styled via fig.update_layout() only
#   st.progress()    → replaced with custom HTML progress bar
#   slider/radio     → base color from config.toml (primaryColor)
#   everything else  → CSS selectors below

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300&family=IBM+Plex+Mono:wght@400&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

/* ── Design tokens ── */
:root {
  --bg:             #12161A;
  --surface:        #1B2127;
  --surface-2:      #222830;
  --accent-primary: #6B8CAE;   /* muted slate-blue: primary UI actions & charts */
  --accent-water:   #6B8CAE;   /* alias for backward compatibility */
  --accent-brass:   #B08D57;   /* muted warm brass: attention indicator */
  --text-primary:   #E7ECEE;
  --text-muted:     #8A97A0;
  --border:         rgba(255,255,255,0.07);
  --border-strong:  rgba(255,255,255,0.18);
  --sev-critical:   #E4572E;
  --sev-high:       #F0A202;
  --sev-medium:     #D9B44A;
  --sev-low:        #5B6770;
  --r:              2px;
}

/* ── Base ── */
html, body, .stApp {
  background: var(--bg) !important;
  color: var(--text-primary) !important;
}
.block-container {
  padding: 1.75rem 2.25rem 3rem !important;
  max-width: none !important;
}
*, *::before, *::after {
  font-family: 'IBM Plex Sans', sans-serif;
  box-sizing: border-box;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.83rem !important;
  color: var(--text-muted) !important;
}

/* ── Dividers ── */
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 0.6rem 0 !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
  background: transparent !important;
  color: var(--text-muted) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 400 !important;
  padding: 0.35rem 1rem !important;
  box-shadow: none !important;
  transition: border-color 0.15s ease, color 0.15s ease !important;
}
[data-testid="stButton"] > button:hover,
[data-testid="stButton"] > button:focus {
  border-color: var(--accent-primary) !important;
  color: var(--accent-primary) !important;
  background: transparent !important;
  box-shadow: none !important;
}

/* ── Radio ── */
[data-testid="stRadio"] label p,
[data-testid="stRadio"] label span,
[data-testid="stRadio"] div[role="radiogroup"] label {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.83rem !important;
  color: var(--text-muted) !important;
}

/* ── Multiselect ── */
[data-testid="stMultiSelect"] input {
  font-family: 'IBM Plex Sans', sans-serif !important;
  color: var(--text-primary) !important;
}
[data-baseweb="tag"] {
  background: var(--surface-2) !important;
  border-radius: var(--r) !important;
}
[data-baseweb="tag"] span {
  color: var(--text-muted) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.78rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.82rem !important;
  color: var(--text-muted) !important;
  padding: 0.55rem 0.75rem !important;
}
[data-testid="stExpander"] summary:hover {
  color: var(--text-primary) !important;
}

/* ── Slider labels ── */
[data-testid="stSlider"] label,
[data-testid="stSlider"] p,
[data-testid="stSelectSlider"] label,
[data-testid="stSelectSlider"] p {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.8rem !important;
  color: var(--text-muted) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
  background: var(--surface) !important;
  border-radius: var(--r) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.83rem !important;
  color: var(--text-muted) !important;
}

/* ── Caption ── */
[data-testid="stCaptionContainer"] p {
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 0.75rem !important;
  color: var(--text-muted) !important;
}

/* ── Page header ── */
.page-header {
  overflow: visible !important;
  padding-top: 0.75rem;
  padding-bottom: 1.25rem;
  margin-bottom: 1.35rem;
  border-bottom: 1px solid var(--border);
}
[data-testid="stMarkdownContainer"]:has(.page-header) {
  overflow: visible !important;
}
.brand-title {
  display: block;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1.4;
  padding-top: 4px;
  color: var(--text-primary);
  text-transform: uppercase;
  margin: 0 0 0.25rem;
  overflow: visible !important;
}
.brand-subtitle {
  display: block;
  font-family: 'Fraunces', serif;
  font-size: 1.15rem;
  font-weight: 300;
  letter-spacing: -0.01em;
  line-height: 1.4;
  color: var(--text-muted);
  margin: 0 0 0.55rem;
  overflow: visible !important;
}
.page-header .sub {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--text-muted);
}
.page-header .sys-time {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--accent-primary);
}

/* ── Section label ── */
.section-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.71rem;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.45rem;
  margin-bottom: 0.75rem;
}

/* ── Metric cards ── */
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 0.9rem 1.2rem 0.85rem;
}
/* Neutral metrics (sensor readings, zones monitored) */
.metric-card.metric-neutral {
  border-left: 1px solid var(--border);
}
.metric-card.metric-neutral .metric-icon {
  color: #6B7C8C;
  opacity: 0.85;
}

/* Attention metric (flagged tickets) */
.metric-card.metric-attention {
  border-left: 3px solid var(--accent-brass);
}
.metric-card.metric-attention .metric-icon {
  color: var(--accent-brass);
  opacity: 0.9;
}

/* Primary metric (water loss) */
.metric-card.metric-primary {
  border-left: 3px solid var(--accent-primary);
}
.metric-card.metric-primary .metric-icon {
  color: var(--accent-primary);
  opacity: 0.9;
}

.metric-icon {
  margin-bottom: 0.55rem;
  line-height: 1;
}
.metric-value {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  margin-bottom: 0.25rem;
  letter-spacing: -0.02em;
}
.metric-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.71rem;
  font-weight: 400;
  color: var(--text-muted);
  letter-spacing: 0.01em;
}

/* ── Custom progress bar ── */
.custom-progress {
  margin: 0.5rem 0 1rem;
}
.custom-progress-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
}
.custom-progress-track {
  background: var(--surface-2);
  border-radius: 1px;
  height: 3px;
  overflow: hidden;
}
.custom-progress-fill {
  background: var(--accent-primary);
  height: 3px;
  border-radius: 1px;
  transition: width 0.3s ease;
}

/* ── Ticket table ── */
.ticket-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--r);
  margin-bottom: 0.75rem;
}
.ticket-table {
  width: 100%;
  border-collapse: collapse;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.82rem;
}
.ticket-table thead tr {
  background: var(--surface-2);
}
.ticket-table thead th {
  font-weight: 500;
  color: var(--text-muted);
  font-size: 0.71rem;
  padding: 0.55rem 0.9rem;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
  letter-spacing: 0.015em;
}
.ticket-table thead th.th-stripe { width: 3px; padding: 0; }
.ticket-table thead th.th-num   { text-align: right; }

.ticket-table tbody tr {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.ticket-table tbody tr:last-child { border-bottom: none; }
.ticket-table tbody tr:hover { background: var(--surface-2); }

.ticket-table tbody td {
  color: var(--text-primary);
  padding: 0.5rem 0.9rem;
  vertical-align: middle;
  white-space: nowrap;
}
/* Severity stripe — the ONE bold visual element on the page */
.ticket-table tbody td.td-stripe { padding: 0; width: 3px; }
.stripe-critical { background: var(--sev-critical); }
.stripe-high     { background: var(--sev-high); }
.stripe-medium   { background: var(--sev-medium); }
.stripe-low      { background: var(--sev-low); }
.stripe-flagged  { background: rgba(138,151,160,0.35); }

.ticket-table tbody td.td-mono {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.73rem;
  color: var(--text-muted);
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ticket-table tbody td.td-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}
.ticket-table tbody td.td-muted { color: var(--text-muted); }

/* Severity cell with icon */
.sev-cell {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.79rem;
  font-weight: 500;
}
.sev-cell.sev-Critical { color: var(--sev-critical); }
.sev-cell.sev-High     { color: var(--sev-high); }
.sev-cell.sev-Medium   { color: var(--sev-medium); }
.sev-cell.sev-Low      { color: var(--sev-low); }
.sev-cell.sev-Flagged  { color: var(--text-muted); }

/* ── Replay clock ── */
.replay-clock {
  padding: 0.9rem 0 1rem;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}
.replay-clock-label {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.71rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  margin-bottom: 0.25rem;
}
.replay-clock-time {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.55rem;
  font-weight: 500;
  color: var(--accent-primary);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

/* ── Sidebar internals ── */
.sidebar-brand {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 0.2rem;
}
.sidebar-brand .brand-bold {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-primary);
  text-transform: uppercase;
}
.sidebar-heading {
  font-family: 'Fraunces', serif;
  font-size: 0.95rem;
  font-weight: 400;
  color: var(--accent-brass);
  letter-spacing: 0.01em;
  margin: 0;
}
.zone-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  margin-bottom: 0.4rem;
  color: var(--text-muted);
  font-family: 'IBM Plex Sans', sans-serif;
}
.zone-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent-primary);
  flex-shrink: 0;
}
.sidebar-sub {
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.76rem;
  color: var(--text-muted);
  margin-bottom: 0;
}

/* ── No-data state ── */
.no-data {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--text-muted);
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.85rem;
  border: 1px solid var(--border);
  border-radius: var(--r);
  background: var(--surface);
  line-height: 1.8;
}
.no-data code {
  background: var(--surface-2);
  padding: 0.15em 0.5em;
  border-radius: 2px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.82rem;
  color: var(--accent-primary);
}
</style>
"""


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=4)
def _load_all_readings() -> pd.DataFrame:
    df = get_readings_df(str(DB_PATH))
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@st.cache_data(ttl=4)
def _load_all_tickets() -> pd.DataFrame:
    df = get_tickets_df(str(DB_PATH))
    if not df.empty:
        df["timestamp_flagged"] = pd.to_datetime(df["timestamp_flagged"])
    return df


def load_data(up_to_ts: datetime.datetime = None):
    """Load readings and tickets, optionally filtered up to a datetime."""
    readings = _load_all_readings()
    tickets  = _load_all_tickets()

    if up_to_ts is not None and not readings.empty:
        readings = readings[readings["timestamp"] <= up_to_ts]
    if up_to_ts is not None and not tickets.empty:
        tickets = tickets[tickets["timestamp_flagged"] <= up_to_ts]

    return readings, tickets


# ── HTML component builders ───────────────────────────────────────────────────

def _metric_card(icon_name: str, value: str, label: str, variant: str = "neutral") -> str:
    """Build one metric card HTML block. variant: 'neutral', 'attention', 'primary'."""
    return (
        f'<div class="metric-card metric-{variant}">'
        f'<div class="metric-icon">{icon(icon_name, 18)}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>'
    )


def render_metrics(readings: pd.DataFrame, tickets: pd.DataFrame) -> None:
    """Render the four top-level metric cards as custom HTML."""
    n_readings  = f"{len(readings):,}" if not readings.empty else "0"
    n_tickets   = str(len(tickets))
    n_zones     = str(readings["zone_id"].nunique()) if not readings.empty else "0"
    water_loss  = (
        f"{tickets['estimated_water_loss_liters'].sum():.1f} L"
        if not tickets.empty and "estimated_water_loss_liters" in tickets.columns
        else "0 L"
    )

    ticket_variant = "attention" if len(tickets) > 0 else "neutral"
    water_variant  = "primary" if not tickets.empty else "neutral"

    html = (
        '<div class="metric-row">'
        + _metric_card("activity", n_readings,  "sensor readings",     variant="neutral")
        + _metric_card("list",     n_tickets,   "flagged tickets",    variant=ticket_variant)
        + _metric_card("building", n_zones,     "zones monitored",    variant="neutral")
        + _metric_card("drop",     water_loss,  "estimated water loss", variant=water_variant)
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_progress(value: float, label: str) -> None:
    """Render a minimal styled progress bar (replaces st.progress())."""
    pct = min(max(value * 100, 0), 100)
    st.markdown(
        f'<div class="custom-progress">'
        f'<div class="custom-progress-label">{label}</div>'
        f'<div class="custom-progress-track">'
        f'<div class="custom-progress-fill" style="width:{pct:.1f}%"></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _ticket_row(row: pd.Series) -> str:
    """Build one <tr> HTML string for a ticket."""
    severity    = str(row.get("severity_label", "Flagged"))
    stripe_cls  = SEV_STRIPE.get(severity, "stripe-flagged")
    sev_color   = SEV_COLOR.get(severity, "var(--text-muted)")
    sev_icon    = SEV_ICON.get(severity, "circle")
    sev_icon_html = icon(sev_icon, 13)

    # Timestamp
    ts = row.get("timestamp_flagged", "")
    ts_str = ts.strftime("%b %d  %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]

    # Water loss
    wl = row.get("estimated_water_loss_liters", None)
    wl_str = f"{float(wl):.1f}" if wl is not None else "—"

    # Anomaly type — replace underscores, sentence case
    atype = str(row.get("anomaly_type", "")).replace("_", " ")

    # Status
    status = str(row.get("status", "open"))

    tid     = str(row.get("ticket_id", ""))
    zone    = str(row.get("zone_id", ""))
    fixture = str(row.get("fixture_id", ""))

    return (
        f'<tr>'
        f'<td class="td-stripe {stripe_cls}"></td>'
        f'<td class="td-mono">{tid}</td>'
        f'<td class="td-muted">{ts_str}</td>'
        f'<td class="td-muted">{zone}</td>'
        f'<td>{fixture}</td>'
        f'<td>{atype}</td>'
        f'<td>'
        f'<span class="sev-cell sev-{severity}" style="color:{sev_color}">'
        f'{sev_icon_html} {severity}'
        f'</span>'
        f'</td>'
        f'<td class="td-num">{wl_str} L</td>'
        f'<td class="td-muted">{status}</td>'
        f'</tr>'
    )


def render_tickets_html(tickets: pd.DataFrame) -> None:
    """Render the tickets list as a custom HTML table."""
    if tickets.empty:
        st.markdown(
            '<div class="no-data">'
            'No tickets flagged yet.<br>'
            'Run <code>python src/simulator.py</code> then '
            '<code>python src/detector.py</code>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    shown    = tickets.head(MAX_TICKETS_SHOWN)
    overflow = len(tickets) - MAX_TICKETS_SHOWN

    rows_html = "".join(_ticket_row(row) for _, row in shown.iterrows())

    table_html = (
        '<div class="ticket-wrap">'
        '<table class="ticket-table">'
        '<thead><tr>'
        '<th class="th-stripe"></th>'
        '<th>Ticket</th>'
        '<th>Flagged at</th>'
        '<th>Zone</th>'
        '<th>Fixture</th>'
        '<th>Type</th>'
        '<th>Severity</th>'
        '<th class="th-num">Water loss</th>'
        '<th>Status</th>'
        '</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

    if overflow > 0:
        st.markdown(
            f'<p style="font-size:0.74rem;color:var(--text-muted);margin-top:0.4rem">'
            f'Showing {MAX_TICKETS_SHOWN} of {len(tickets)} tickets — '
            f'{overflow} additional tickets not shown.</p>',
            unsafe_allow_html=True,
        )


# ── Chart builders ────────────────────────────────────────────────────────────

def build_flow_chart(
    readings: pd.DataFrame,
    zone_filter: list = None,
    uirevision: str = "stable",
    chart_mode: str = "zone_total",
) -> go.Figure:
    """
    Flow rate chart with two display modes.

    chart_mode='zone_total'  — one trace per zone (aggregated sum), 4 lines max.
                               Default view: clean, no per-fixture clutter.
    chart_mode='per_fixture' — one trace per fixture, colored by zone,
                               line style by fixture type (solid/dash/dot).

    uirevision: Plotly key that preserves client-side state (legend isolation,
    zoom, pan) across Streamlit reruns. Pass same string to keep state;
    new/unique string to force a full chart reset.
    """
    fig = go.Figure()

    if readings.empty:
        fig.update_layout(
            title=dict(text="No readings yet", font=dict(color="#8A97A0", size=13)),
            paper_bgcolor="#12161A",
            plot_bgcolor="#12161A",
            height=360,
        )
        return fig

    df = readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if zone_filter:
        df = df[df["zone_id"].isin(zone_filter)]

    # Downsample: every 5 minutes for rendering performance
    df = df[df["timestamp"].dt.minute % 5 == 0]

    if chart_mode == "zone_total":
        # ── Zone total mode: aggregate flow per zone per timestamp ─────────────
        zone_agg = (
            df.groupby(["timestamp", "zone_id"], as_index=False)
            ["flow_rate_lpm"].sum()
        )
        for zone_id, zdf in zone_agg.groupby("zone_id"):
            zdf   = zdf.sort_values("timestamp")
            color = ZONE_COLORS.get(str(zone_id), "#8A97A0")
            label = str(zone_id).replace("T2_", "").replace("_", " ")
            fig.add_trace(go.Scatter(
                x=zdf["timestamp"],
                y=zdf["flow_rate_lpm"],
                name=label,
                uid=f"zone_{zone_id}",
                mode="lines",
                line=dict(color=color, width=2.0, dash="solid"),
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Time: %{x|%b %d %H:%M}<br>"
                    "Total flow: %{y:.2f} LPM"
                    "<extra></extra>"
                ),
            ))
        chart_title = "Flow rate (L/min) — zone totals"
    else:
        # ── Per-fixture mode: one trace per fixture, zone color + type dash ────
        # Infer fixture type from fixture_id prefix — more robust than a dict
        # lookup which can silently fall back to "sink" on any mismatch.
        #   "Urinal_*" → dot     "Toilet_*" → dash     anything else → solid
        def _dash_for(fid: str) -> str:
            fid_lower = str(fid).lower()
            if fid_lower.startswith("urinal"):
                return "dot"
            if fid_lower.startswith("toilet"):
                return "dash"
            return "solid"

        def _ftype_label(fid: str) -> str:
            fid_lower = str(fid).lower()
            if fid_lower.startswith("urinal"):
                return "urinal"
            if fid_lower.startswith("toilet"):
                return "toilet"
            return "sink"

        for fixture_id, fdf in df.groupby("fixture_id"):
            fdf        = fdf.sort_values("timestamp")
            zone_id    = str(fdf["zone_id"].iloc[0])
            color      = ZONE_COLORS.get(zone_id, "#8A97A0")
            dash       = _dash_for(fixture_id)
            ftype      = _ftype_label(fixture_id)
            # Sink_01 slightly heavier — hero fixture (sustained leak)
            width      = 2.2 if fixture_id == "Sink_01" else 1.4
            zone_label = zone_id.replace("T2_", "").replace("_", " ")
            fig.add_trace(go.Scatter(
                x=fdf["timestamp"],
                y=fdf["flow_rate_lpm"],
                name=f"{fixture_id}  • {zone_label}",
                uid=f"fixture_{fixture_id}",
                mode="lines",
                line=dict(color=color, width=width, dash=dash),
                hovertemplate=(
                    f"<b>{fixture_id}</b> ({ftype})<br>"
                    "Time: %{x|%b %d %H:%M}<br>"
                    "Flow: %{y:.2f} LPM"
                    "<extra></extra>"
                ),
            ))
        chart_title = "Flow rate (L/min) — per fixture  —  color = zone  —  style = type (solid sink / dashed toilet / dotted urinal)"

    fig.update_layout(
        title=dict(
            text=chart_title,
            font=dict(family="IBM Plex Sans", size=12, color="#8A97A0"),
            x=0, xanchor="left", pad=dict(l=0, b=8),
        ),
        paper_bgcolor="#12161A",
        plot_bgcolor="#12161A",
        font=dict(family="IBM Plex Sans", color="#8A97A0", size=11),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(107, 140, 174, 0.07)",
            zeroline=False, showline=False,
            tickfont=dict(family="IBM Plex Sans", size=10, color="#8A97A0"),
            title=None,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(107, 140, 174, 0.07)",
            zeroline=False, showline=False,
            tickfont=dict(family="IBM Plex Sans", size=10, color="#8A97A0"),
            title=dict(text="L/min", font=dict(size=10, color="#8A97A0")),
        ),
        legend=dict(
            bgcolor="rgba(27,33,39,0.8)",
            bordercolor="rgba(255,255,255,0.07)",
            borderwidth=1,
            font=dict(family="IBM Plex Sans", size=10, color="#8A97A0"),
            orientation="h",
            yanchor="top",
            y=-0.14,
            xanchor="left",
            x=0,
            itemclick="toggle",          # single click: show/hide that trace
            itemdoubleclick="toggleothers",  # double click: isolate (hide all others)
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1B2127",
            bordercolor="rgba(255,255,255,0.1)",
            font=dict(family="IBM Plex Sans", size=11, color="#E7ECEE"),
        ),
        height=370,
        margin=dict(l=0, r=0, t=32, b=52),
        uirevision=uirevision,   # preserves legend isolation / zoom across st.rerun()
    )
    return fig


def build_heatmap(readings: pd.DataFrame) -> go.Figure:
    """Occupancy pattern heatmap, styled to match design system."""
    if readings.empty:
        return go.Figure()

    df = readings.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    agg   = df.groupby(["fixture_id", "hour"])["occupancy"].mean().reset_index()
    pivot = agg.pivot(index="fixture_id", columns="hour", values="occupancy").fillna(0)

    # Dynamic height: allocate ~26px per fixture row plus header/margin headroom
    # so Plotly never auto-skips categorical labels.
    chart_height = max(280, len(pivot) * 26 + 80)

    import plotly.express as px
    fig = px.imshow(
        pivot,
        labels=dict(x="Hour of day", y="Fixture", color="Avg occupancy"),
        color_continuous_scale=[[0, "#12161A"], [0.35, "#1B242E"], [0.7, "#3B526B"], [1, "#6B8CAE"]],
        aspect="auto",
        zmin=0, zmax=1,
    )
    fig.update_layout(
        title=dict(
            text="Occupancy pattern — average by hour of day",
            font=dict(family="IBM Plex Sans", size=12, color="#8A97A0"),
            x=0, xanchor="left",
        ),
        paper_bgcolor="#12161A",
        plot_bgcolor="#12161A",
        font=dict(family="IBM Plex Sans", color="#8A97A0", size=10),
        coloraxis_colorbar=dict(
            tickfont=dict(family="IBM Plex Sans", size=9, color="#8A97A0"),
            thickness=10,
            len=0.8,
        ),
        xaxis=dict(tickfont=dict(family="IBM Plex Sans", size=9, color="#8A97A0"), title=None, dtick=1),
        yaxis=dict(tickfont=dict(family="IBM Plex Sans", size=9, color="#8A97A0"), title=None, dtick=1),
        height=chart_height,
        margin=dict(l=0, r=60, t=36, b=0),
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<span class="brand-bold">KOHLER</span>'
            '<span class="sidebar-heading">Facility Monitor</span>'
            '</div>'
            '<p class="sidebar-sub">Terminal 2 · airport restroom block</p>',
            unsafe_allow_html=True,
        )
        st.divider()

        view = st.radio(
            "View",
            ["Full dataset", "Replay demo"],
            key="view_mode",
            label_visibility="collapsed",
        )

        st.divider()

        zone_items = "".join(
            f'<div class="zone-item"><div class="zone-dot" style="background:{color}"></div>{z}</div>'
            for z, color in ZONE_COLORS.items()
        )
        st.markdown(
            '<p style="font-size:0.71rem;color:var(--text-muted);'
            'letter-spacing:0.06em;margin-bottom:0.5rem">zones</p>'
            f'{zone_items}',
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown(
            '<p style="font-size:0.71rem;color:var(--text-muted);'
            'letter-spacing:0.06em;margin-bottom:0.4rem">detection</p>'
            '<p style="font-size:0.78rem;color:var(--text-muted);line-height:1.55">'
            'Adaptive baseline (2.5&sigma;/fixture/hr)<br>'
            'Multi-signal correlation (occupancy, duration, health)<br>'
            'Slow-drip rate-of-change tracking<br>'
            'Weighted severity scoring (0&ndash;100)</p>',
            unsafe_allow_html=True,
        )

    return str(view)


# ── Page header ───────────────────────────────────────────────────────────────

def render_header() -> None:
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f'<div class="page-header">'
        f'<div class="brand-title">KOHLER</div>'
        f'<div class="brand-subtitle">Facility Monitor</div>'
        f'<div class="sub">Terminal 2 &nbsp;&middot;&nbsp; airport restroom block '
        f'&nbsp;&middot;&nbsp; Jan 15&ndash;16, 2024'
        f'&nbsp;&nbsp;<span class="sys-time">{now_str}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Full dataset view ─────────────────────────────────────────────────────────

def render_full_dataset() -> None:
    readings, tickets = load_data()

    if readings.empty:
        st.markdown(
            '<div class="no-data">'
            'No sensor data in the database.<br><br>'
            'Run <code>python src/simulator.py</code> &nbsp;then&nbsp; '
            '<code>python src/detector.py</code>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # Metrics
    render_metrics(readings, tickets)

    # Zone filter — default to first zone only to avoid 17-trace clutter
    zones = sorted(readings["zone_id"].unique().tolist())
    default_zone = [zones[0]] if zones else zones
    selected = st.multiselect(
        "Filter zones",
        options=zones,
        default=default_zone,
        key="zone_filter_full",
        label_visibility="collapsed",
    )
    active_zones = selected or zones

    # Chart mode toggle + chart
    st.markdown(
        f'<div class="section-label">'
        f'{icon("activity", 13)} flow rate over time'
        f'</div>',
        unsafe_allow_html=True,
    )
    chart_mode = st.radio(
        "Chart view",
        options=["Zone total", "Per fixture"],
        index=0,          # default: Zone total
        horizontal=True,
        key="chart_mode_full",
        label_visibility="collapsed",
    )
    mode_key = "zone_total" if chart_mode == "Zone total" else "per_fixture"
    st.plotly_chart(
        build_flow_chart(
            readings,
            zone_filter=active_zones,
            uirevision=f"full_dataset_{mode_key}",
            chart_mode=mode_key,
        ),
        width="stretch",
        config={"displayModeBar": False},
        key="full_dataset_flow_chart",
    )

    # Occupancy heatmap (collapsible — reduces visual noise on first load)
    with st.expander("Occupancy pattern by hour of day", expanded=False):
        st.plotly_chart(
            build_heatmap(readings),
            width="stretch",
            config={"displayModeBar": False},
        )

    # Tickets
    n_tickets = len(tickets)
    st.markdown(
        f'<div class="section-label">'
        f'{icon("list", 13)} flagged tickets &nbsp;'
        f'<span style="color:var(--text-muted);font-weight:400">({n_tickets})</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_tickets_html(tickets)

    # Auto-refresh
    time.sleep(DASHBOARD_REFRESH_SECONDS)
    st.rerun()


# ── Replay demo view ──────────────────────────────────────────────────────────

def render_replay() -> None:
    """
    Replay mode — stepped playback of the 48-hour simulation.

    Architecture:
      The tick loop uses @st.fragment(run_every=...) so it fires on a timer
      WITHOUT triggering a full Streamlit script rerun.

      The Plotly flow chart lives INSIDE this fragment so it updates automatically
      with new readings on every tick. Plotly's client-side state (legend visibility
      toggles, zoom, pan) is preserved across ticks via:
        1. Stable component key: key="replay_flow_chart"
        2. Stable uirevision: uirevision="replay_chart"
        3. Stable trace uids: uid=f"zone_{zone_id}"
    """
    sim_end = SIM_START + datetime.timedelta(hours=SIM_DURATION_HOURS)

    # ── Session state init ────────────────────────────────────────────────────
    if "replay_ts" not in st.session_state:
        st.session_state.replay_ts = SIM_START
    if "replay_running" not in st.session_state:
        st.session_state.replay_running = False
    if "replay_speed" not in st.session_state:
        st.session_state.replay_speed = 2

    # ── Controls (parent scope — button clicks cause full reruns intentionally)
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        btn_label = "Pause" if st.session_state.replay_running else "Play"
        if st.button(btn_label, key="replay_play"):
            st.session_state.replay_running = not st.session_state.replay_running
            st.rerun()
    with c2:
        if st.button("Reset", key="replay_reset"):
            st.session_state.replay_ts = SIM_START
            st.session_state.replay_running = False
            st.rerun()
    with c3:
        speed = st.select_slider(
            "Simulated hours per step",
            options=[0.5, 1, 2, 4, 8],
            value=st.session_state.replay_speed,
            key="replay_speed",
        )

    # ── Fragment: clock / metrics / chart / tickets / tick-advance ────────────
    #    run_every fires this block on a timer without full page reruns.
    #    The chart is inside this fragment so it auto-updates data on each tick.
    @st.fragment(run_every=REPLAY_REFRESH_SECONDS if st.session_state.replay_running else None)
    def _replay_ticker() -> None:
        cur_ts   = st.session_state.replay_ts
        progress = min(
            (cur_ts - SIM_START).total_seconds() / (SIM_DURATION_HOURS * 3600),
            1.0,
        )

        # Clock display
        st.markdown(
            f'<div class="replay-clock">'
            f'<div class="replay-clock-label">simulated time</div>'
            f'<div class="replay-clock-time">'
            f'{cur_ts.strftime("%a, %d %b %Y  \u2014  %H:%M")}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        render_progress(progress, f"{progress*100:.0f}% of 48-hour simulation")

        # Data for metrics, chart, and tickets
        readings, tickets = load_data(up_to_ts=cur_ts)
        render_metrics(readings, tickets)

        # Flow rate chart — inside fragment so it updates on every tick
        st.markdown(
            f'<div class="section-label">'
            f'{icon("activity", 13)} flow rate so far'
            f'</div>',
            unsafe_allow_html=True,
        )
        if not readings.empty:
            st.plotly_chart(
                build_flow_chart(readings, uirevision="replay_chart"),
                width="stretch",
                config={"displayModeBar": False},
                key="replay_flow_chart",
            )
        else:
            st.caption("No readings yet — press Play to start the replay.")

        # Tickets
        n_tickets = len(tickets)
        st.markdown(
            f'<div class="section-label">'
            f'{icon("list", 13)} tickets discovered &nbsp;'
            f'<span style="color:var(--text-muted);font-weight:400">({n_tickets})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        render_tickets_html(tickets)

        # Advance clock (only when running)
        if st.session_state.replay_running:
            spd   = st.session_state.get("replay_speed", 2)
            nxt   = cur_ts + datetime.timedelta(hours=float(spd))
            if nxt >= sim_end:
                st.session_state.replay_ts = sim_end
                st.session_state.replay_running = False
                st.success("Replay complete — full 48 hours simulated.")
            else:
                st.session_state.replay_ts = nxt

    _replay_ticker()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Inject design system CSS — done once, applies to the whole page
    st.markdown(_CSS, unsafe_allow_html=True)

    render_header()
    view = render_sidebar()

    if view == "Full dataset":
        render_full_dataset()
    else:
        render_replay()


if __name__ == "__main__":
    main()
