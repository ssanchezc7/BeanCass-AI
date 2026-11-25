// Estado del servicio de inferencia: online (modelos cargados), degraded (algún modelo falló) u offline.
import { API_URL } from '@/lib/servidor'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(): Promise<Response> {
  const headers = { 'Cache-Control': 'no-store' }
  try {
    const res = await fetch(`${API_URL}/health`, { cache: 'no-store', signal: AbortSignal.timeout(4000) })
    const body: unknown = await res.json().catch(() => null)
    const models =
      typeof body === 'object' && body !== null && 'models_loaded' in body
        ? (body as { models_loaded: Record<string, boolean> }).models_loaded
        : null
    if (res.ok) return Response.json({ status: 'online', models_loaded: models }, { headers })
    return Response.json({ status: 'degraded', models_loaded: models }, { status: 503, headers })
  } catch {
    return Response.json({ status: 'offline', models_loaded: null }, { status: 503, headers })
  }
}
