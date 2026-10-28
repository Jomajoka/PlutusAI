"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { authedFetch, Business } from "@/lib/api";
import { getSupabase } from "@/lib/supabaseClient";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "signup">("login");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const supabase = getSupabase();
    const { error } =
      mode === "login"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

    if (error) {
      setError(error.message);
      return;
    }

    try {
      const res = await authedFetch("/businesses");
      if (res.ok) {
        const businesses: Business[] = await res.json();
        if (businesses.length > 0) {
          router.push(`/dashboard?business=${businesses[0].id}`);
          return;
        }
      }
    } catch {
      // Fall through to the businesses page if the lookup failed.
    }

    router.push("/businesses");
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-sm flex-col gap-3 rounded-lg border border-zinc-200 p-6 dark:border-zinc-800"
      >
        <h1 className="text-xl font-semibold text-black dark:text-zinc-50">
          {mode === "login" ? "Log in" : "Sign up"}
        </h1>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border border-zinc-300 px-3 py-2 transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-600 dark:focus:ring-white/10"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border border-zinc-300 px-3 py-2 transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-600 dark:focus:ring-white/10"
          required
          minLength={6}
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="cursor-pointer rounded bg-black px-3 py-2 text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:active:bg-zinc-300"
        >
          {mode === "login" ? "Log in" : "Sign up"}
        </button>
        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
          className="cursor-pointer text-sm text-zinc-500 underline transition-colors hover:text-zinc-800 dark:hover:text-zinc-300"
        >
          {mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}
