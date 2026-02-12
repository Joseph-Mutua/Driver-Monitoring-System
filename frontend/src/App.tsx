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
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 md:px-8">
      <header className="animate-rise">
        <p className="font-display text-xs uppercase tracking-[0.25em] text-cyan-700">DMS + ADAS Suite</p>
        <h1 className="mt-2 font-display text-4xl font-bold text-ink md:text-5xl">Trip Safety Intelligence</h1>
        <p className="mt-3 max-w-3xl text-slate-700">
          Upload front and cabin streams, process with synchronized DMS and ADAS analytics, and review event clips,
          timeline, scores, and downloadable PDF reports.
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
      {error && <p className="rounded-xl bg-rose/10 p-3 text-sm font-semibold text-rose">{error}</p>}

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
      <ClipSummaries trips={trips} onOpen={loadTrip} />
    </main>
  );
}
