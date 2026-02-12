import type { Trip } from "../types";

type Props = {
  trips: Trip[];
  onOpen: (tripId: string) => void;
};

export default function ClipSummaries({ trips, onOpen }: Props) {
  return (
    <section className="glass animate-rise rounded-3xl p-6 shadow-glow">
      <h3 className="font-display text-xl font-semibold">Trip History</h3>
      <div className="mt-4 overflow-auto rounded-xl border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3">Trip ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Driver</th>
              <th className="px-4 py-3">Vehicle</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {trips.map((trip) => (
              <tr key={trip.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{trip.id.slice(0, 8)}</td>
                <td className="px-4 py-2 uppercase">{trip.status}</td>
                <td className="px-4 py-2">{trip.driver_id || "-"}</td>
                <td className="px-4 py-2">{trip.vehicle_id || "-"}</td>
                <td className="px-4 py-2">{trip.duration_seconds.toFixed(1)}s</td>
                <td className="px-4 py-2">
                  <button onClick={() => onOpen(trip.id)} className="text-cyan-700 hover:underline">
                    open
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
