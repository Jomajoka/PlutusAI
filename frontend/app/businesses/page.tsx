"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { authedFetch, Business, UnauthenticatedError } from "@/lib/api";
import { getSupabase } from "@/lib/supabaseClient";
import Logo from "@/components/Logo";

export default function Businesses() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadBusinesses() {
    try {
      const res = await authedFetch("/businesses");
      if (!res.ok) {
        setError(`Failed to load (${res.status})`);
        return;
      }
      setBusinesses(await res.json());
    } catch (err) {
      if (err instanceof UnauthenticatedError) router.push("/login");
    }
  }

  useEffect(() => {
    getSupabase().auth.getSession().then(({ data }) => {
      if (!data.session) {
        router.push("/login");
        return;
      }
      loadBusinesses();
    });
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await authedFetch("/businesses", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (!res.ok) {
        setError(`Failed to create (${res.status})`);
        return;
      }
      setName("");
      await loadBusinesses();
    } catch (err) {
      if (err instanceof UnauthenticatedError) router.push("/login");
    }
  }

  async function handleLogout() {
    await getSupabase().auth.signOut();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 bg-zinc-50 p-10 font-sans dark:bg-black">
      <div className="flex w-full max-w-sm flex-col gap-4">
        <div className="flex items-center justify-between">
          <Logo size="sm" />
          <button
            onClick={handleLogout}
            className="cursor-pointer text-sm text-zinc-500 underline transition-colors hover:text-zinc-800 dark:hover:text-zinc-300"
          >
            Log out
          </button>
        </div>
        <h1 className="text-xl font-semibold text-black dark:text-zinc-50">Your businesses</h1>
      </div>

      <form onSubmit={handleCreate} className="flex w-full max-w-sm gap-2">
        <input
          type="text"
          placeholder="Business name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded border border-zinc-300 px-3 py-2 transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-600 dark:focus:ring-white/10"
          required
        />
        <button
          type="submit"
          className="cursor-pointer rounded bg-black px-3 py-2 text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:active:bg-zinc-300"
        >
          Add
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="w-full max-w-sm">
        {businesses.map((b) => (
          <li
            key={b.id}
            className="flex items-center justify-between border-b border-zinc-200 py-2 transition-colors hover:bg-zinc-100/60 dark:border-zinc-800 dark:hover:bg-zinc-900/60"
          >
            <span>{b.name}</span>
            <div className="flex gap-3">
              <Link
                href={`/dashboard?business=${b.id}`}
                className="text-sm text-zinc-500 underline transition-colors hover:text-zinc-800 dark:hover:text-zinc-300"
              >
                Dashboard
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
