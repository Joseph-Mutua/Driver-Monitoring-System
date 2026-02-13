import axios from "axios";
import type {
  EventItem,
  MlPipelineActionResponse,
  MlPipelineJob,
  MlPipelineJobList,
  MlPipelineLogResponse,
  MlPipelineRunRequest,
  Score,
  Trip,
  TripCompleteResponse,
  TripCreateResponse
} from "../types";

const api = axios.create({ baseURL: "/api" });

export async function createTrip(params: {
  dayFolder: string;
  driverId?: string;
  vehicleId?: string;
  frontFiles: File[];
  rearFiles: File[];
  cabinFiles?: File[];
}) {
  const form = new FormData();
  form.append("day_folder", params.dayFolder);
  if (params.driverId) form.append("driver_id", params.driverId);
  if (params.vehicleId) form.append("vehicle_id", params.vehicleId);
  params.frontFiles.forEach((f) => form.append("front_files", f));
  params.rearFiles.forEach((f) => form.append("rear_files", f));
  (params.cabinFiles || []).forEach((f) => form.append("cabin_files", f));

  const { data } = await api.post<TripCreateResponse>("/trips", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function completeUpload(tripId: string) {
  const { data } = await api.post<TripCompleteResponse>(`/trips/${tripId}/complete-upload`);
  return data;
}

export async function getTrip(tripId: string) {
  const { data } = await api.get<Trip>(`/trips/${tripId}`);
  return data;
}

export async function getTripEvents(tripId: string) {
  const { data } = await api.get<EventItem[]>(`/trips/${tripId}/events`);
  return data;
}

export async function getTripScores(tripId: string) {
  const { data } = await api.get<Score>(`/trips/${tripId}/scores`);
  return data;
}

export async function listTrips(limit = 40) {
  const { data } = await api.get<Trip[]>(`/trips?limit=${limit}`);
  return data;
}

export async function deleteTrip(tripId: string) {
  const { data } = await api.delete<{ deleted: string }>(`/trips/${tripId}`);
  return data;
}

export async function bulkDeleteTrips(tripIds: string[]) {
  const { data } = await api.post<{ deleted: string[]; failed: { id: string; detail: string }[] }>(
    "/trips/bulk-delete",
    { trip_ids: tripIds }
  );
  return data;
}

export async function runMlPipeline(body: MlPipelineRunRequest) {
  const { data } = await api.post<MlPipelineJob>("/ml/pipeline/run", body);
  return data;
}

export async function listMlPipelineJobs() {
  const { data } = await api.get<MlPipelineJobList>("/ml/pipeline/jobs");
  return data;
}

export async function getMlPipelineJob(jobId: string) {
  const { data } = await api.get<MlPipelineJob>(`/ml/pipeline/jobs/${jobId}`);
  return data;
}

export async function getMlPipelineLog(jobId: string) {
  const { data } = await api.get<MlPipelineLogResponse>(`/ml/pipeline/jobs/${jobId}/log`);
  return data;
}

export async function cancelMlPipelineJob(jobId: string) {
  const { data } = await api.post<MlPipelineActionResponse>(`/ml/pipeline/jobs/${jobId}/cancel`);
  return data;
}

export async function retryMlPipelineJob(jobId: string) {
  const { data } = await api.post<MlPipelineJob>(`/ml/pipeline/jobs/${jobId}/retry`);
  return data;
}
