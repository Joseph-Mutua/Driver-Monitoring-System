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
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {cards.map(([label, value], idx) => (
        <article key={label} className="glass animate-rise rounded-2xl p-5 shadow-glow" style={{ animationDelay: `${idx * 70}ms` }}>
          <p className="text-sm text-slate-600">{label} Score</p>
          <p className="mt-2 font-display text-3xl font-bold">{Number(value).toFixed(1)}</p>
        </article>
      ))}
    </div>
  );
}
