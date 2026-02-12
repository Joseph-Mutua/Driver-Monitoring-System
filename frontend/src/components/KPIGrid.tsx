type Props = {
  overall: number;
  fatigue: number;
  distraction: number;
  lane: number;
  following: number;
};

export default function KPIGrid({ overall, fatigue, distraction, lane, following }: Props) {
  const cards = [
    ["Overall", overall],
    ["Fatigue", fatigue],
    ["Distraction", distraction],
    ["Lane", lane],
    ["Following", following]
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map(([label, value], idx) => (
        <article
          key={label}
          className="card animate-rise p-5 shadow-card transition-shadow hover:shadow-card-hover"
          style={{ animationDelay: `${idx * 60}ms` }}
        >
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label} score</p>
          <p className="mt-2 font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">
            {Number(value).toFixed(1)}
          </p>
        </article>
      ))}
    </div>
  );
}
