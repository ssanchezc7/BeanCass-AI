// Validaciones del cliente (el servidor repite todas: esto solo da respuesta inmediata al usuario).
import { MAX_ASPECT_RATIO, MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, MIN_IMAGE_SIDE } from './config'

export type ImageKind = 'jpeg' | 'png'

const FIRMAS_RECHAZADAS: Array<[string, (b: Uint8Array) => boolean]> = [
  ['GIF', (b) => ascii(b, 0, 4) === 'GIF8'],
  ['WebP', (b) => ascii(b, 0, 4) === 'RIFF' && ascii(b, 8, 12) === 'WEBP'],
  ['HEIC/HEIF', (b) => ascii(b, 4, 8) === 'ftyp'],
  ['PDF', (b) => ascii(b, 0, 5) === '%PDF-'],
  ['BMP', (b) => ascii(b, 0, 2) === 'BM'],
  ['SVG', (b) => /<\?xml|<svg/i.test(ascii(b, 0, b.length))],
]

function ascii(b: Uint8Array, desde: number, hasta: number): string {
  return String.fromCharCode(...b.subarray(desde, Math.min(hasta, b.length)))
}

/** Detecta el formato por magic bytes (no confía en la extensión ni en file.type). */
export function detectKind(head: Uint8Array): ImageKind | null {
  if (head.length >= 3 && head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return 'jpeg'
  const png = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]
  if (head.length >= 8 && png.every((v, i) => head[i] === v)) return 'png'
  return null
}

export function rejectedFormat(head: Uint8Array): string | null {
  for (const [nombre, prueba] of FIRMAS_RECHAZADAS) if (prueba(head)) return nombre
  return null
}

function indexOfSeq(hay: Uint8Array, seq: number[]): number {
  outer: for (let i = hay.length - seq.length; i >= 0; i--) {
    for (let j = 0; j < seq.length; j++) if (hay[i + j] !== seq[j]) continue outer
    return i
  }
  return -1
}

/** PNG debe contener el chunk IEND; JPEG, el marcador EOI (FFD9) cerca del final. */
export function isComplete(kind: ImageKind, tail: Uint8Array): boolean {
  if (kind === 'png') return indexOfSeq(tail, [0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82]) >= 0
  return indexOfSeq(tail, [0xff, 0xd9]) >= 0
}

export function formatMB(bytes: number): string {
  return (bytes / (1024 * 1024)).toLocaleString('es-EC', { maximumFractionDigits: 1 })
}

function loadDimensions(src: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = () => reject(new Error('decodificacion'))
    img.src = src
  })
}

export type ValidationResult =
  | { ok: true; src: string; width: number; height: number; kind: ImageKind }
  | { ok: false; message: string }

/**
 * Valida tipo, tamaño, integridad y dimensiones. Si es válida devuelve un object URL
 * que el llamador debe revocar (URL.revokeObjectURL) cuando ya no lo use.
 */
export async function validateImageFile(file: File): Promise<ValidationResult> {
  if (file.size === 0) return { ok: false, message: 'El archivo está vacío. Elige otra fotografía.' }
  if (file.size > MAX_UPLOAD_BYTES) {
    return { ok: false, message: `La imagen pesa ${formatMB(file.size)} MB y el máximo es ${MAX_UPLOAD_MB} MB. Reduce su tamaño o usa otra foto.` }
  }
  const head = new Uint8Array(await file.slice(0, 512).arrayBuffer())
  const kind = detectKind(head)
  if (!kind) {
    const otro = rejectedFormat(head)
    return {
      ok: false,
      message: otro
        ? `El formato ${otro} no está soportado. Usa una imagen JPEG o PNG.`
        : 'El archivo no es una imagen JPEG o PNG válida, aunque su extensión lo indique.',
    }
  }
  // Los navegadores dibujan imágenes truncadas sin error: se comprueba el marcador de fin de archivo.
  const tail = new Uint8Array(await file.slice(Math.max(0, file.size - 65536)).arrayBuffer())
  if (!isComplete(kind, tail)) {
    return { ok: false, message: 'No se pudo leer la imagen: el archivo parece dañado o incompleto.' }
  }
  const src = URL.createObjectURL(file)
  try {
    const { width, height } = await loadDimensions(src)
    if (Math.min(width, height) < MIN_IMAGE_SIDE) {
      URL.revokeObjectURL(src)
      return { ok: false, message: `La imagen mide ${width}×${height} px; el mínimo es ${MIN_IMAGE_SIDE}×${MIN_IMAGE_SIDE} px.` }
    }
    const ratio = Math.max(width, height) / Math.min(width, height)
    if (ratio > MAX_ASPECT_RATIO) {
      URL.revokeObjectURL(src)
      return { ok: false, message: `La imagen es demasiado alargada (${ratio.toFixed(1)}:1). Recórtala para centrar la hoja.` }
    }
    return { ok: true, src, width, height, kind }
  } catch {
    URL.revokeObjectURL(src)
    return { ok: false, message: 'No se pudo leer la imagen: el archivo parece dañado o incompleto.' }
  }
}

/** Revisa un arrastre: exactamente un archivo y ninguna carpeta. */
export function inspectDrop(dt: DataTransfer): { file: File } | { message: string } {
  const items = Array.from(dt.items ?? []).filter((i) => i.kind === 'file')
  const hasFolder = items.some((i) => {
    const entry = typeof i.webkitGetAsEntry === 'function' ? i.webkitGetAsEntry() : null
    return entry?.isDirectory === true
  })
  if (hasFolder) return { message: 'No se admiten carpetas. Arrastra una sola imagen JPEG o PNG.' }
  const files = Array.from(dt.files ?? [])
  if (files.length === 0) return { message: 'No se detectó ningún archivo. Arrastra una imagen JPEG o PNG.' }
  if (files.length > 1) return { message: `Arrastraste ${files.length} archivos. Analiza una sola imagen a la vez.` }
  return { file: files[0] }
}
