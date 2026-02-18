'use client';

export default function ConfirmModal({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  loading
}: {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-4 space-y-3">
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-slate-600">{message}</p>
        <div className="flex justify-end gap-2">
          <button className="border px-3 py-2 rounded" onClick={onCancel} disabled={loading}>Cancel</button>
          <button className="bg-red-600 text-white px-3 py-2 rounded disabled:opacity-60" onClick={onConfirm} disabled={loading}>
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
