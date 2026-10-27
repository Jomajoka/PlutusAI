"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getSupabase } from "@/lib/supabaseClient";

type Business = { id: string; name: string };

export default function Businesses() {
  const router = useRouter();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function authedFetch(path: string, init?: RequestInit) {
    const { data } = await getSupabase().auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      router.push("/login");
      throw new Error("No session");
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
    return fetch(`${apiUrl}${path}`, {
      ...init,
      headers: {
        ...init?.headers,
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
  }

  async function loadBusinesses() {
    const res = await authedFetch("/businesses");
    if (!res.ok) {
      setError(`Failed to load (${res.status})`);
      return;
    }
    setBusinesses(await res.json());
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
  }

  async function handleLogout() {
    await getSupabase().auth.signOut();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen flex-col items-center gap-6 bg-zinc-50 p-10 font-sans dark:bg-black">
      <div className="flex w-full max-w-sm justify-between">
        <h1 className="text-xl font-semibold text-black dark:text-zinc-50">
          Your businesses
        </h1>
        <button onClick={handleLogout} className="text-sm text-zinc-500 underline">
          Log out
        </button>
      </div>

      <form onSubmit={handleCreate} className="flex w-full max-w-sm gap-2">
        <input
          type="text"
          placeholder="Business name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          required
        />
        <button type="submit" className="rounded bg-black px-3 py-2 text-white dark:bg-white dark:text-black">
          Add
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="w-full max-w-sm">
        {businesses.map((b) => (
          <li key={b.id} className="border-b border-zinc-200 py-2 dark:border-zinc-800">
            {b.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
