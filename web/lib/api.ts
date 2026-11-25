// Cliente del proxy /api/predict con timeout, cancelación y mensajes de error accionables.
import { REQUEST_TIMEOUT_MS } from './config'
import { isApiErrorBody, isPredictResponse, type Crop, type PredictResponse, type UiError } from './tipos'

export class PredictError extends Error {
  constructor(public readonly ui: UiError) {
    super(ui.message)
  }
}

const REINTENTABLES = new Set([429, 500, 502, 503, 504])

function mensajePorEstado(status: number, code: string, serverMessage: string): string {
  switch (status) {
    case 413:
    case 415:
    case 422:
    case 400:
      return serverMessage
    case 429:
      return 'Has hecho demasiadas solicitudes seguidas. Espera un minuto y vuelve a intentarlo.'
    case 503:
      return code === 'servicio_no_disponible'
        ? 'No hay conexión con el servidor de análisis. Comprueba que la API esté en ejecución y reintenta.'
        : serverMessage || 'El modelo no está disponible en este momento. Intenta de nuevo en unos segundos.'
    case 504:
      return 'El análisis tardó demasiado. Intenta de nuevo; si persiste, usa una imagen más liviana.'
    default:
      return 'Ocurrió un error inesperado en el servidor. Intenta de nuevo en unos momentos.'
  }
}

/**
 * Envía la imagen al proxy. `signal` permite cancelar (cambio de cultivo, volver, desmontar).
 * Lanza PredictError con un mensaje en español listo para mostrar.
 */
export async function predict(crop: Crop, file: File, signal: AbortSignal): Promise<PredictResponse> {
  const form = new FormData()
  form.append('crop', crop)
  form.append('file', file, file.name)

  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  const combined = AbortSignal.any([signal, timeout])

  let res: Response
  try {
    res = await fetch('/api/predict', { method: 'POST', body: form, signal: combined })
  } catch (err) {
    if (signal.aborted) throw err // cancelado por el usuario: el llamador lo ignora
    if (timeout.aborted) {
      throw new PredictError({ code: 'tiempo_agotado', message: mensajePorEstado(504, '', ''), retryable: true })
    }
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false
    throw new PredictError({
      code: offline ? 'sin_conexion' : 'red',
      message: offline
        ? 'Parece que no tienes conexión a internet. Revisa tu red y reintenta.'
        : 'No se pudo contactar con el servidor. Revisa tu conexión y reintenta.',
      retryable: true,
    })
  }

  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }

  if (res.ok && isPredictResponse(body)) return body
  const code = isApiErrorBody(body) ? body.error.code : 'respuesta_invalida'
  const serverMessage = isApiErrorBody(body) ? body.error.message : ''
  const status = res.ok ? 502 : res.status
  throw new PredictError({
    code,
    message: mensajePorEstado(status, code, serverMessage),
    retryable: REINTENTABLES.has(status),
  })
}

export type ServiceStatus = 'checking' | 'online' | 'degraded' | 'offline'

export async function checkHealth(signal?: AbortSignal): Promise<ServiceStatus> {
  try {
    const res = await fetch('/api/health', { cache: 'no-store', signal })
    const body: unknown = await res.json().catch(() => null)
    const status = typeof body === 'object' && body !== null ? (body as { status?: unknown }).status : null
    return status === 'online' || status === 'degraded' ? status : 'offline'
  } catch {
    return 'offline'
  }
}
