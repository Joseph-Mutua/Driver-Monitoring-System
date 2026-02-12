import type { EventItem } from "../types";

type Props = { events: EventItem[] };

type SeverityGrade = "low" | "moderate" | "high";

/** Return severity grade for a 0–1 value */
function severityGrade(value: number): SeverityGrade {
  if (value < 0.3) return "low";
  if (value < 0.6) return "moderate";
  return "high";
}

/** Pill styles: explicit hex so colors are visible (theme only defines single amber/emerald/rose) */
const SEVERITY_STYLES: Record<SeverityGrade, string> = {
  low: "bg-[#d1fae5] text-[#047857] border border-[#6ee7b7]",
  moderate: "bg-[#fef3c7] text-[#b45309] border border-[#fcd34d]",
  high: "bg-[#fecdd3] text-[#be123c] border border-[#fda4af]"
};

/** Solid color swatch for legend */
const SEVERITY_SWATCH: Record<SeverityGrade, string> = {
  low: "bg-[#10b981] border-[#059669]",
  moderate: "bg-[#f59e0b] border-[#d97706]",
  high: "bg-[#e11d48] border-[#be123c]"
};

const SEVERITY_LEGEND: { grade: SeverityGrade; range: string; label: string }[] = [
  { grade: "low", range: "0.0 – 0.3", label: "Low (brief or low confidence)" },
  { grade: "moderate", range: "0.3 – 0.6", label: "Moderate" },
  { grade: "high", range: "0.6 – 1.0", label: "High (strong or prolonged)" }
];

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
    <section className="card animate-rise overflow-visible p-6 shadow-card">
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
            {sorted.map((event) => {
              const grade = severityGrade(event.severity);
              return (
                <tr key={event.id} className="transition-colors hover:bg-slate-50/80">
                  <td className="px-3 py-3 font-medium text-ink">{event.type.replace(/_/g, " ")}</td>
                  <td className="px-3 py-3 uppercase text-slate-600">{event.stream}</td>
                  <td
                    className="max-w-0 truncate px-3 py-3 text-slate-600"
                    title={event.clip_name}
                  >
                    {shortenClipName(event.clip_name)}
                  </td>
                  <td className="px-3 py-3 tabular-nums text-slate-600" title={event.ts_ms_start != null ? `${event.ts_ms_start} ms` : undefined}>
                    {event.start_display_time ?? event.ts_ms_start}
                  </td>
                  <td className="px-3 py-3 tabular-nums text-slate-600" title={event.ts_ms_end != null ? `${event.ts_ms_end} ms` : undefined}>
                    {event.end_display_time ?? event.ts_ms_end}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex rounded-md px-2 py-1 font-medium tabular-nums ${SEVERITY_STYLES[grade]}`}
                    >
                      {event.severity.toFixed(2)}
                    </span>
                  </td>
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
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-slate-200 pt-4 text-xs text-slate-600">
          <span className="font-medium text-slate-500">Severity:</span>
          {SEVERITY_LEGEND.map(({ grade, range, label }) => (
            <span key={grade} className="inline-flex items-center gap-2">
              <span
                className={`h-3 w-3 shrink-0 rounded-sm border ${SEVERITY_SWATCH[grade]}`}
                aria-hidden
              />
              <span
                className={`inline-flex rounded-md px-2 py-0.5 font-medium tabular-nums ${SEVERITY_STYLES[grade]}`}
                aria-hidden
              >
                {range}
              </span>
              <span>{label}</span>
            </span>
          ))}
      </footer>
    </section>
  );
}
