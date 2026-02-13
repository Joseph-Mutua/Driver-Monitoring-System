import { useMemo } from "react";
import type { Score } from "../types";

type Props = {
  score: Score;
};

function toRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export default function TripInsights({ score }: Props) {
  const details = useMemo(() => toRecord(score.details), [score.details]);
  const sceneDistribution = toRecord(details.scene_distribution);
  const streams = Array.isArray(details.streams_present) ? (details.streams_present as string[]) : [];
  const limitations = Array.isArray(details.limitations) ? (details.limitations as string[]) : [];
  const roadProfile = typeof details.road_profile === "string" ? details.road_profile : "unknown";

  return (
    <section className="card animate-rise p-6 shadow-card">
      <h3 className="font-display text-lg font-semibold text-ink">Model Insights</h3>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <article className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Road Profile</p>
          <p className="mt-2 font-medium text-ink">{roadProfile}</p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Streams Used</p>
          <p className="mt-2 font-medium text-ink">{streams.length ? streams.join(", ") : "unknown"}</p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Scene Distribution</p>
          <p className="mt-2 text-sm text-slate-700">
            day {String(sceneDistribution.day ?? 0)} | dusk {String(sceneDistribution.dusk ?? 0)} | night {String(sceneDistribution.night ?? 0)}
          </p>
        </article>
      </div>

      <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-xs uppercase tracking-wide text-amber-700">Operational Limitations</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
          {limitations.length > 0 ? limitations.map((item, i) => <li key={i}>{item}</li>) : <li>No limitations reported.</li>}
        </ul>
      </div>
    </section>
  );
}
