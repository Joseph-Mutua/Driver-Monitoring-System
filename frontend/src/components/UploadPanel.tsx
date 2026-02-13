import { UploadCloud } from "lucide-react";

type Props = {
  dayFolder: string;
  driverId: string;
  vehicleId: string;
  frontFiles: File[];
  rearFiles: File[];
  cabinFiles: File[];
  onDayFolder: (value: string) => void;
  onDriverId: (value: string) => void;
  onVehicleId: (value: string) => void;
  onFrontFiles: (files: File[]) => void;
  onRearFiles: (files: File[]) => void;
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
    rearFiles,
    cabinFiles,
    onDayFolder,
    onDriverId,
    onVehicleId,
    onFrontFiles,
    onRearFiles,
    onCabinFiles,
    onAnalyze,
    disabled
  } = props;

  return (
    <section className="card animate-rise p-6 shadow-card">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-soft">
          <UploadCloud className="h-5 w-5 text-cyan-500" />
        </div>
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Trip Uploader</h2>
          <p className="text-xs text-slate-500">Front camera required, rear recommended, cabin optional</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <input
          value={dayFolder}
          onChange={(e) => onDayFolder(e.target.value)}
          placeholder="Day folder (e.g. 251101)"
          className="input"
        />
        <input
          value={driverId}
          onChange={(e) => onDriverId(e.target.value)}
          placeholder="Driver ID (optional)"
          className="input"
        />
        <input
          value={vehicleId}
          onChange={(e) => onVehicleId(e.target.value)}
          placeholder="Vehicle ID (optional)"
          className="input"
        />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <label className="file-block">
          <span className="file-label">Front stream (required)</span>
          <input type="file" multiple accept=".mp4" className="file-input" onChange={(e) => onFrontFiles(Array.from(e.target.files ?? []))} />
          <span className="file-count">{frontFiles.length} file{frontFiles.length !== 1 ? "s" : ""} selected</span>
        </label>
        <label className="file-block">
          <span className="file-label">Rear stream (recommended)</span>
          <input type="file" multiple accept=".mp4" className="file-input" onChange={(e) => onRearFiles(Array.from(e.target.files ?? []))} />
          <span className="file-count">{rearFiles.length} file{rearFiles.length !== 1 ? "s" : ""} selected</span>
        </label>
        <label className="file-block">
          <span className="file-label">Cabin stream (optional, DMS)</span>
          <input type="file" multiple accept=".mp4" className="file-input" onChange={(e) => onCabinFiles(Array.from(e.target.files ?? []))} />
          <span className="file-count">{cabinFiles.length} file{cabinFiles.length !== 1 ? "s" : ""} selected</span>
        </label>
      </div>

      <button
        onClick={onAnalyze}
        disabled={disabled || frontFiles.length === 0}
        className="btn-primary mt-6"
      >
        Upload and Analyze Trip
      </button>
    </section>
  );
}
