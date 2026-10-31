/**
 * Backend access. The base URL comes from `VITE_API_BASE_URL`; services in
 * `src/services` own the endpoints and map responses to the domain types.
 */
export const API_BASE_URL: string = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export const API_PREFIX = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** FastAPI errors carry `{detail: string}` or a list of validation problems. */
function describeError(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  return `Request failed (${status})`;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof init?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, { ...init, headers });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(`Can't reach the MNEMOS backend at ${API_BASE_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null);
    throw new ApiError(describeError(body, res.status), res.status);
  }
  return (await res.json()) as T;
}

/** Turns a backend-relative path (e.g. an evidence frame URL) into a loadable URL. */
export function absoluteUrl(path: string): string {
  return /^https?:\/\//.test(path) ? path : `${API_BASE_URL}${path}`;
}

export const videoMediaUrl = (videoId: string) =>
  `${API_BASE_URL}${API_PREFIX}/videos/${videoId}/media`;

export const frameUrl = (videoId: string, timestampMs: number) =>
  `${API_BASE_URL}${API_PREFIX}/videos/${videoId}/frames/${Math.max(0, Math.round(timestampMs))}`;
