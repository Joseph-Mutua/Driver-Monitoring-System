import { useEffect, useMemo, useState } from "react";
import ClipSummaries from "./components/ClipSummaries";
import EventsTable from "./components/EventsTable";
import JobProgress from "./components/JobProgress";
import KPIGrid from "./components/KPIGrid";
import UploadPanel from "./components/UploadPanel";
import { completeUpload, createTrip, getTrip, getTripEvents, getTripScores, listTrips } from "./services/api";
import type { EventItem, Score, Trip } from "./types";

export default function App() {
  const [dayFolder, setDayFolder] = useState("");
  const [driverId, setDriverId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [frontFiles, setFrontFiles] = useState<File[]>([]);
  const [cabinFiles, setCabinFiles] = useState<File[]>([]);

  const [currentTrip, setCurrentTrip] = useState<Trip | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [scores, setScores] = useState<Score | null>(null);
  const [trips, setTrips] = useState<Trip[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canPoll = useMemo(() => {
    if (!currentTrip) return false;
    return currentTrip.status === "processing" || currentTrip.status === "uploaded";
  }, [currentTrip]);

  async function refreshTrips() {
    const rows = await listTrips();
    setTrips(rows);
  }

  async function loadTrip(tripId: string) {
    const trip = await getTrip(tripId);
    setCurrentTrip(trip);
    if (trip.status === "done") {
      const [tripEvents, tripScores] = await Promise.all([getTripEvents(tripId), getTripScores(tripId)]);
      setEvents(tripEvents);
      setScores(tripScores);
    }
  }

  async function onAnalyze() {
    setError(null);
    setBusy(true);
    setEvents([]);
    setScores(null);

    try {
      const created = await createTrip({
        dayFolder,
        driverId: driverId || undefined,
        vehicleId: vehicleId || undefined,
        frontFiles,
        cabinFiles
      });

      await completeUpload(created.trip.id);
      const started = await getTrip(created.trip.id);
      setCurrentTrip(started);
      await refreshTrips();
    } catch {
      setError("Trip submission failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshTrips().catch(() => {
      setError("Could not load trip history.");
    });
  }, []);

  useEffect(() => {
    if (!canPoll || !currentTrip) return;
    const timer = setInterval(async () => {
      try {
        const latest = await getTrip(currentTrip.id);
        setCurrentTrip(latest);
        if (latest.status === "done") {
          const [tripEvents, tripScores] = await Promise.all([getTripEvents(latest.id), getTripScores(latest.id)]);
          setEvents(tripEvents);
          setScores(tripScores);
          await refreshTrips();
          clearInterval(timer);
        }
        if (latest.status === "failed") {
          setError(latest.error || "Trip analysis failed.");
          await refreshTrips();
          clearInterval(timer);
        }
      } catch {
        setError("Status polling failed.");
        clearInterval(timer);
      }
    }, 2500);

    return () => clearInterval(timer);
  }, [canPoll, currentTrip]);

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-10 sm:px-6 lg:px-8">
      <header className="animate-rise border-b border-slate-200/80 pb-8">
        <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-cyan-600">DMS + ADAS</p>
        <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">Trip Safety Intelligence</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600">
          Upload front and cabin streams, run synchronized DMS and ADAS analytics, and review events, scores, and PDF reports.
        </p>
      </header>

      <UploadPanel
        dayFolder={dayFolder}
        driverId={driverId}
        vehicleId={vehicleId}
        frontFiles={frontFiles}
        cabinFiles={cabinFiles}
        onDayFolder={setDayFolder}
        onDriverId={setDriverId}
        onVehicleId={setVehicleId}
        onFrontFiles={setFrontFiles}
        onCabinFiles={setCabinFiles}
        onAnalyze={onAnalyze}
        disabled={busy}
      />

      {currentTrip && <JobProgress trip={currentTrip} />}
      {error && (
        <div className="animate-rise rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
          {error}
        </div>
      )}

      {scores && (
        <KPIGrid
          overall={scores.overall_score}
          fatigue={scores.fatigue_score}
          distraction={scores.distraction_score}
          lane={scores.lane_score}
          following={scores.following_distance_score}
        />
      )}

      {events.length > 0 && <EventsTable events={events} />}
      <ClipSummaries
        trips={trips}
        onOpen={loadTrip}
        onDeleted={async (deletedIds) => {
          await refreshTrips();
          if (currentTrip && deletedIds.includes(currentTrip.id)) {
            setCurrentTrip(null);
            setEvents([]);
            setScores(null);
          }
        }}
      />
    </main>
  );
}
