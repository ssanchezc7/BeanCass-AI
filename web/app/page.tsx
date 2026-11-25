'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AboutModelDialog } from '@/components/beancass/AboutModelDialog'
import { HomeStep } from '@/components/beancass/HomeStep'
import { ReportView } from '@/components/beancass/ReportView'
import { ResultStep } from '@/components/beancass/ResultStep'
import { Topbar } from '@/components/beancass/Topbar'
import { UploadStep } from '@/components/beancass/UploadStep'
import { PredictError, checkHealth, predict, type ServiceStatus } from '@/lib/api'
import { CROPS_CONTENT } from '@/lib/cultivos'
import type { Crop, Photo, PredictResponse, Stage, UiError } from '@/lib/tipos'
import { validateImageFile } from '@/lib/validacion'

const ANUNCIOS: Record<Stage, string> = {
  home: 'Inicio',
  upload: 'Paso 1: selecciona una fotografía',
  result: 'Paso 2: resultado del análisis',
  report: 'Reporte de clasificación',
}

export default function Page() {
  const [stage, setStage] = useState<Stage>('home')
  const [crop, setCrop] = useState<Crop>('bean')
  const [photo, setPhoto] = useState<Photo | null>(null)
  const [validating, setValidating] = useState(false)
  const [inputError, setInputError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [apiError, setApiError] = useState<UiError | null>(null)
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [analyzedAt, setAnalyzedAt] = useState<Date | null>(null)
  const [trueLabel, setTrueLabel] = useState('')
  const [service, setService] = useState<ServiceStatus>('checking')
  const [aboutOpen, setAboutOpen] = useState(false)
  const [announcement, setAnnouncement] = useState('')

  const abortRef = useRef<AbortController | null>(null)
  const photoRef = useRef<Photo | null>(null)
  const fileToken = useRef(0)

  // --- Foto: un único object URL vivo, revocado al reemplazar, quitar o desmontar ---
  const replacePhoto = useCallback((next: Photo | null) => {
    const prev = photoRef.current
    if (prev && prev.src !== next?.src) URL.revokeObjectURL(prev.src)
    photoRef.current = next
    setPhoto(next)
  }, [])

  useEffect(() => () => {
    abortRef.current?.abort()
    if (photoRef.current) URL.revokeObjectURL(photoRef.current.src)
  }, [])

  // --- Estado del servicio ---
  const refreshService = useCallback(async () => {
    setService('checking')
    setService(await checkHealth())
  }, [])

  useEffect(() => { void refreshService() }, [refreshService])

  // --- Foco y anuncios accesibles al cambiar de pantalla (no en la carga inicial) ---
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return }
    setAnnouncement(ANUNCIOS[stage])
    document.querySelector<HTMLElement>('main h1')?.focus({ preventScroll: false })
    window.scrollTo({ top: 0 })
  }, [stage])

  function cancelPending() {
    abortRef.current?.abort()
    abortRef.current = null
    setAnalyzing(false)
  }

  function resetAnalysis() {
    cancelPending()
    setResult(null)
    setApiError(null)
    setTrueLabel('')
  }

  function goHome() {
    resetAnalysis()
    fileToken.current++
    setValidating(false)
    setInputError(null)
    replacePhoto(null)
    setStage('home')
  }

  function chooseCrop(next: Crop) {
    goHome()
    setCrop(next)
    setStage('upload')
  }

  async function acceptFile(file: File, sample: boolean) {
    const token = ++fileToken.current
    resetAnalysis()
    setInputError(null)
    setValidating(true)
    const v = await validateImageFile(file)
    if (token !== fileToken.current) {
      if (v.ok) URL.revokeObjectURL(v.src)
      return
    }
    setValidating(false)
    if (!v.ok) {
      setInputError(v.message)
      setAnnouncement(v.message)
      return
    }
    replacePhoto({ file, src: v.src, name: sample ? `Ejemplo de ${CROPS_CONTENT[crop].name.toLowerCase()}` : file.name, sample, width: v.width, height: v.height })
    setAnnouncement('Imagen lista para analizar')
  }

  async function loadExample() {
    const info = CROPS_CONTENT[crop]
    try {
      const res = await fetch(info.image)
      if (!res.ok) throw new Error('ejemplo')
      const blob = await res.blob()
      await acceptFile(new File([blob], `ejemplo-${info.english.toLowerCase()}.png`, { type: blob.type || 'image/png' }), true)
    } catch {
      setInputError('No se pudo cargar la imagen de ejemplo. Intenta de nuevo.')
    }
  }

  async function analyze() {
    if (!photo || analyzing || validating) return
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setAnalyzing(true)
    setApiError(null)
    setAnnouncement('Analizando imagen…')
    try {
      const r = await predict(crop, photo.file, ctrl.signal)
      if (ctrl.signal.aborted) return
      setResult(r)
      setAnalyzedAt(new Date())
      setTrueLabel('')
      setService('online')
      setStage('result')
    } catch (err) {
      if (ctrl.signal.aborted) return
      const ui = err instanceof PredictError
        ? err.ui
        : { code: 'desconocido', message: 'Ocurrió un error inesperado. Intenta de nuevo.', retryable: true }
      setApiError(ui)
      setAnnouncement(ui.message)
      if (ui.code === 'servicio_no_disponible' || ui.code === 'red' || ui.code === 'sin_conexion') setService('offline')
    } finally {
      if (abortRef.current === ctrl) {
        abortRef.current = null
        setAnalyzing(false)
      }
    }
  }

  function backToUpload() {
    resetAnalysis()
    setStage('upload')
  }

  return (
    <main className="app-shell">
      <p className="sr-only" aria-live="polite" role="status">{announcement}</p>
      <Topbar status={service} onHome={goHome} onAbout={() => setAboutOpen(true)} />

      {stage === 'home' && <HomeStep onChoose={chooseCrop} onAbout={() => setAboutOpen(true)} />}

      {stage === 'upload' && (
        <UploadStep
          crop={crop}
          photo={photo}
          validating={validating}
          inputError={inputError}
          apiError={apiError}
          analyzing={analyzing}
          service={service}
          onBack={goHome}
          onFile={(f) => void acceptFile(f, false)}
          onInputError={(m) => { setInputError(m); setAnnouncement(m) }}
          onExample={() => void loadExample()}
          onRemove={() => { resetAnalysis(); setInputError(null); replacePhoto(null) }}
          onAnalyze={() => void analyze()}
          onRetryService={() => void refreshService()}
        />
      )}

      {stage === 'result' && photo && result && (
        <ResultStep
          crop={crop}
          photo={photo}
          result={result}
          trueLabel={trueLabel}
          onTrueLabel={setTrueLabel}
          onBack={backToUpload}
          onAnother={() => { backToUpload(); replacePhoto(null) }}
          onChangeCrop={goHome}
          onReport={() => setStage('report')}
          onAbout={() => setAboutOpen(true)}
        />
      )}

      {stage === 'report' && photo && result && analyzedAt && (
        <ReportView crop={crop} photo={photo} result={result} analyzedAt={analyzedAt} trueLabel={trueLabel} onBack={() => setStage('result')} />
      )}

      <AboutModelDialog open={aboutOpen} onClose={() => setAboutOpen(false)} focusCrop={stage === 'home' ? undefined : crop} />

      <footer className="site-footer">
        <span>BeanCass AI <span className="footer-dot">·</span> Proyecto universitario UNEMI</span>
        <span>Resultados orientativos; no constituyen un diagnóstico.</span>
      </footer>
    </main>
  )
}
