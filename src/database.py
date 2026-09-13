"""
database.py — SQLite schema creation and query helpers.

Schema matches Section 3 of the PRD exactly.
All functions accept a db_path string so they are stateless and testable.
"""

import sqlite3
from pathlib import Path

import pandas as pd


# ── Connection ─────────────────────────────────────────────────────────────────

def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set for dict-style access."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db(db_path: str) -> None:
    """
    Create the sensor_readings and tickets tables if they don't already exist.
    Safe to call multiple times (idempotent).
    """
    conn = get_connection(db_path)
    with conn:
        # ── sensor_readings (Section 3: Sensor reading) ────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp               TEXT    NOT NULL,
                zone_id                 TEXT    NOT NULL,
                fixture_id              TEXT    NOT NULL,
                flow_rate_lpm           REAL    NOT NULL,
                occupancy               INTEGER NOT NULL,
                flush_count_cumulative  INTEGER NOT NULL,
                sensor_status           TEXT    NOT NULL DEFAULT 'OK'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_readings_fixture_ts
            ON sensor_readings (fixture_id, timestamp)
        """)

        # ── tickets (Section 3: Ticket) ────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id                   TEXT PRIMARY KEY,
                timestamp_flagged           TEXT NOT NULL,
                zone_id                     TEXT NOT NULL,
                fixture_id                  TEXT NOT NULL,
                anomaly_type                TEXT NOT NULL,
                severity_score              REAL,
                severity_label              TEXT NOT NULL DEFAULT 'Flagged',
                explanation                 TEXT NOT NULL DEFAULT '',
                estimated_water_loss_liters REAL,
                estimated_cost_impact       REAL,
                status                      TEXT NOT NULL DEFAULT 'open'
            )
        """)
    conn.close()


# ── Write ──────────────────────────────────────────────────────────────────────

def insert_readings_df(db_path: str, df: pd.DataFrame) -> None:
    """
    Bulk-insert a DataFrame of sensor readings.
    The DataFrame must NOT include the auto-increment 'id' column.
    """
    conn = get_connection(db_path)
    df.to_sql("sensor_readings", conn, if_exists="append", index=False)
    conn.close()


def insert_ticket(db_path: str, ticket: dict) -> None:
    """Insert (or replace) a single ticket row."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO tickets (
                ticket_id, timestamp_flagged, zone_id, fixture_id,
                anomaly_type, severity_score, severity_label, explanation,
                estimated_water_loss_liters, estimated_cost_impact, status
            ) VALUES (
                :ticket_id, :timestamp_flagged, :zone_id, :fixture_id,
                :anomaly_type, :severity_score, :severity_label, :explanation,
                :estimated_water_loss_liters, :estimated_cost_impact, :status
            )
        """, ticket)
    conn.close()


# ── Read ───────────────────────────────────────────────────────────────────────

def get_readings_df(db_path: str, fixture_id: str = None) -> pd.DataFrame:
    """
    Return all (or fixture-filtered) sensor readings as a DataFrame.
    timestamp column is parsed as datetime.
    """
    db_path = str(db_path)
    if not Path(db_path).exists():
        return pd.DataFrame()

    conn = get_connection(db_path)
    query = "SELECT timestamp, zone_id, fixture_id, flow_rate_lpm, occupancy, flush_count_cumulative, sensor_status FROM sensor_readings"
    params: list = []
    if fixture_id:
        query += " WHERE fixture_id = ?"
        params.append(fixture_id)
    query += " ORDER BY timestamp"

    df = pd.read_sql_query(query, conn, params=params, parse_dates=["timestamp"])
    conn.close()
    return df


def get_tickets_df(db_path: str) -> pd.DataFrame:
    """Return all tickets as a DataFrame, newest first."""
    db_path = str(db_path)
    if not Path(db_path).exists():
        return pd.DataFrame()

    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT * FROM tickets ORDER BY timestamp_flagged DESC",
        conn,
        parse_dates=["timestamp_flagged"],
    )
    conn.close()
    return df
