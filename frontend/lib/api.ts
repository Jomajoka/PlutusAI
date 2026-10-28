import { getSupabase } from "@/lib/supabaseClient";

export class UnauthenticatedError extends Error {}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function authedFetch(path: string, init?: RequestInit): Promise<Response> {
  const { data } = await getSupabase().auth.getSession();
  const token = data.session?.access_token;
  if (!token) {
    throw new UnauthenticatedError();
  }

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  // Let the browser set its own multipart boundary for FormData bodies.
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`${API_URL}${path}`, { ...init, headers });
}

export type Business = { id: string; name: string };
