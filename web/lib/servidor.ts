// Utilidades solo de servidor para los route handlers que hacen de proxy hacia FastAPI.
// (Solo se importa desde app/api/*; API_URL no es una variable NEXT_PUBLIC, así que nunca llega al navegador.)

export const API_URL = (process.env.API_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '')

export function errorJson(status: number, code: string, message: string, headers?: HeadersInit): Response {
  return Response.json({ error: { code, message } }, { status, headers: { 'Cache-Control': 'no-store', ...headers } })
}

/** IP del cliente reenviada a la API para el rate limit (solo se usa si la API confía en el proxy). */
export function clientIp(req: Request): string | null {
  const xff = req.headers.get('x-forwarded-for')
  if (xff) return xff.split(',')[0].trim().slice(0, 64)
  return req.headers.get('x-real-ip')
}
