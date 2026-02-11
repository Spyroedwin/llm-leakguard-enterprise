const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function chat(prompt) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });

  const data = await res.json();
  if (!res.ok) {
    // backend sends { detail: "..." } on errors
    const msg = data?.detail || "Request failed";
    throw new Error(msg);
  }
  return data;
}

export async function getLogs() {
  const res = await fetch(`${API_BASE}/logs`);
  if (!res.ok) throw new Error("Failed to load logs");
  return await res.json();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend unhealthy");
  return await res.json();
}
