import { useMemo, useState } from "react";
import type { MlPipelineJob } from "../types";

type Props = {
  jobs: MlPipelineJob[];
  logs: Record<string, string>;
  busy: boolean;
  onRun: (body: { manifest: string; output_root: string; ground_truth?: string }) => Promise<void>;
  onRefresh: () => Promise<void>;
  onLoadLog: (jobId: string) => Promise<void>;
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
};

function statusColor(status: MlPipelineJob["status"]) {
  if (status === "completed") return "bg-emerald-100 text-emerald-700";
  if (status === "failed") return "bg-rose-100 text-rose-700";
  if (status === "cancelled") return "bg-amber-100 text-amber-700";
  if (status === "running") return "bg-cyan-100 text-cyan-700";
  return "bg-slate-100 text-slate-600";
}

export default function MlTrainingPanel({ jobs, logs, busy, onRun, onRefresh, onLoadLog, onCancel, onRetry }: Props) {
  const [manifest, setManifest] = useState("d:\\WORK\\DMS\\backend\\ml\\data\\manifest.jsonl");
  const [outputRoot, setOutputRoot] = useState("d:\\WORK\\DMS\\backend\\ml\\artifacts\\run_ui");
  const [groundTruth, setGroundTruth] = useState("d:\\WORK\\DMS\\backend\\ml\\data\\ground_truth.json");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const selectedLog = useMemo(() => {
    if (!selectedJobId) return "";
    return logs[selectedJobId] || "";
  }, [logs, selectedJobId]);

  return (
    <section className="card animate-rise p-6 shadow-card">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-lg font-semibold text-ink">Model Training Pipeline</h3>
        <button className="link-pill" onClick={onRefresh}>Refresh Jobs</button>
      </div>

      <p className="mt-1 text-sm text-slate-600">
        Run dataset validation, split generation, detector training, calibration, and acceptance gates.
      </p>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <input className="input" value={manifest} onChange={(e) => setManifest(e.target.value)} placeholder="Manifest path" />
        <input className="input" value={outputRoot} onChange={(e) => setOutputRoot(e.target.value)} placeholder="Output root" />
        <input className="input" value={groundTruth} onChange={(e) => setGroundTruth(e.target.value)} placeholder="Ground truth (optional)" />
      </div>

      <button
        className="btn-primary mt-4"
        disabled={busy || !manifest || !outputRoot}
        onClick={() => onRun({ manifest, output_root: outputRoot, ground_truth: groundTruth || undefined })}
      >
        {busy ? "Starting..." : "Run Training Pipeline"}
      </button>

      <div className="mt-6 overflow-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="px-3 py-3">Job</th>
              <th className="px-3 py-3">Status</th>
              <th className="px-3 py-3">Started</th>
              <th className="px-3 py-3">Artifacts</th>
              <th className="px-3 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {jobs.map((job) => (
              <tr key={job.job_id} className="hover:bg-slate-50/80">
                <td className="px-3 py-3 font-mono text-xs text-slate-700">{job.job_id.slice(0, 8)}...</td>
                <td className="px-3 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(job.status)}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-3 py-3 text-slate-600">{new Date(job.started_at).toLocaleString()}</td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(job.artifact_urls || {}).map(([key, url]) => (
                      <a
                        key={key}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-200"
                        title={job.artifacts?.[key] || key}
                      >
                        download:{key}
                      </a>
                    ))}
                    {job.log_url && <a href={job.log_url} className="link-pill" target="_blank" rel="noreferrer">log file</a>}
                  </div>
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="link-pill"
                      onClick={async () => {
                        setSelectedJobId(job.job_id);
                        await onLoadLog(job.job_id);
                      }}
                    >
                      View Log Tail
                    </button>
                    {(job.status === "queued" || job.status === "running") && (
                      <button className="link-pill" onClick={() => onCancel(job.job_id)}>
                        Cancel
                      </button>
                    )}
                    {(job.status === "failed" || job.status === "cancelled") && (
                      <button className="link-pill" onClick={() => onRetry(job.job_id)}>
                        Retry
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={5}>No training jobs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedJobId && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Log tail ({selectedJobId.slice(0, 8)}...)</p>
          <pre className="max-h-72 overflow-auto rounded-lg border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100">{selectedLog || "No log content"}</pre>
        </div>
      )}
    </section>
  );
}
