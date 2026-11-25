// Límites compartidos con el servidor. NEXT_PUBLIC_MAX_UPLOAD_MB debe coincidir con MAX_UPLOAD_MB de la API.

function numeroPositivo(valor: string | undefined, defecto: number): number {
  const n = Number(valor)
  return Number.isFinite(n) && n > 0 ? n : defecto
}

export const MAX_UPLOAD_MB = numeroPositivo(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB, 8)
export const MAX_UPLOAD_BYTES = Math.floor(MAX_UPLOAD_MB * 1024 * 1024)
export const MIN_IMAGE_SIDE = 64
export const MAX_ASPECT_RATIO = 5
export const REQUEST_TIMEOUT_MS = 30_000
export const CROPS = ['bean', 'cassava'] as const
