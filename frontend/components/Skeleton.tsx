export function Skeleton({
  className = "",
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return <div className={`animate-pulse rounded bg-zinc-200 dark:bg-zinc-800 ${className}`} style={style} />;
}

export function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex gap-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="flex-1 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
          >
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="mt-3 h-7 w-24" />
          </div>
        ))}
      </div>

      {[280, 160, 160].map((height, i) => (
        <div
          key={i}
          className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
        >
          <Skeleton className="mb-4 h-3.5 w-36" />
          <Skeleton className="w-full" style={{ height }} />
        </div>
      ))}
    </div>
  );
}
