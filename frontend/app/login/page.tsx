"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { authedFetch, Business } from "@/lib/api";
import { getSupabase } from "@/lib/supabaseClient";
import Logo from "@/components/Logo";

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
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-zinc-50 p-6 font-sans dark:bg-black">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 -left-40 h-80 w-80 rounded-full bg-blue-500/10 blur-3xl dark:bg-blue-500/10"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-emerald-500/10 blur-3xl dark:bg-emerald-500/10"
      />

      <div className="relative z-10 flex w-full max-w-sm flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-3">
          <Logo size="lg" />
          <p className="text-center text-sm text-zinc-500 dark:text-zinc-400">
            Visualize your business, simulate what&apos;s next.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
        >
          <h1 className="text-lg font-semibold text-black dark:text-zinc-50">
            {mode === "login" ? "Log in" : "Create your account"}
          </h1>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2 transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-600 dark:focus:ring-white/10"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2 transition-colors focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-black/10 dark:border-zinc-700 dark:bg-zinc-950 dark:focus:border-zinc-600 dark:focus:ring-white/10"
            required
            minLength={6}
          />
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <button
            type="submit"
            className="cursor-pointer rounded bg-black px-3 py-2 font-medium text-white transition-colors hover:bg-zinc-800 active:bg-zinc-700 dark:bg-white dark:text-black dark:hover:bg-zinc-200 dark:active:bg-zinc-300"
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
    </div>
  );
}
