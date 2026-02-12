import axios from "axios";
import type { EventItem, Score, Trip, TripCompleteResponse, TripCreateResponse } from "../types";

const api = axios.create({ baseURL: "/api" });

export async function createTrip(params: {
  dayFolder: string;
  driverId?: string;
  vehicleId?: string;
  frontFiles: File[];
  cabinFiles: File[];
}) {
  const form = new FormData();
  form.append("day_folder", params.dayFolder);
  if (params.driverId) form.append("driver_id", params.driverId);
  if (params.vehicleId) form.append("vehicle_id", params.vehicleId);
  params.frontFiles.forEach((f) => form.append("front_files", f));
  params.cabinFiles.forEach((f) => form.append("cabin_files", f));

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
