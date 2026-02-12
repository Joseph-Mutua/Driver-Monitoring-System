import type { Trip } from "../types";

type Props = { trip: Trip };

export default function JobProgress({ trip }: Props) {
  return (
    <section className="glass animate-rise rounded-3xl p-6 shadow-glow">
      <h3 className="font-display text-xl font-semibold">Processing Status</h3>
      <p className="mt-2 text-sm text-slate-700">{trip.message || "In progress"}</p>
      <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan to-emerald transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, trip.progress))}%` }}
        />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-600">
        <span>{trip.status.toUpperCase()}</span>
        <span>{trip.progress.toFixed(1)}%</span>
      </div>
      {trip.error && <p className="mt-3 text-sm font-semibold text-rose">{trip.error}</p>}
      {trip.report_pdf_url && (
        <a href={trip.report_pdf_url} target="_blank" className="mt-4 inline-block text-sm font-semibold text-cyan-700">
          Download PDF report
        </a>
      )}
    </section>
  );
}
