import { HelpCircle } from "lucide-react";

type Props = {
  overall: number;
  fatigue: number;
  distraction: number;
  lane: number;
  following: number;
};

const SCORE_METADATA: Record<string, { label: string; tooltip: string }> = {
  overall: {
    label: "Overall",
    tooltip:
      "Combined safety score (0–100) averaging fatigue, distraction, lane keeping, and following distance. Higher is better."
  },
  fatigue: {
    label: "Fatigue",
    tooltip:
      "Based on signs of driver fatigue (e.g. PERCLOS, eye closure) and microsleep events. 100 = no issues; lower scores indicate more fatigue-related events."
  },
  distraction: {
    label: "Distraction",
    tooltip:
      "Based on distracted driving, mobile phone use, and seatbelt not worn. 100 = no issues; lower scores indicate more distraction or rule violations."
  },
  lane: {
    label: "Lane",
    tooltip:
      "Based on lane deviation events. 100 = good lane discipline; lower scores indicate more lane departures or drifting."
  },
  following: {
    label: "Following",
    tooltip:
      "Based on tailgating and obstruction-ahead events. 100 = safe following distance; lower scores indicate following too close or obstacles not respected."
  }
};

export default function KPIGrid({ overall, fatigue, distraction, lane, following }: Props) {
  const cards: [string, number][] = [
    ["overall", overall],
    ["fatigue", fatigue],
    ["distraction", distraction],
    ["lane", lane],
    ["following", following]
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map(([key, value], idx) => {
        const meta = SCORE_METADATA[key];
        return (
          <article
            key={key}
            className="card relative z-0 animate-rise p-5 shadow-card transition-shadow hover:z-[50] hover:shadow-card-hover"
            style={{ animationDelay: `${idx * 60}ms` }}
          >
            <div className="flex items-start justify-between gap-1">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                {meta.label} score
              </p>
              <span
                className="group relative inline-flex shrink-0 cursor-help text-slate-400 hover:text-cyan-500 transition-colors"
                aria-label={`More about ${meta.label} score`}
              >
                <HelpCircle className="h-4 w-4" aria-hidden />
                <span
                  role="tooltip"
                  className="pointer-events-none absolute left-1/2 bottom-full z-[100] mb-2 w-64 -translate-x-1/2 origin-bottom scale-95 rounded-xl border border-slate-200/80 bg-white px-4 py-3.5 text-left text-sm leading-relaxed text-slate-600 opacity-0 shadow-[0_4px_20px_rgba(0,0,0,0.08)] transition-all duration-200 group-hover:scale-100 group-hover:opacity-100"
                >
                  <span className="absolute -bottom-1.5 left-1/2 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border-r border-b border-slate-200/80 bg-white" />
                  {meta.tooltip}
                </span>
              </span>
            </div>
            <p className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
              {Number(value).toFixed(1)}
            </p>
          </article>
        );
      })}
    </div>
  );
}
