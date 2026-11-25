'use client'

import { useId, useRef, useState, type DragEvent } from 'react'
import { ArrowLeft, ArrowRight, CircleAlert, FlaskConical, ImagePlus, Leaf, LoaderCircle, RefreshCw, ShieldCheck, Upload, X } from 'lucide-react'
import { MAX_UPLOAD_MB } from '@/lib/config'
import { CROPS_CONTENT } from '@/lib/cultivos'
import { inspectDrop } from '@/lib/validacion'
import type { ServiceStatus } from '@/lib/api'
import type { Crop, Photo, UiError } from '@/lib/tipos'

interface Props {
  crop: Crop
  photo: Photo | null
  validating: boolean
  inputError: string | null
  apiError: UiError | null
  analyzing: boolean
  service: ServiceStatus
  onBack: () => void
  onFile: (file: File) => void
  onInputError: (message: string) => void
  onExample: () => void
  onRemove: () => void
  onAnalyze: () => void
  onRetryService: () => void
}

export function UploadStep(p: Props) {
  const info = CROPS_CONTENT[p.crop]
  const fileRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const hintId = useId()
  const errorId = useId()
  const busy = p.validating || p.analyzing

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    if (busy) return
    const r = inspectDrop(e.dataTransfer)
    if ('file' in r) p.onFile(r.file)
    else p.onInputError(r.message)
  }

  return (
    <section className="workflow-page page-width">
      <button className="back-link" onClick={p.onBack}><ArrowLeft size={16} /> Volver al inicio</button>
      <div className="flow-heading">
        <div className="step-label">PASO 01 <span>—</span> FOTOGRAFÍA</div>
        <h1 tabIndex={-1}>Empecemos con tu <em>hoja.</em></h1>
        <p>Selecciona una fotografía clara de una hoja del cultivo elegido.</p>
      </div>
      <div className="upload-layout">
        <div className="upload-main">
          <div className="selected-crop">
            <div className="selected-icon"><Leaf size={19} /></div>
            <div><span>CULTIVO SELECCIONADO</span><strong>{info.name}</strong></div>
            <button onClick={p.onBack}>Cambiar</button>
          </div>

          {p.service === 'offline' && (
            <div className="service-banner" role="alert">
              <CircleAlert size={16} />
              <span>No hay conexión con el servidor de análisis. Puedes preparar la foto y reintentar.</span>
              <button onClick={p.onRetryService}><RefreshCw size={13} /> Reintentar</button>
            </div>
          )}

          <div
            className={`dropzone ${dragging ? 'is-dragging' : ''} ${p.photo ? 'has-photo' : ''} ${p.inputError ? 'has-error' : ''}`}
            onDragOver={(e) => { e.preventDefault(); if (!busy) setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            {p.photo ? (
              <div className="preview-image-wrap">
                <img className="preview-image" src={p.photo.src} alt="Vista previa de la hoja seleccionada" />
                <div className="preview-file">
                  <span className="file-thumb"><ImagePlus size={18} /></span>
                  <span>
                    <b title={p.photo.name}>{p.photo.name}</b>
                    <small>{p.photo.sample ? 'Imagen de ejemplo' : 'Fotografía seleccionada'} · {p.photo.width}×{p.photo.height} px</small>
                  </span>
                  <button className="remove-photo" aria-label="Quitar imagen" onClick={p.onRemove} disabled={p.analyzing}><X size={17} /></button>
                </div>
              </div>
            ) : (
              <button
                className="dropzone-inner"
                onClick={() => fileRef.current?.click()}
                disabled={busy}
                aria-describedby={`${hintId}${p.inputError ? ` ${errorId}` : ''}`}
              >
                <div className="upload-icon">{p.validating ? <LoaderCircle size={23} className="spin" /> : <Upload size={23} />}</div>
                <strong>{p.validating ? 'Revisando la imagen…' : 'Arrastra tu imagen aquí'}</strong>
                <span>o <u>selecciona un archivo</u> desde tu dispositivo</span>
                <small id={hintId}>JPG o PNG · máximo {MAX_UPLOAD_MB} MB · mínimo 64×64 px</small>
              </button>
            )}
            <input
              ref={fileRef}
              className="sr-only"
              type="file"
              accept="image/jpeg,image/png"
              aria-label="Seleccionar imagen JPG o PNG"
              tabIndex={-1}
              onChange={(e) => {
                const files = e.target.files
                if (files && files.length > 1) p.onInputError('Selecciona una sola imagen.')
                else if (files?.[0]) p.onFile(files[0])
                e.target.value = '' // permite volver a elegir el mismo archivo
              }}
            />
          </div>

          {p.inputError && (
            <p className="form-error" id={errorId} role="alert"><CircleAlert size={15} /> {p.inputError}</p>
          )}

          <button className="example-button" onClick={p.onExample} disabled={busy}><ImagePlus size={16} /> Usar imagen de ejemplo</button>
          <div className="analysis-note">
            <ShieldCheck size={17} />
            <span>Tu fotografía se analiza en el servidor y <b>no se almacena</b>: se procesa en memoria y se descarta.</span>
          </div>

          {p.apiError && (
            <div className="form-error api-error" role="alert">
              <CircleAlert size={15} />
              <span>{p.apiError.message}</span>
              {p.apiError.retryable && p.photo && (
                <button onClick={p.onAnalyze} disabled={p.analyzing}><RefreshCw size={13} /> Reintentar</button>
              )}
            </div>
          )}

          <button className="primary-button analyze-button" disabled={!p.photo || busy} onClick={p.onAnalyze} aria-busy={p.analyzing}>
            {p.analyzing
              ? <><LoaderCircle size={18} className="spin" /> Analizando imagen…</>
              : <>Analizar imagen <ArrowRight size={17} /></>}
          </button>
        </div>
        <aside className="upload-aside">
          <div className="aside-kicker">RECORRIDO</div>
          <div className="steps">
            <div className="step active"><span>1</span><div><b>Fotografía</b><small>Selecciona una imagen</small></div></div>
            <div className="step"><span>2</span><div><b>Resultado</b><small>Clasificación del modelo</small></div></div>
            <div className="step"><span>3</span><div><b>Reporte</b><small>Documento imprimible</small></div></div>
          </div>
          <div className="model-chip"><FlaskConical size={16} /><span><small>MODELO</small><b>{info.model}</b></span></div>
        </aside>
      </div>
    </section>
  )
}
