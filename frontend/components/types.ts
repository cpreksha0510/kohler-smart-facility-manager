export interface OverviewMetrics {
  sensor_readings_count: number;
  total_tickets_count: number;
  open_tickets_count: number;
  in_progress_tickets_count: number;
  resolved_tickets_count: number;
  zones_monitored_count: number;
  estimated_water_loss_liters: number;
  estimated_cost_impact_inr: number;
  sim_start: string;
  sim_end: string;
  sim_duration_hours: number;
  zones: { zone_id: string; color: string; name: string }[];
  total_fixtures: number;
}

export interface Reading {
  timestamp_str: string;
  zone_id: string;
  fixture_id?: string;
  flow_rate_lpm: number;
  occupancy?: number;
  sensor_status?: string;
}

export interface Ticket {
  ticket_id: string;
  timestamp_flagged: string;
  timestamp_flagged_str: string;
  zone_id: string;
  fixture_id: string;
  anomaly_type: string;
  severity_score: number;
  severity_label: string;
  explanation: string;
  estimated_water_loss_liters: number;
  estimated_cost_impact: number;
  status: "open" | "dispatched" | "resolved";
  resolution_note?: string;
}

export interface DailyDigest {
  digest: string;
  ticket_count: number;
  created_at: string;
}

export interface OccupancyHeatmapData {
  fixtures: string[];
  hours: number[];
  matrix: number[][];
}
