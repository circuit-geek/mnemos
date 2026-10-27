/**
 * API configuration. The services in `src/services` currently resolve from
 * local mock data. To go live, point `VITE_API_BASE_URL` at the FastAPI
 * backend and replace the mock bodies with `apiFetch` calls (each service
 * documents the proposed endpoint it maps to).
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const USE_MOCKS = true;

export const API_PREFIX = "/api/v1";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

/** Simulates network latency for mock responses. */
export function mockLatency<T>(value: T, ms = 220): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
