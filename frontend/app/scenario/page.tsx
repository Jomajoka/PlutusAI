"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { authedFetch, Business, UnauthenticatedError } from "@/lib/api";

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
      narration: string | null;
    };

function compactNumber(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(abs < 10 ? 2 : 0);
}

function currency(n: number): string {
  return `${n < 0 ? "-" : ""}$${compactNumber(Math.abs(n))}`;
}

function friendlyError(status: number, detail: string): string {
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
    <div className="viz-root">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" strokeDasharray="0" />
          <XAxis dataKey="label" stroke="var(--axis)" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
          <YAxis stroke="var(--axis)" tick={{ fill: "var(--text-muted)", fontSize: 12 }} tickFormatter={compactNumber} />
          <Tooltip
            formatter={(value: number) => currency(value)}
            contentStyle={{ background: "var(--surface-1)", border: "1px solid var(--grid)", fontSize: 12 }}
          />
          <Bar dataKey="profit" name="Profit" barSize={48} radius={[4, 4, 0, 0]}>
            <Cell fill="var(--text-muted)" />
            <Cell fill={improved ? "var(--diverging-pos)" : "var(--diverging-neg)"} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <style jsx global>{`
        .viz-root {
          --surface-1: #ffffff;
          --text-secondary: #52514e;
          --text-muted: #898781;
          --grid: #e1e0d9;
          --axis: #c3c2b7;
          --series-1: #2a78d6;
          --diverging-pos: #2a78d6;
          --diverging-neg: #e34948;
        }
        @media (prefers-color-scheme: dark) {
          .viz-root {
            --surface-1: #18181b;
            --text-secondary: #c3c2b7;
            --text-muted: #898781;
            --grid: #2c2c2a;
            --axis: #383835;
            --series-1: #3987e5;
            --diverging-pos: #3987e5;
            --diverging-neg: #e66767;
          }
        }
      `}</style>
    </div>
  );
}

function SweepChart({ points, optimum }: { points: SweepPoint[]; optimum: SweepPoint }) {
  return (
    <div className="viz-root">
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
            formatter={(value: number) => currency(value)}
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
      <style jsx global>{`
        .viz-root {
          --surface-1: #ffffff;
          --text-secondary: #52514e;
          --text-muted: #898781;
          --grid: #e1e0d9;
          --axis: #c3c2b7;
          --series-1: #2a78d6;
          --diverging-pos: #2a78d6;
        }
        @media (prefers-color-scheme: dark) {
          .viz-root {
            --surface-1: #18181b;
            --text-secondary: #c3c2b7;
            --text-muted: #898781;
            --grid: #2c2c2a;
            --axis: #383835;
            --series-1: #3987e5;
            --diverging-pos: #3987e5;
          }
        }
      `}</style>
    </div>
  );
}

function ScenarioInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState<string>(searchParams.get("business") ?? "");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ScenarioResponse | null>(null);

  useEffect(() => {
    authedFetch("/businesses")
      .then(async (res) => {
        if (res.ok) setBusinesses(await res.json());
      })
      .catch((err) => {
        if (err instanceof UnauthenticatedError) router.push("/login");
      });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId || !query.trim()) {
      setError("Choose a business and type a question first.");
      return;
    }
    setError(null);
    setLoading(true);
    setResponse(null);
    try {
      const res = await authedFetch("/scenario/query", {
        method: "POST",
        body: JSON.stringify({ business_id: businessId, query }),
      });
      if (!res.ok) {
        const detail = await res.text();
        setError(friendlyError(res.status, detail));
        return;
      }
      setResponse(await res.json());
    } catch (err) {
      if (err instanceof UnauthenticatedError) {
        router.push("/login");
        return;
      }
      setError("Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 p-6 font-sans dark:bg-black sm:p-10">
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-black dark:text-zinc-50">What-if scenarios</h1>
            <p className="text-sm text-zinc-500">Ask about a price or sourcing change and see the simulated impact.</p>
          </div>
          <Link href="/businesses" className="text-sm text-zinc-500 underline transition-colors hover:text-zinc-800 dark:hover:text-zinc-300">
            Back
          </Link>
        </header>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
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
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What if I raise the price of Widget by 10%?"
              className="flex-1 rounded border border-zinc-300 px-3 py-2 text-sm transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-600 dark:focus:ring-white/10"
            />
            <button
              type="submit"
              disabled={loading}
              className="cursor-pointer rounded bg-black px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:active:bg-zinc-300"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </div>
        </form>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {response?.status === "needs_clarification" && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
            {response.message}
          </div>
        )}

        {response?.status === "ok" && (
          <div className="flex flex-col gap-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
              {response.product_name} &middot; {response.lever === "price" ? "Price change" : "Sourcing change"}
            </h2>

            {response.kind === "single" && <BeforeAfterChart result={response.result} />}
            {response.kind === "sweep" && <SweepChart points={response.points} optimum={response.optimum} />}

            {response.narration && (
              <p className="text-sm text-zinc-600 dark:text-zinc-400">{response.narration}</p>
            )}

            {response.is_elasticity_estimated === false && (
              <p className="text-xs text-zinc-400">
                Note: not enough price history to estimate this product&apos;s own demand sensitivity, so a default
                assumption was used instead.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ScenarioPage() {
  return (
    <Suspense>
      <ScenarioInner />
    </Suspense>
  );
}
