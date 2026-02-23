export const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export async function apiGet<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { signal });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed (${res.status}) ${text}`);
  }
  return res.json() as Promise<T>;
}
