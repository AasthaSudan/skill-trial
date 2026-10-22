export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number, public details?: Record<string, unknown>) { super(message); }
}
export let serverOffset = 0;
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const csrf = document.cookie.split('; ').find(x => x.startsWith('st_csrf='))?.split('=')[1];
  if (csrf) headers.set('X-CSRF-Token', decodeURIComponent(csrf));
  const r = await fetch('/api/v1' + path, { ...options, headers, credentials: 'include' });
  const time = Number(r.headers.get('X-Server-Time')); if (time) serverOffset = time * 1000 - Date.now();
  const body = await r.json();
  if (!r.ok) throw new ApiError(body.error?.code || 'REQUEST_FAILED', body.error?.message || 'Something went wrong. Please try again.', r.status, body.error?.details);
  return body;
}
export const post = <T = any>(path: string, body: unknown = {}, key?: string) => api<T>(path, { method: 'POST', body: JSON.stringify(body), headers: key ? { 'Idempotency-Key': key } : {} });
export const patch = <T = any>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
export async function download(path: string, name: string) {
  const r = await fetch('/api/v1' + path, { credentials: 'include' });
  if (!r.ok) { const b = await r.json(); throw new Error(b.error?.message || 'Download failed.'); }
  const url = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function date(t: number | null | undefined, time = false) { return t ? new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', ...(time ? { hour: '2-digit', minute: '2-digit' } : { year: 'numeric' }) }).format(new Date(t * 1000)) : '—'; }
export const title = (s: string | null | undefined) => (s || 'Not stated').replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
export const percent = (n: number | null | undefined) => n == null ? '—' : Math.round(n * 100) + '%';
