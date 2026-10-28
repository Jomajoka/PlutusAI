"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { authedFetch, Business, UnauthenticatedError } from "@/lib/api";

type Kpis = { total_revenue: number; total_units_sold: number; total_margin: number };
type TrendPoint = { period: string; product_name: string; revenue: number };
type MixRow = { product_name: string; revenue: number };
type MarginRow = { product_name: string; margin: number };

type DashboardSummary = {
  kpis: Kpis;
  revenue_trend: TrendPoint[];
  product_mix: MixRow[];
  margin_by_product: MarginRow[];
};

// Fixed categorical order -- validated for CVD-safe adjacent contrast. Never
// cycled or reassigned per-filter; the same product keeps the same color in
// every chart on this page.
const CATEGORICAL_SLOTS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
];
const MAX_SERIES = CATEGORICAL_SLOTS.length;

function compactNumber(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(abs < 10 ? 2 : 0);
}

function currency(n: number): string {
  return `$${compactNumber(n)}`;
}

function useColorForProduct(names: string[]) {
  return useMemo(() => {
    const sorted = [...new Set(names)].sort();
    const map = new Map<string, string>();
    sorted.forEach((name, i) => {
      map.set(name, i < MAX_SERIES ? CATEGORICAL_SLOTS[i] : "var(--text-muted)");
    });
    return map;
  }, [names]);
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="viz-root flex-1 rounded-xl border border-zinc-200 bg-[var(--surface-1)] p-5 shadow-sm dark:border-zinc-800">
      <p className="text-sm text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="viz-root rounded-xl border border-zinc-200 bg-[var(--surface-1)] p-5 shadow-sm dark:border-zinc-800">
      <h2 className="mb-4 text-sm font-semibold text-[var(--text-secondary)]">{title}</h2>
      {children}
    </div>
  );
}

type TooltipEntry = { name?: string; value?: number; color?: string };

function LineKeyTooltip({
  active,
  payload,
  label,
  valuePrefix = "",
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
  valuePrefix?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-zinc-200 bg-[var(--surface-1)] px-3 py-2 text-xs shadow-md dark:border-zinc-700">
      <p className="mb-1 font-medium text-[var(--text-secondary)]">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="inline-block h-[2px] w-3"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-[var(--text-secondary)]">{entry.name}:</span>
          <span className="font-semibold text-[var(--text-primary)]">
            {valuePrefix}
            {compactNumber(entry.value ?? 0)}
          </span>
        </div>
      ))}
    </div>
  );
}

function DashboardInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState<string>(searchParams.get("business") ?? "");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [summaryBusinessId, setSummaryBusinessId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loading = businessId !== "" && summaryBusinessId !== businessId && !error;

  useEffect(() => {
    authedFetch("/businesses")
      .then(async (res) => {
        if (res.ok) setBusinesses(await res.json());
      })
      .catch((err) => {
        if (err instanceof UnauthenticatedError) router.push("/login");
      });
  }, []);

  useEffect(() => {
    if (!businessId) return;
    let cancelled = false;

    authedFetch(`/dashboard/summary?business_id=${businessId}`)
      .then(async (res) => {
        if (cancelled) return;
        if (!res.ok) {
          setError(`Failed to load dashboard (${res.status})`);
          setSummaryBusinessId(businessId);
          return;
        }
        setSummary(await res.json());
        setSummaryBusinessId(businessId);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthenticatedError) {
          router.push("/login");
          return;
        }
        setError("Could not reach the server. Is the backend running?");
        setSummaryBusinessId(businessId);
      });

    return () => {
      cancelled = true;
    };
  }, [businessId]);

  const productNames = useMemo(
    () => (summary ? [...new Set(summary.revenue_trend.map((r) => r.product_name))] : []),
    [summary]
  );
  const colorFor = useColorForProduct(productNames);

  const trendByPeriod = useMemo(() => {
    if (!summary) return [];
    const rows = new Map<string, Record<string, string | number>>();
    for (const point of summary.revenue_trend) {
      const row = rows.get(point.period) ?? { period: point.period };
      row[point.product_name] = point.revenue;
      rows.set(point.period, row);
    }
    return [...rows.values()];
  }, [summary]);

  return (
    <div className="min-h-screen bg-zinc-50 p-6 font-sans dark:bg-black sm:p-10">
      <div className="mx-auto flex max-w-4xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-black dark:text-zinc-50">Dashboard</h1>
            <p className="text-sm text-zinc-500">Revenue, product mix, and margin from your saved data.</p>
          </div>
          <Link
            href="/businesses"
            className="text-sm text-zinc-500 underline transition-colors hover:text-zinc-800 dark:hover:text-zinc-300"
          >
            Back
          </Link>
        </header>

        <select
          value={businessId}
          onChange={(e) => setBusinessId(e.target.value)}
          className="cursor-pointer self-start rounded border border-zinc-300 bg-white px-3 py-2 text-sm transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-600 dark:focus:ring-white/10"
        >
          <option value="" disabled>
            Select a business
          </option>
          {businesses.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {!businessId && !error && (
          <p className="text-sm text-zinc-500">Choose a business above to see its dashboard.</p>
        )}

        {loading && <p className="text-sm text-zinc-500">Loading...</p>}

        {summary && !loading && summary.revenue_trend.length === 0 && (
          <p className="text-sm text-zinc-500">
            No financial data yet for this business.{" "}
            <Link href={`/ingest?business=${businessId}`} className="underline hover:text-zinc-800 dark:hover:text-zinc-300">
              Add some
            </Link>
            .
          </p>
        )}

        {summary && summary.revenue_trend.length > 0 && (
          <div className="viz-root flex flex-col gap-6">
            <div className="flex gap-4">
              <StatTile label="Total revenue" value={currency(summary.kpis.total_revenue)} />
              <StatTile label="Units sold" value={compactNumber(summary.kpis.total_units_sold)} />
              <StatTile label="Total margin" value={currency(summary.kpis.total_margin)} />
            </div>

            <ChartCard title="Revenue over time">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={trendByPeriod} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="0" />
                  <XAxis dataKey="period" stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                  <YAxis
                    stroke="var(--axis)"
                    tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                    tickFormatter={compactNumber}
                  />
                  <Tooltip content={<LineKeyTooltip valuePrefix="$" />} />
                  {productNames.length >= 2 && (
                    <Legend
                      wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }}
                      iconType="plainline"
                    />
                  )}
                  {productNames.map((name) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      name={name}
                      stroke={colorFor.get(name)}
                      strokeWidth={2}
                      dot={{ r: 4, strokeWidth: 0, fill: colorFor.get(name) }}
                      activeDot={{ r: 5 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Revenue by product">
              <ResponsiveContainer width="100%" height={Math.max(120, summary.product_mix.length * 44)}>
                <BarChart
                  data={summary.product_mix}
                  layout="vertical"
                  margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
                >
                  <CartesianGrid horizontal={false} stroke="var(--grid)" strokeDasharray="0" />
                  <XAxis
                    type="number"
                    stroke="var(--axis)"
                    tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                    tickFormatter={compactNumber}
                  />
                  <YAxis
                    type="category"
                    dataKey="product_name"
                    stroke="var(--axis)"
                    tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
                    width={90}
                  />
                  <Tooltip content={<LineKeyTooltip valuePrefix="$" />} />
                  <Bar dataKey="revenue" name="Revenue" barSize={20} radius={[0, 4, 4, 0]}>
                    {summary.product_mix.map((row) => (
                      <Cell key={row.product_name} fill={colorFor.get(row.product_name)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Margin by product (revenue − cost)">
              <ResponsiveContainer width="100%" height={Math.max(120, summary.margin_by_product.length * 44)}>
                <BarChart
                  data={summary.margin_by_product}
                  layout="vertical"
                  margin={{ top: 0, right: 24, bottom: 0, left: 0 }}
                >
                  <CartesianGrid horizontal={false} stroke="var(--grid)" strokeDasharray="0" />
                  <XAxis
                    type="number"
                    stroke="var(--axis)"
                    tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                    tickFormatter={compactNumber}
                  />
                  <YAxis
                    type="category"
                    dataKey="product_name"
                    stroke="var(--axis)"
                    tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
                    width={90}
                  />
                  <ReferenceLine x={0} stroke="var(--baseline)" />
                  <Tooltip content={<LineKeyTooltip valuePrefix="$" />} />
                  <Bar dataKey="margin" name="Margin" barSize={20} radius={[0, 4, 4, 0]}>
                    {summary.margin_by_product.map((row) => (
                      <Cell
                        key={row.product_name}
                        fill={row.margin >= 0 ? "var(--diverging-pos)" : "var(--diverging-neg)"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        )}
      </div>

      <style jsx global>{`
        .viz-root {
          --surface-1: #ffffff;
          --text-primary: #0b0b0b;
          --text-secondary: #52514e;
          --text-muted: #898781;
          --grid: #e1e0d9;
          --axis: #c3c2b7;
          --baseline: #898781;
          --series-1: #2a78d6;
          --series-2: #eb6834;
          --series-3: #1baf7a;
          --series-4: #eda100;
          --series-5: #e87ba4;
          --series-6: #008300;
          --series-7: #6250d6;
          --series-8: #e34948;
          --diverging-pos: #2a78d6;
          --diverging-neg: #e34948;
        }
        @media (prefers-color-scheme: dark) {
          .viz-root {
            --surface-1: #18181b;
            --text-primary: #f0efec;
            --text-secondary: #c3c2b7;
            --text-muted: #898781;
            --grid: #2c2c2a;
            --axis: #383835;
            --baseline: #52514e;
            --series-1: #3987e5;
            --series-2: #d95926;
            --series-3: #199e70;
            --series-4: #c98500;
            --series-5: #d55181;
            --series-6: #008300;
            --series-7: #9085e9;
            --series-8: #e66767;
            --diverging-pos: #3987e5;
            --diverging-neg: #e66767;
          }
        }
      `}</style>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense>
      <DashboardInner />
    </Suspense>
  );
}
