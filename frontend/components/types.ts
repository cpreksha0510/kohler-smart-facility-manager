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

export interface TicketEvidence {
  expected_flow_lpm: number;
  observed_flow_lpm: number;
  peak_flow_lpm: number;
  flow_deviation_lpm: number;
  duration_minutes: number;
  occupancy_rate: number;
  occupancy_mismatch: number;
  sensor_health: string;
  sensor_health_score: number;
  normalized_flow_deviation: number;
  normalized_duration: number;
  normalized_occupancy_mismatch: number;
  normalized_sensor_health: number;
  evidence_strength_score: number;
  evidence_strength_label: "Strong" | "Moderate" | "Weak";
  anomaly_type: string;
  severity_score: number;
  severity_label: string;
  estimated_water_loss_liters: number;
}

export interface ProjectionHorizon {
  duration_minutes: number;
  projected_loss_liters: number;
  projected_cost_inr: number;
}

export interface InterventionImpact {
  actual_loss_liters: number;
  potential_unassisted_loss_liters: number;
  estimated_water_saved_liters: number;
  avoided_cost_inr: number;
  counterfactual_horizon_hours: number;
  model_label: string;
}

export interface TicketSustainability {
  type: "active" | "resolved";
  projections?: {
    "1h": ProjectionHorizon;
    "6h": ProjectionHorizon;
    "24h": ProjectionHorizon;
    "7d": ProjectionHorizon;
  };
  intervention_impact?: InterventionImpact;
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
  evidence?: TicketEvidence;
  sustainability?: TicketSustainability;
}

export interface ZoneSustainability {
  zone_id: string;
  water_waste_liters: number;
  water_saved_liters: number;
  cost_impact_inr: number;
  avoided_cost_inr: number;
  open_count: number;
  resolved_count: number;
}

export interface SustainabilitySummary {
  water_waste_liters: number;
  water_saved_liters: number;
  cost_impact_inr: number;
  avoided_cost_inr: number;
  projected_unresolved_loss_24h_liters: number;
  projected_unresolved_loss_7d_liters: number;
  highest_waste_fixture?: {
    fixture_id: string;
    zone_id: string;
    water_waste_liters: number;
    cost_impact_inr: number;
    ticket_count: number;
  } | null;
  highest_waste_zone?: {
    zone_id: string;
    water_waste_liters: number;
    cost_impact_inr: number;
    open_count: number;
    resolved_count: number;
  } | null;
  zone_breakdown: ZoneSustainability[];
  model_notice: string;
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
