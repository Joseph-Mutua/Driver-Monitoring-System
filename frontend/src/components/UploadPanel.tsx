import { UploadCloud } from "lucide-react";

type Props = {
  dayFolder: string;
  driverId: string;
  vehicleId: string;
  frontFiles: File[];
  cabinFiles: File[];
  onDayFolder: (value: string) => void;
  onDriverId: (value: string) => void;
  onVehicleId: (value: string) => void;
  onFrontFiles: (files: File[]) => void;
  onCabinFiles: (files: File[]) => void;
  onAnalyze: () => void;
  disabled?: boolean;
};

export default function UploadPanel(props: Props) {
  const {
    dayFolder,
    driverId,
    vehicleId,
    frontFiles,
    cabinFiles,
    onDayFolder,
    onDriverId,
    onVehicleId,
    onFrontFiles,
    onCabinFiles,
    onAnalyze,
    disabled
  } = props;

  return (
    <section className="glass animate-rise rounded-3xl p-6 shadow-glow">
      <div className="mb-4 flex items-center gap-3">
        <UploadCloud className="h-6 w-6 text-cyan" />
        <h2 className="font-display text-2xl font-semibold">Trip Uploader</h2>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <input
          value={dayFolder}
          onChange={(e) => onDayFolder(e.target.value)}
          placeholder="Day folder (e.g. 251101)"
          className="rounded-xl border border-slate-300 bg-white px-4 py-3"
        />
        <input
          value={driverId}
          onChange={(e) => onDriverId(e.target.value)}
          placeholder="Driver ID (optional)"
          className="rounded-xl border border-slate-300 bg-white px-4 py-3"
        />
        <input
          value={vehicleId}
          onChange={(e) => onVehicleId(e.target.value)}
          placeholder="Vehicle ID (optional)"
          className="rounded-xl border border-slate-300 bg-white px-4 py-3"
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <label className="rounded-xl border border-slate-300 bg-white p-4 text-sm">
          <p className="mb-2 font-semibold">Front stream files (mandatory)</p>
          <input type="file" multiple accept=".mp4" onChange={(e) => onFrontFiles(Array.from(e.target.files ?? []))} />
          <p className="mt-2 text-xs text-slate-600">Selected: {frontFiles.length}</p>
        </label>

        <label className="rounded-xl border border-slate-300 bg-white p-4 text-sm">
          <p className="mb-2 font-semibold">Cabin stream files (optional)</p>
          <input type="file" multiple accept=".mp4" onChange={(e) => onCabinFiles(Array.from(e.target.files ?? []))} />
          <p className="mt-2 text-xs text-slate-600">Selected: {cabinFiles.length}</p>
        </label>
      </div>

      <button
        onClick={onAnalyze}
        disabled={disabled || frontFiles.length === 0}
        className="mt-5 rounded-xl bg-ink px-5 py-3 font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-45"
      >
        Upload and Analyze Trip
      </button>
    </section>
  );
}
