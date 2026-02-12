import type { Trip } from "../types";

type Props = { trip: Trip };

export default function JobProgress({ trip }: Props) {
  return (
    <section className="card animate-rise p-6 shadow-card">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-semibold text-ink">Processing Status</h3>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-600">
          {trip.status}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600">{trip.message || "In progress…"}</p>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-cyan-500 transition-all duration-500 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, trip.progress))}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>Progress</span>
        <span>{trip.progress.toFixed(1)}%</span>
      </div>
      {trip.error && (
        <p className="mt-3 text-sm font-medium text-rose-600">{trip.error}</p>
      )}
      {trip.report_pdf_url && (
        <a
          href={trip.report_pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary mt-4 inline-flex items-center gap-2 text-sm"
        >
          Download PDF report
        </a>
      )}
    </section>
  );
}
