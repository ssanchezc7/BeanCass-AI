// Tipos compartidos entre el cliente, el proxy y la API de inferencia.

export type Crop = 'bean' | 'cassava'
export type Stage = 'home' | 'upload' | 'result' | 'report'
export type QualityLevel = 'ok' | 'low_confidence' | 'inconclusive'

export interface ApiProbability {
  class_id: number
  label: string
  label_es: string
  probability: number
}

export interface PredictResponse {
  crop: Crop
  model: { name: string; version: string }
  prediction: {
    class_id: number
    label: string
    label_es: string
    confidence: number
    is_healthy: boolean
  }
  probabilities: ApiProbability[]
  quality: {
    level: QualityLevel
    warnings: string[]
    signals: { top1: number; margin: number; entropy: number; leaf_ratio: number; reasons: string[] }
  }
  image: { width: number; height: number; resized_to: [number, number] }
  inference_ms: number
  disclaimer: string
}

export interface ApiErrorBody {
  error: { code: string; message: string }
}

export interface Photo {
  file: File
  src: string // object URL (se revoca al reemplazar o quitar la foto)
  name: string
  sample: boolean
  width: number
  height: number
}

export interface UiError {
  code: string
  message: string
  retryable: boolean
}

export function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null || !('error' in value)) return false
  const err = (value as { error: unknown }).error
  return (
    typeof err === 'object' && err !== null &&
    typeof (err as { code?: unknown }).code === 'string' &&
    typeof (err as { message?: unknown }).message === 'string'
  )
}

export function isPredictResponse(value: unknown): value is PredictResponse {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Partial<PredictResponse>
  return (
    (v.crop === 'bean' || v.crop === 'cassava') &&
    typeof v.prediction?.confidence === 'number' &&
    Array.isArray(v.probabilities) &&
    typeof v.quality?.level === 'string'
  )
}
