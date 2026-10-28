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
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { authedFetch, Business, UnauthenticatedError } from "@/lib/api";
import Spinner, { FullPageSpinner } from "@/components/Spinner";

import IngestPanel from "./IngestPanel";

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

type BacktestRow = {
  product_name: string;
  held_out_period: string;
  predicted_units_sold: number;
  actual_units_sold: number;
  predicted_revenue: number;
  actual_revenue: number;
  error_pct: number;
  is_elasticity_estimated: boolean;
  confidence: "low" | "medium" | "high";
  inflation_pct: number | null;
};

type SeasonalityRow = {
  product_name: string;
  sub_period: string;
  deviation_pct: number;
  periods_used: number;
};

type BenchmarkResponse =
  | { status: "unavailable" }
  | {
      status: "ok";
      industry: string;
      business_margin_pct: number;
      benchmark_low_pct: number;
      benchmark_high_pct: number;
      position: "below" | "within" | "above";
    };

type SingleResult = {
  old_price?: number;
  new_price?: number;
  old_profit: number;
  new_profit: number;
  delta_profit: number;
};

type SweepPoint = { new_price: number; new_profit: number; elasticity_used: number };

type ScenarioResponse =
  | { status: "needs_clarification"; message: string }
  | {
      status: "ok";
      kind: "single";
      lever: string;
      product_name: string;
      result: SingleResult;
      elasticity_used: number | null;
      is_elasticity_estimated: boolean | null;
      confidence: "low" | "medium" | "high" | null;
      narration: string | null;
    }
  | {
      status: "ok";
      kind: "sweep";
      lever: string;
      product_name: string;
      points: SweepPoint[];
      optimum: SweepPoint;
      elasticity_used: number | null;
      is_elasticity_estimated: boolean | null;
      confidence: "low" | "medium" | "high" | null;
      narration: string | null;
    };

function currencyFull(n: number): string {
  return `${n < 0 ? "-" : ""}$${compactNumber(Math.abs(n))}`;
}

function friendlyScenarioError(status: number, detail: string): string {
  if (status === 503) {
    return "The AI model is temporarily unavailable (free-tier models can be rate-limited). Please try again in a moment.";
  }
  return `Something went wrong (${status}). ${detail}`;
}

