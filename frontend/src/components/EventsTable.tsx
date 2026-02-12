import type { EventItem } from "../types";

type Props = { events: EventItem[] };

export default function EventsTable({ events }: Props) {
  const sorted = [...events].sort((a, b) => b.severity - a.severity);

  return (
    <section className="glass animate-rise rounded-3xl p-6 shadow-glow">
      <h3 className="font-display text-xl font-semibold">Event Timeline</h3>
      <div className="mt-4 max-h-[430px] overflow-auto rounded-xl border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-slate-50 text-slate-700">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Stream</th>
              <th className="px-4 py-3">Clip</th>
              <th className="px-4 py-3">Start</th>
              <th className="px-4 py-3">End</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Artifacts</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((event) => (
              <tr key={event.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{event.type}</td>
                <td className="px-4 py-2 uppercase">{event.stream}</td>
                <td className="px-4 py-2">{event.clip_name}</td>
                <td className="px-4 py-2">{event.ts_ms_start}</td>
                <td className="px-4 py-2">{event.ts_ms_end}</td>
                <td className="px-4 py-2">{event.severity.toFixed(2)}</td>
                <td className="px-4 py-2">
                  <div className="flex gap-2">
                    {event.snapshot_url && (
                      <a href={event.snapshot_url} target="_blank" className="text-cyan-700 hover:underline">
                        snapshot
                      </a>
                    )}
                    {event.clip_url && (
                      <a href={event.clip_url} target="_blank" className="text-cyan-700 hover:underline">
                        clip
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
