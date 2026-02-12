import { useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Trash2, X } from "lucide-react";
import { bulkDeleteTrips } from "../services/api";
import type { Trip } from "../types";

type Props = {
  trips: Trip[];
  onOpen: (tripId: string) => void;
  onDeleted?: (deletedIds: string[]) => void;
};

export default function ClipSummaries({ trips, onOpen, onDeleted }: Props) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [pendingDeleteIds, setPendingDeleteIds] = useState<string[] | null>(null);

  const allIds = trips.map((t) => t.id);
  const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));

  function toggleOne(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) setSelectedIds(new Set());
    else setSelectedIds(new Set(allIds));
  }

  function openDeleteModal(ids: string[]) {
    if (ids.length === 0) return;
    setPendingDeleteIds(ids);
  }

  function closeDeleteModal() {
    setPendingDeleteIds(null);
  }

  async function confirmDelete() {
    if (!pendingDeleteIds || pendingDeleteIds.length === 0) return;
    setDeleting(true);
    try {
      const res = await bulkDeleteTrips(pendingDeleteIds);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        pendingDeleteIds.forEach((id) => next.delete(id));
        return next;
      });
      if (res.failed.length > 0 && res.deleted.length === 0) {
        console.error("Delete failed:", res.failed);
      }
      if (res.deleted.length > 0) onDeleted?.(res.deleted);
      closeDeleteModal();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="card animate-rise overflow-hidden p-6 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h3 className="font-display text-lg font-semibold text-ink">Trip History</h3>
        {selectedIds.size > 0 && (
          <button
            type="button"
            onClick={() => openDeleteModal(Array.from(selectedIds))}
            disabled={deleting}
            className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-700 transition hover:bg-rose-100 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            Delete selected ({selectedIds.size})
          </button>
        )}
      </div>
      <div className="mt-4 overflow-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50/95 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th className="w-10 px-2 py-3">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                  className="h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                  aria-label="Select all trips"
                />
              </th>
              <th className="px-4 py-3">Trip ID</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Driver</th>
              <th className="px-4 py-3">Vehicle</th>
              <th className="px-4 py-3">Duration</th>
              <th className="px-4 py-3">Action</th>
              <th className="w-10 px-2 py-3" aria-label="Delete column" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {trips.map((trip) => (
              <tr key={trip.id} className="transition-colors hover:bg-slate-50/80">
                <td className="px-2 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(trip.id)}
                    onChange={() => toggleOne(trip.id)}
                    className="h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                    aria-label={`Select trip ${trip.id.slice(0, 8)}`}
                  />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{trip.id.slice(0, 8)}…</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      trip.status === "done"
                        ? "bg-emerald-100 text-emerald-700"
                        : trip.status === "failed"
                          ? "bg-rose-100 text-rose-700"
                          : trip.status === "processing"
                            ? "bg-cyan-100 text-cyan-700"
                            : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {trip.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{trip.driver_id || "—"}</td>
                <td className="px-4 py-3 text-slate-600">{trip.vehicle_id || "—"}</td>
                <td className="px-4 py-3 tabular-nums text-slate-600">{trip.duration_seconds.toFixed(1)}s</td>
                <td className="px-4 py-3">
                  <button onClick={() => onOpen(trip.id)} className="link-pill">
                    Open
                  </button>
                </td>
                <td className="px-2 py-3">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openDeleteModal([trip.id]);
                    }}
                    disabled={deleting}
                    className="rounded p-1.5 text-red-600 transition hover:bg-red-50 hover:text-red-700 disabled:opacity-50"
                    title="Delete this trip"
                    aria-label={`Delete trip ${trip.id.slice(0, 8)}`}
                  >
                    <Trash2 className="h-4 w-4 shrink-0 text-red-600" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pendingDeleteIds !== null &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-500/60 p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-modal-title"
            onClick={() => !deleting && closeDeleteModal()}
          >
            <div
              className="relative w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={closeDeleteModal}
                disabled={deleting}
                className="absolute right-4 top-4 rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>

              <div className="flex gap-4 pr-8">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-100">
                  <AlertTriangle className="h-6 w-6 text-rose-600" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <h4 id="delete-modal-title" className="font-display text-lg font-semibold text-ink">
                    Delete trip{pendingDeleteIds.length > 1 ? "s" : ""}?
                  </h4>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    Are you sure you want to delete the selected trip{pendingDeleteIds.length > 1 ? "s" : ""}? All
                    associated data will be permanently removed from the server. This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  disabled={deleting}
                  className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmDelete}
                  disabled={deleting}
                  className="rounded-lg bg-rose px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
                >
                  {deleting ? "Deleting…" : "Delete"}
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </section>
  );
}
