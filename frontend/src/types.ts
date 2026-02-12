export type Trip = {
  id: string;
  created_at: string;
  status: "uploaded" | "processing" | "done" | "failed";
  day_folder?: string | null;
  vehicle_id?: string | null;
  driver_id?: string | null;
  duration_seconds: number;
  sync_offset_seconds: number;
  progress: number;
  message: string;
  error?: string | null;
  report_pdf_url?: string | null;
};

export type TripCreateResponse = {
  trip: Trip;
  uploaded_front_files: number;
  uploaded_cabin_files: number;
};

export type TripCompleteResponse = {
  trip_id: string;
  status: string;
  message: string;
};

export type EventItem = {
  id: number;
  trip_id: string;
  type: string;
  ts_ms_start: number;
  ts_ms_end: number;
  severity: number;
  stream: string;
  clip_name: string;
  snapshot_url?: string | null;
  clip_url?: string | null;
  metadata: Record<string, string | number | boolean>;
};

export type Score = {
  trip_id: string;
  fatigue_score: number;
  distraction_score: number;
  lane_score: number;
  following_distance_score: number;
  overall_score: number;
  details: Record<string, unknown>;
};
