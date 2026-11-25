// Proxy hacia FastAPI: evita CORS, oculta la URL interna y valida antes de reenviar.
import { CROPS, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, REQUEST_TIMEOUT_MS } from '@/lib/config'
import { API_URL, clientIp, errorJson } from '@/lib/servidor'
import { detectKind, rejectedFormat } from '@/lib/validacion'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const SOBRECARGA_MULTIPART = 64 * 1024

export async function POST(req: Request): Promise<Response> {
  const declarado = Number(req.headers.get('content-length') ?? '0')
  if (declarado > MAX_UPLOAD_BYTES + SOBRECARGA_MULTIPART) {
    return errorJson(413, 'archivo_demasiado_grande', `El archivo supera el tamaño máximo de ${MAX_UPLOAD_MB} MB.`)
  }
  if (!(req.headers.get('content-type') ?? '').startsWith('multipart/form-data')) {
    return errorJson(400, 'solicitud_invalida', 'La solicitud debe enviarse como multipart/form-data.')
  }

  let form: FormData
  try {
    form = await req.formData()
  } catch {
    return errorJson(400, 'solicitud_invalida', 'El cuerpo multipart está mal formado.')
  }

  const crop = form.get('crop')
  if (typeof crop !== 'string' || crop.length === 0) {
    return errorJson(400, 'cultivo_requerido', "Falta el campo 'crop' (bean o cassava).")
  }
  if (!(CROPS as readonly string[]).includes(crop.trim().toLowerCase())) {
    return errorJson(400, 'cultivo_invalido', "Cultivo no válido. Usa 'bean' (fréjol) o 'cassava' (yuca).")
  }
  const files = form.getAll('file').filter((v): v is File => typeof v !== 'string')
  if (files.length === 0) return errorJson(400, 'archivo_requerido', "Falta el archivo de imagen en el campo 'file'.")
  if (files.length > 1) return errorJson(400, 'multiples_archivos', 'Envía una sola imagen por solicitud.')
  const file = files[0]
  if (file.size === 0) return errorJson(400, 'archivo_vacio', 'El archivo está vacío.')
  if (file.size > MAX_UPLOAD_BYTES) {
    return errorJson(413, 'archivo_demasiado_grande', `El archivo supera el tamaño máximo de ${MAX_UPLOAD_MB} MB.`)
  }
  const head = new Uint8Array(await file.slice(0, 512).arrayBuffer())
  const kind = detectKind(head)
  if (!kind) {
    const otro = rejectedFormat(head)
    return errorJson(415, 'tipo_no_soportado', otro
      ? `Formato ${otro} no soportado. Usa una imagen JPEG o PNG.`
      : 'El archivo no es una imagen JPEG o PNG válida.')
  }

  // Se reenvía con un nombre neutro: el nombre original nunca llega a la API.
  const reenviado = new FormData()
  reenviado.append('crop', crop.trim().toLowerCase())
  reenviado.append('file', file, kind === 'jpeg' ? 'imagen.jpg' : 'imagen.png')

  const headers: Record<string, string> = {}
  const ip = clientIp(req)
  if (ip) headers['X-Forwarded-For'] = ip

  let upstream: Response
  try {
    upstream = await fetch(`${API_URL}/api/v1/predict`, {
      method: 'POST',
      body: reenviado,
      headers,
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]),
      cache: 'no-store',
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      return errorJson(504, 'tiempo_agotado', 'El análisis tardó demasiado. Intenta de nuevo.')
    }
    return errorJson(503, 'servicio_no_disponible', 'No hay conexión con el servidor de análisis.')
  }

  const texto = await upstream.text()
  let cuerpo: unknown
  try {
    cuerpo = JSON.parse(texto)
  } catch {
    return errorJson(502, 'respuesta_invalida', 'El servidor de análisis devolvió una respuesta inválida.')
  }
  const extra: Record<string, string> = { 'Cache-Control': 'no-store' }
  const retry = upstream.headers.get('retry-after')
  if (retry) extra['Retry-After'] = retry
  return Response.json(cuerpo, { status: upstream.status, headers: extra })
}
