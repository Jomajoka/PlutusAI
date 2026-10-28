"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { authedFetch, Business, UnauthenticatedError } from "@/lib/api";

type PreviewRecord = {
  field: string;
  value: number;
  product_name: string;
  period: string | null;
  source_line: string;
  verified: boolean;
};

type PreviewNote = { category: string | null; text: string };

type PreviewResponse = {
  records: PreviewRecord[];
  unverified_records: PreviewRecord[];
  notes: PreviewNote[];
};

type EditableRecord = PreviewRecord & { included: boolean };
type EditableNote = PreviewNote & { included: boolean };

const FIELD_LABELS: Record<string, string> = {
  revenue: "Revenue",
  cost: "Cost",
  units_sold: "Units sold",
  unit_price: "Unit price",
};

type Step = "input" | "review" | "done";

function IngestPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [businessId, setBusinessId] = useState<string>(searchParams.get("business") ?? "");
  const [mode, setMode] = useState<"text" | "pdf">("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const [step, setStep] = useState<Step>("input");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [records, setRecords] = useState<EditableRecord[]>([]);
  const [notes, setNotes] = useState<EditableNote[]>([]);
  const [savedCounts, setSavedCounts] = useState<{ rows: number; notes: number } | null>(null);

  useEffect(() => {
    authedFetch("/businesses")
      .then(async (res) => {
        if (res.ok) setBusinesses(await res.json());
      })
      .catch((err) => {
        if (err instanceof UnauthenticatedError) router.push("/login");
      });
  }, []);

  function friendlyError(status: number, detail: string): string {
    if (status === 503) {
      return "The AI model is temporarily unavailable (free-tier models can be rate-limited). Please try again in a moment.";
    }
    if (status === 400) {
      return `Could not read that file: ${detail}`;
    }
    return `Something went wrong (${status}). ${detail}`;
  }

  async function handlePreview(e: React.FormEvent) {
    e.preventDefault();
    if (!businessId) {
      setError("Choose a business first.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      let res: Response;
      if (mode === "text") {
        if (!text.trim()) {
          setError("Paste some text first.");
          setLoading(false);
          return;
        }
        res = await authedFetch("/ingest/text/preview", {
          method: "POST",
          body: JSON.stringify({ business_id: businessId, text }),
        });
      } else {
        if (!file) {
          setError("Choose a PDF file first.");
          setLoading(false);
          return;
        }
        const form = new FormData();
        form.append("business_id", businessId);
        form.append("file", file);
        res = await authedFetch("/ingest/pdf/preview", { method: "POST", body: form });
      }

      if (!res.ok) {
        const detail = await res.text();
        setError(friendlyError(res.status, detail));
        setLoading(false);
        return;
      }

      const data: PreviewResponse = await res.json();
      const allRecords: EditableRecord[] = [
        ...data.records.map((r) => ({ ...r, included: true })),
        ...data.unverified_records.map((r) => ({ ...r, included: false })),
      ];
      if (allRecords.length === 0) {
        setError("No financial figures were found in that input. Try pasting more detail, or a different page/section.");
        setLoading(false);
        return;
      }
      setRecords(allRecords);
      setNotes(data.notes.map((n) => ({ ...n, included: true })));
      setStep("review");
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

  function updateRecord(index: number, patch: Partial<EditableRecord>) {
    setRecords((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function updateNote(index: number, patch: Partial<EditableNote>) {
    setNotes((prev) => prev.map((n, i) => (i === index ? { ...n, ...patch } : n)));
  }

  async function handleConfirm() {
    setError(null);
    setLoading(true);
    try {
      const res = await authedFetch("/ingest/text/confirm", {
        method: "POST",
        body: JSON.stringify({
          business_id: businessId,
          records: records
            .filter((r) => r.included)
            .map((r) => ({
              field: r.field,
              value: r.value,
              product_name: r.product_name,
              period: r.period,
            })),
          notes: notes
            .filter((n) => n.included)
            .map((n) => ({ category: n.category, text: n.text })),
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        setError(friendlyError(res.status, detail));
        setLoading(false);
        return;
      }
      const result = await res.json();
      setSavedCounts({ rows: result.saved_financial_rows, notes: result.saved_notes });
      setStep("done");
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

  function startOver() {
    setStep("input");
    setText("");
    setFile(null);
    setRecords([]);
    setNotes([]);
    setSavedCounts(null);
    setError(null);
  }

  const includedCount = records.filter((r) => r.included).length;

  return (
    <div className="min-h-screen bg-zinc-50 p-6 font-sans dark:bg-black sm:p-10">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-black dark:text-zinc-50">Add business data</h1>
            <p className="text-sm text-zinc-500">Paste text or upload a PDF — we&apos;ll extract the numbers for you to confirm.</p>
          </div>
          <Link href="/businesses" className="text-sm text-zinc-500 underline hover:text-zinc-800 dark:hover:text-zinc-300">
            Back
          </Link>
        </header>

        <ol className="flex gap-2 text-xs font-medium text-zinc-500">
          {(["input", "review", "done"] as Step[]).map((s, i) => (
            <li
              key={s}
              className={`flex items-center gap-2 rounded-full px-3 py-1 ${
                step === s
                  ? "bg-black text-white dark:bg-white dark:text-black"
                  : "bg-zinc-200 dark:bg-zinc-800"
              }`}
            >
              {i + 1}. {s === "input" ? "Input" : s === "review" ? "Review" : "Done"}
            </li>
          ))}
        </ol>

        {error && (
          <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {step === "input" && (
          <form onSubmit={handlePreview} className="flex flex-col gap-5 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Business</label>
              <select
                value={businessId}
                onChange={(e) => setBusinessId(e.target.value)}
                className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                required
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
            </div>

            <div className="flex gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800">
              {(["text", "pdf"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    mode === m
                      ? "bg-white text-black shadow-sm dark:bg-zinc-950 dark:text-white"
                      : "text-zinc-500"
                  }`}
                >
                  {m === "text" ? "Paste text" : "Upload PDF"}
                </button>
              ))}
            </div>

            {mode === "text" ? (
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste quarterly results, a product report, or any text with financial figures..."
                rows={10}
                className="resize-y rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
              />
            ) : (
              <input
                type="file"
                accept="application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="rounded border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
              />
            )}

            <button
              type="submit"
              disabled={loading}
              className="self-start rounded bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
            >
              {loading ? "Extracting..." : "Preview extracted data"}
            </button>
          </form>
        )}

        {step === "review" && (
          <div className="flex flex-col gap-5">
            <div className="rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex items-center justify-between border-b border-zinc-200 px-5 py-3 dark:border-zinc-800">
                <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                  Extracted records ({includedCount} of {records.length} selected)
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 text-left text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800">
                      <th className="px-4 py-2"></th>
                      <th className="px-4 py-2">Field</th>
                      <th className="px-4 py-2">Value</th>
                      <th className="px-4 py-2">Product</th>
                      <th className="px-4 py-2">Period</th>
                      <th className="px-4 py-2">Source</th>
                      <th className="px-4 py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r, i) => (
                      <tr
                        key={i}
                        className={`border-b border-zinc-100 align-top dark:border-zinc-800 ${
                          r.included ? "" : "opacity-50"
                        }`}
                      >
                        <td className="px-4 py-2">
                          <input
                            type="checkbox"
                            checked={r.included}
                            onChange={(e) => updateRecord(i, { included: e.target.checked })}
                          />
                        </td>
                        <td className="px-4 py-2 whitespace-nowrap">{FIELD_LABELS[r.field] ?? r.field}</td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={r.value}
                            onChange={(e) => updateRecord(i, { value: parseFloat(e.target.value) })}
                            className="w-28 rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            value={r.product_name}
                            onChange={(e) => updateRecord(i, { product_name: e.target.value })}
                            className="w-28 rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="text"
                            value={r.period ?? ""}
                            onChange={(e) => updateRecord(i, { period: e.target.value || null })}
                            className="w-24 rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                          />
                        </td>
                        <td className="max-w-xs px-4 py-2 font-mono text-xs text-zinc-500">{r.source_line}</td>
                        <td className="px-4 py-2 whitespace-nowrap">
                          {r.verified ? (
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
                              Verified
                            </span>
                          ) : (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                              Needs review
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {notes.length > 0 && (
              <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                  Other notes found (not saved as financial figures)
                </h2>
                <ul className="flex flex-col gap-2">
                  {notes.map((n, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm">
                      <input
                        type="checkbox"
                        checked={n.included}
                        onChange={(e) => updateNote(i, { included: e.target.checked })}
                        className="mt-1"
                      />
                      <div>
                        {n.category && (
                          <span className="mr-2 rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                            {n.category}
                          </span>
                        )}
                        <span className="text-zinc-700 dark:text-zinc-300">{n.text}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => setStep("input")}
                className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
              >
                Back
              </button>
              <button
                onClick={handleConfirm}
                disabled={loading || includedCount === 0}
                className="rounded bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
              >
                {loading ? "Saving..." : `Save ${includedCount} record${includedCount === 1 ? "" : "s"}`}
              </button>
            </div>
          </div>
        )}

        {step === "done" && savedCounts && (
          <div className="flex flex-col items-start gap-4 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <p className="text-sm text-zinc-700 dark:text-zinc-300">
              Saved <strong>{savedCounts.rows}</strong> financial record{savedCounts.rows === 1 ? "" : "s"}
              {savedCounts.notes > 0 && (
                <>
                  {" "}and <strong>{savedCounts.notes}</strong> note{savedCounts.notes === 1 ? "" : "s"}
                </>
              )}
              .
            </p>
            <div className="flex gap-3">
              <button
                onClick={startOver}
                className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
              >
                Add more data
              </button>
              <Link
                href="/businesses"
                className="rounded bg-black px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-black"
              >
                Back to businesses
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function IngestPage() {
  return (
    <Suspense>
      <IngestPageInner />
    </Suspense>
  );
}
