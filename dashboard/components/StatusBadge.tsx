export default function StatusBadge({ status }: { status: string }) {
  const color: Record<string,string> = {
    NEW: 'bg-slate-200 text-slate-800',
    SPEC_READY: 'bg-blue-100 text-blue-800',
    RUNNING: 'bg-amber-100 text-amber-800',
    PASSED: 'bg-green-100 text-green-800',
    FAILED: 'bg-red-100 text-red-800',
    UNKNOWN: 'bg-gray-200 text-gray-800'
  };
  return <span className={`px-2 py-1 rounded text-xs font-medium ${color[status] || color.UNKNOWN}`}>{status}</span>;
}
