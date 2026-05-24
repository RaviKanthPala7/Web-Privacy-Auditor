/**
 * Talks to the FastAPI backend.
 * Local dev: VITE_API_URL empty → /audit (Vite proxy or nginx in Docker).
 * GCP: set VITE_API_URL to your Cloud Run API URL at build time.
 */
const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export async function runAudit(url) {
  const res = await fetch(`${API_BASE}/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })

  const data = await res.json()

  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`)
  }

  return data
}
