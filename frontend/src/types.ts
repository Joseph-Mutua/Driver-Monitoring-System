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
  start_display_time?: string | null;
  end_display_time?: string | null;
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

export type MlPipelineRunRequest = {
  manifest: string;
  output_root: string;
  ground_truth?: string;
};

export type MlPipelineJob = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  message: string;
  manifest: string;
  output_root: string;
  ground_truth?: string | null;
  started_at: string;
  finished_at?: string | null;
  log_url?: string | null;
  artifacts: Record<string, string>;
  artifact_urls: Record<string, string>;
  error?: string | null;
};

export type MlPipelineJobList = {
  jobs: MlPipelineJob[];
};

export type MlPipelineLogResponse = {
  job_id: string;
  log_tail: string;
};

export type MlPipelineActionResponse = {
  job_id: string;
  status: string;
  message: string;
};
