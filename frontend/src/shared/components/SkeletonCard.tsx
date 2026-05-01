export default function SkeletonCard() {
  return (
    <div className="snap-card rounded-lg border border-sf-line bg-white p-2 shadow-sm">
      <div className="mb-2 aspect-square animate-pulse rounded-md bg-slate-100" />
      <div className="mb-2 h-3 w-4/5 animate-pulse rounded bg-slate-100" />
      <div className="h-3 w-1/2 animate-pulse rounded bg-slate-100" />
    </div>
  );
}