function BeforeAfterChart({ result }: { result: SingleResult }) {
  const improved = result.delta_profit >= 0;
  const data = [
    { label: "Before", profit: result.old_profit },
    { label: "After", profit: result.new_profit },
  ];
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="0" />
        <XAxis dataKey="label" stroke="var(--axis)" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
        <YAxis stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickFormatter={compactNumber} />
        <Tooltip
          formatter={(value: number) => currencyFull(value)}
          contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--grid)", fontSize: 12 }}
        />
        <Bar dataKey="profit" name="Profit" barSize={48} radius={[4, 4, 0, 0]}>
          <Cell fill="var(--text-muted)" />
          <Cell fill={improved ? "var(--diverging-pos)" : "var(--diverging-neg)"} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function SweepChart({ points, optimum }: { points: SweepPoint[]; optimum: SweepPoint }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={points} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="0" />
        <XAxis
          dataKey="new_price"
          stroke="var(--axis)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          tickFormatter={(v) => `$${compactNumber(v)}`}
        />
        <YAxis stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickFormatter={compactNumber} />
        <Tooltip
          formatter={(value: number) => currencyFull(value)}
          labelFormatter={(label: number) => `Price: $${compactNumber(label)}`}
          contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--grid)", fontSize: 12 }}
        />
        <Line type="monotone" dataKey="new_profit" name="Profit" stroke="var(--series-1)" strokeWidth={2} dot={false} />
        <ReferenceDot
          x={optimum.new_price}
          y={optimum.new_profit}
          r={6}
          fill="var(--diverging-pos)"
          stroke="var(--surface-1)"
          strokeWidth={2}
          label={{ value: "Best", position: "top", fill: "var(--text-secondary)", fontSize: 12 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

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

  const [backtests, setBacktests] = useState<BacktestRow[]>([]);
  const [seasonality, setSeasonality] = useState<SeasonalityRow[]>([]);
  const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);

  const [query, setQuery] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [askResponse, setAskResponse] = useState<ScenarioResponse | null>(null);

  const [showIngest, setShowIngest] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

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
  }, [businessId, refreshKey]);

  useEffect(() => {
    if (!businessId) return;
    let cancelled = false;

    authedFetch(`/dashboard/backtest?business_id=${businessId}`)
      .then(async (res) => {
        if (cancelled || !res.ok) return;
        setBacktests(await res.json());
      })
      .catch(() => {
        if (!cancelled) setBacktests([]);
      });

    return () => {
      cancelled = true;
    };
  }, [businessId, refreshKey]);

  useEffect(() => {
    if (!businessId) return;
    let cancelled = false;

    authedFetch(`/dashboard/seasonality?business_id=${businessId}`)
      .then(async (res) => {
        if (cancelled || !res.ok) return;
        setSeasonality(await res.json());
      })
      .catch(() => {
        if (!cancelled) setSeasonality([]);
      });

    return () => {
      cancelled = true;
    };
  }, [businessId, refreshKey]);

  useEffect(() => {
    if (!businessId) return;
    let cancelled = false;

    authedFetch(`/dashboard/benchmark?business_id=${businessId}`)
      .then(async (res) => {
        if (cancelled || !res.ok) return;
        setBenchmark(await res.json());
      })
      .catch(() => {
        if (!cancelled) setBenchmark(null);
      });

    return () => {
      cancelled = true;
    };
  }, [businessId, refreshKey]);

  const productNames = useMemo(
    () => (summary ? [...new Set(summary.revenue_trend.map((r) => r.product_name))] : []),
    [summary]
  );
  const colorFor = useColorForProduct(productNames);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId || !query.trim()) {
      setAskError("Type a question first.");
      return;
    }
    setAskError(null);
    setAskLoading(true);
    setAskResponse(null);
    try {
      const res = await authedFetch("/scenario/query", {
        method: "POST",
        body: JSON.stringify({ business_id: businessId, query }),
      });
      if (!res.ok) {
        const detail = await res.text();
        setAskError(friendlyScenarioError(res.status, detail));
        return;
      }
      setAskResponse(await res.json());
    } catch (err) {
      if (err instanceof UnauthenticatedError) {
        router.push("/login");
        return;
      }
      setAskError("Could not reach the server. Is the backend running?");
    } finally {
      setAskLoading(false);
    }
  }

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

        {businessId && !showIngest && (
          <button
            onClick={() => setShowIngest(true)}
            className="cursor-pointer self-start rounded border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            + Add data
          </button>
        )}

        {businessId && showIngest && (
          <IngestPanel
            businessId={businessId}
            onSaved={() => setRefreshKey((k) => k + 1)}
            onClose={() => setShowIngest(false)}
          />
        )}

        {loading && (
          <div className="flex flex-col items-center gap-3 py-16">
            <Spinner className="h-8 w-8" />
            <p className="text-sm text-zinc-500">Loading dashboard...</p>
          </div>
        )}

        {summary && !loading && summary.revenue_trend.length === 0 && (
          <p className="text-sm text-zinc-500">
            No financial data yet for this business.{" "}
            <button
              onClick={() => setShowIngest(true)}
              className="cursor-pointer underline hover:text-zinc-800 dark:hover:text-zinc-300"
            >
              Add some
            </button>
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

            {backtests.length > 0 && (
              <ChartCard title="Model accuracy check (predicted vs. actual units sold)">
                <p className="mb-3 text-xs text-[var(--text-muted)]">
                  For each product with a real price change in its history, the model was given only the data
                  before that change and asked to predict what happened next — here&apos;s how close it got.
                </p>
                <ResponsiveContainer width="100%" height={Math.max(140, backtests.length * 56)}>
                  <BarChart
                    data={backtests}
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
                    <Tooltip content={<LineKeyTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)" }} iconType="plainline" />
                    <Bar dataKey="actual_units_sold" name="Actual" fill="var(--text-muted)" barSize={16} radius={[0, 4, 4, 0]} />
                    <Bar dataKey="predicted_units_sold" name="Predicted" fill="var(--series-1)" barSize={16} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <ul className="mt-3 flex flex-col gap-1">
                  {backtests.map((row) => (
                    <li key={row.product_name} className="text-xs text-[var(--text-muted)]">
                      {row.product_name} ({row.held_out_period}): off by {Math.abs(row.error_pct * 100).toFixed(0)}%
                      &middot; {row.confidence} confidence
                      {row.inflation_pct !== null && (
                        <> &middot; general inflation over this window: {(row.inflation_pct * 100).toFixed(1)}%</>
                      )}
                    </li>
                  ))}
                </ul>
              </ChartCard>
            )}

            {seasonality.length > 0 && (
              <ChartCard title="Seasonal patterns">
                <p className="mb-3 text-xs text-[var(--text-muted)]">
                  Based on this product&apos;s own history across years, not a general industry claim.
                </p>
                <ul className="flex flex-col gap-2">
                  {seasonality.map((row) => {
                    const up = row.deviation_pct > 0;
                    return (
                      <li
                        key={`${row.product_name}-${row.sub_period}`}
                        className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
                      >
                        <span className="text-[var(--text-secondary)]">
                          {row.product_name} &middot; {row.sub_period}
                        </span>
                        <span
                          className={
                            "font-semibold " +
                            (up ? "text-[var(--diverging-pos)]" : "text-[var(--diverging-neg)]")
                          }
                        >
                          {up ? "+" : ""}
                          {(row.deviation_pct * 100).toFixed(0)}% vs. average
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </ChartCard>
            )}

            {benchmark?.status === "ok" && (
              <ChartCard title={`Industry benchmark — ${benchmark.industry}`}>
                <p className="mb-3 text-xs text-[var(--text-muted)]">
                  Rough general reference based on your inferred industry, not live market data.
                </p>
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-semibold text-[var(--text-primary)]">
                    {benchmark.business_margin_pct.toFixed(1)}%
                  </span>
                  <span className="text-sm text-[var(--text-secondary)]">
                    your margin &middot; typical {benchmark.benchmark_low_pct.toFixed(0)}–
                    {benchmark.benchmark_high_pct.toFixed(0)}%
                  </span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                  <div
                    className={
                      "h-full " +
                      (benchmark.position === "within"
                        ? "bg-[var(--diverging-pos)]"
                        : "bg-[var(--diverging-neg)]")
                    }
                    style={{
                      width: `${Math.max(4, Math.min(100, (benchmark.business_margin_pct / benchmark.benchmark_high_pct) * 100))}%`,
                    }}
                  />
                </div>
                <p className="mt-2 text-xs text-[var(--text-secondary)]">
                  {benchmark.position === "within" &&
                    "Your margin falls within the typical range for this industry."}
                  {benchmark.position === "below" &&
                    "Your margin is below the typical range for this industry."}
                  {benchmark.position === "above" &&
                    "Your margin is above the typical range for this industry."}
                </p>
              </ChartCard>
            )}

            <div className="rounded-xl border border-zinc-200 bg-[var(--surface-1)] p-5 shadow-sm dark:border-zinc-800">
              <h2 className="mb-3 text-sm font-semibold text-[var(--text-secondary)]">What-if</h2>
              <form onSubmit={handleAsk} className="flex gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. What if I raise the price of Widget by 10%?"
                  className="flex-1 rounded border border-zinc-300 px-3 py-2 text-sm transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-600 dark:focus:ring-white/10"
                />
                <button
                  type="submit"
                  disabled={askLoading}
                  className="cursor-pointer rounded bg-black px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:active:bg-zinc-300"
                >
                  {askLoading ? "Thinking..." : "Ask"}
                </button>
              </form>

              {askError && (
                <p className="mt-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
                  {askError}
                </p>
              )}

              {askResponse?.status === "needs_clarification" && (
                <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
                  {askResponse.message}
                </p>
              )}

              {askResponse?.status === "ok" && (
                <div className="mt-4 flex flex-col gap-3">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--text-secondary)]">
                    {askResponse.product_name} &middot; {askResponse.lever === "price" ? "Price change" : "Sourcing change"}
                    {askResponse.confidence && (
                      <span
                        className={
                          "rounded-full px-2 py-0.5 text-xs font-normal " +
                          (askResponse.confidence === "high"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                            : askResponse.confidence === "medium"
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300"
                            : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400")
                        }
                      >
                        {askResponse.confidence} confidence
                      </span>
                    )}
                  </h3>

                  {askResponse.kind === "single" && <BeforeAfterChart result={askResponse.result} />}
                  {askResponse.kind === "sweep" && (
                    <SweepChart points={askResponse.points} optimum={askResponse.optimum} />
                  )}

                  {askResponse.narration && (
                    <p className="text-sm text-[var(--text-secondary)]">{askResponse.narration}</p>
                  )}

                  {askResponse.is_elasticity_estimated === false && (
                    <p className="text-xs text-[var(--text-muted)]">
                      Note: not enough price history to estimate this product&apos;s own demand sensitivity, so a
                      default assumption was used instead.
                    </p>
                  )}
                </div>
              )}
            </div>
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
    <Suspense fallback={<FullPageSpinner />}>
      <DashboardInner />
    </Suspense>
  );
}
