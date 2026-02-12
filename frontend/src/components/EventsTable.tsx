import type { EventItem } from "../types";

type Props = { events: EventItem[] };

/** Show a short clip name (prefix…suffix) with full name on hover */
function shortenClipName(name: string, maxChars = 28): string {
  if (name.length <= maxChars) return name;
  const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")) : "";
  const base = name.slice(0, -ext.length);
  const keep = Math.max(0, maxChars - ext.length - 4); // "…" + 2 chars each side
  if (keep >= base.length) return name;
  const start = base.slice(0, Math.ceil(keep / 2));
  const end = base.slice(-Math.floor(keep / 2));
  return `${start}…${end}${ext}`;
}

export default function EventsTable({ events }: Props) {
  const sorted = [...events].sort((a, b) => b.severity - a.severity);

  return (
    <section className="card animate-rise overflow-hidden p-6 shadow-card">
      <h3 className="font-display text-lg font-semibold text-ink">Event Timeline</h3>
      <div className="mt-4 max-h-[420px] overflow-auto rounded-lg border border-slate-200">
        <table className="w-full table-fixed text-left text-sm">
          <colgroup>
            <col className="w-[14%]" />
            <col className="w-[8%]" />
            <col className="w-[22%]" />
            <col className="w-[12%]" />
            <col className="w-[12%]" />
            <col className="w-[10%]" />
            <col className="w-[22%]" />
          </colgroup>
          <thead className="sticky top-0 bg-slate-50/95 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-3 py-3">Type</th>
              <th className="px-3 py-3">Stream</th>
              <th className="px-3 py-3">Clip</th>
              <th className="px-3 py-3">Start</th>
              <th className="px-3 py-3">End</th>
              <th className="px-3 py-3">Severity</th>
              <th className="px-3 py-3">Artifacts</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sorted.map((event) => (
              <tr key={event.id} className="transition-colors hover:bg-slate-50/80">
                <td className="px-3 py-3 font-medium text-ink">{event.type.replace(/_/g, " ")}</td>
                <td className="px-3 py-3 uppercase text-slate-600">{event.stream}</td>
                <td
                  className="max-w-0 truncate px-3 py-3 text-slate-600"
                  title={event.clip_name}
                >
                  {shortenClipName(event.clip_name)}
                </td>
                <td className="px-3 py-3 tabular-nums text-slate-600">{event.ts_ms_start}</td>
                <td className="px-3 py-3 tabular-nums text-slate-600">{event.ts_ms_end}</td>
                <td className="px-3 py-3 tabular-nums text-slate-600">{event.severity.toFixed(2)}</td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-2">
                    {event.snapshot_url && (
                      <a href={event.snapshot_url} target="_blank" rel="noopener noreferrer" className="link-pill">
                        Snapshot
                      </a>
                    )}
                    {event.clip_url && (
                      <a href={event.clip_url} target="_blank" rel="noopener noreferrer" className="link-pill">
                        Clip
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
