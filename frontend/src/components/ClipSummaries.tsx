import type { Trip } from "../types";

type Props = {
  trips: Trip[];
  onOpen: (tripId: string) => void;
};

export default function ClipSummaries({ trips, onOpen }: Props) {
  return (
    <section className="card animate-rise overflow-hidden p-6 shadow-card">
      <h3 className="font-display text-lg font-semibold text-ink">Trip History</h3>
      <div className="mt-4 overflow-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50/95 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-4 py-3">Trip ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Driver</th>
              <th className="px-4 py-3">Vehicle</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {trips.map((trip) => (
              <tr key={trip.id} className="transition-colors hover:bg-slate-50/80">
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{trip.id.slice(0, 8)}…</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      trip.status === "done"
                        ? "bg-emerald-100 text-emerald-700"
                        : trip.status === "failed"
                          ? "bg-rose-100 text-rose-700"
                          : trip.status === "processing"
                            ? "bg-cyan-100 text-cyan-700"
                            : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {trip.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{trip.driver_id || "—"}</td>
                <td className="px-4 py-3 text-slate-600">{trip.vehicle_id || "—"}</td>
                <td className="px-4 py-3 tabular-nums text-slate-600">{trip.duration_seconds.toFixed(1)}s</td>
                <td className="px-4 py-3">
                  <button onClick={() => onOpen(trip.id)} className="link-pill">
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
