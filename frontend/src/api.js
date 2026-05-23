/**
 * Talks to the FastAPI backend.
 * Vite proxy forwards /audit → http://127.0.0.1:8000/audit
 */
export async function runAudit(url) {
  const res = await fetch('/audit', {
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
