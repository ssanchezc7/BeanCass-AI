'use client'

import { useId } from 'react'
import { ArrowLeft, ArrowRight, Camera, ChevronRight, CircleAlert, FileText, FlaskConical, ImagePlus, Leaf, RefreshCw, TriangleAlert } from 'lucide-react'
import { CROPS_CONTENT, classContent, percentLabel } from '@/lib/cultivos'
import type { Crop, Photo, PredictResponse } from '@/lib/tipos'
import { ScoreBars } from './ScoreBars'

interface Props {
  crop: Crop
  photo: Photo
  result: PredictResponse
  trueLabel: string
  onTrueLabel: (code: string) => void
  onBack: () => void
  onAnother: () => void
  onChangeCrop: () => void
  onReport: () => void
  onAbout: () => void
}

export function verdict(result: PredictResponse) {
  const inconclusive = result.quality.level === 'inconclusive'
  const [first, second] = result.probabilities
  return {
    inconclusive,
    overline: inconclusive
      ? 'RESULTADO NO CONCLUYENTE'
      : result.quality.level === 'low_confidence' ? 'CATEGORÍA MÁS PROBABLE · CONFIANZA MODERADA' : 'CATEGORÍA PREDICHA',
    title: inconclusive ? 'No concluyente' : result.prediction.label_es,
    description: inconclusive
      ? `Las opciones más probables son ${first.label_es} (${percentLabel(first.probability)} %)${second ? ` y ${second.label_es} (${percentLabel(second.probability)} %)` : ''}. No se emite una categoría: repite la foto.`
      : null,
  }
}

export function ResultStep(p: Props) {
  const info = CROPS_CONTENT[p.crop]
  const r = p.result
  const v = verdict(r)
  const top = classContent(p.crop, r.prediction.label)
  const selectId = useId()
  const real = p.trueLabel ? classContent(p.crop, p.trueLabel) : undefined
  const match = real?.code === r.prediction.label

  return (
    <section className="workflow-page result-page page-width">
      <button className="back-link" onClick={p.onBack}><ArrowLeft size={16} /> Volver a la fotografía</button>
      <div className="result-top">
        <div>
          <div className="step-label">PASO 02 <span>—</span> RESULTADO</div>
          <h1 tabIndex={-1}>Resultado orientativo</h1>
          <p>Clasificación generada por {r.model.name} a partir de tu fotografía.</p>
        </div>
        <div className="simulated-tag" title={`Versión ${r.model.version}`}>
          <span /> {r.model.name.toUpperCase()} · {r.inference_ms} MS
        </div>
      </div>
      <div className="result-grid">
        <div className="result-photo-panel">
          <img src={p.photo.src} alt="Fotografía analizada" />
          <div className="photo-caption"><ImagePlus size={15} /><span>Fotografía original</span><small title={p.photo.name}>{p.photo.name}</small></div>
          <div className="image-unchanged"><ImagePlus size={13} /> {r.image.width}×{r.image.height} px · el modelo la ve a 224×224 sin deformarla</div>
        </div>

        <div className="result-content">
          <div className="result-crop-label"><Leaf size={16} /> {info.name.toUpperCase()}</div>
          <div className={`prediction-card ${v.inconclusive ? 'is-inconclusive' : ''}`} aria-live="polite">
            <div className="prediction-top">
              <div>
                <span className="result-overline">{v.overline}</span>
                <h2>{v.title}</h2>
              </div>
              <div className="score-circle" aria-label={`Confianza máxima ${percentLabel(r.prediction.confidence)} por ciento`}>
                <strong>{percentLabel(r.prediction.confidence)}<small>%</small></strong>
              </div>
            </div>
            <p className="prediction-description">
              {v.description ?? top?.description ?? r.disclaimer}
            </p>
          </div>

          <ScoreBars probabilities={r.probabilities} tag={r.model.name} />

          {r.quality.warnings.map((w) => (
            <div className={`disclaimer ${r.quality.level !== 'ok' ? 'is-warning' : ''}`} key={w}>
              <TriangleAlert size={16} /><span>{w}</span>
            </div>
          ))}
          <div className="disclaimer">
            <CircleAlert size={16} />
            <span>La puntuación del modelo no garantiza que la clasificación sea correcta. {r.disclaimer}</span>
          </div>

          {v.inconclusive ? (
            <div className="info-card">
              <div className="info-icon"><Camera size={17} /></div>
              <div>
                <b>Cómo obtener una mejor foto</b>
                <p>El modelo se entrenó con fotos de campo de hojas individuales. Para un resultado más fiable:</p>
                <div className="info-subsections">
                  <span>ENCUADRE <small>Una sola hoja ocupando la mayor parte de la imagen, enfocada y sin desenfoque.</small></span>
                  <span>LUZ <small>Luz natural difusa, sin sombras fuertes ni reflejos; evita fondos con muchas hojas.</small></span>
                </div>
              </div>
            </div>
          ) : top && (
            <div className="info-card">
              <div className="info-icon"><Leaf size={17} /></div>
              <div>
                <b>Sobre {top.code === 'healthy' ? 'la hoja sana' : /^[A-Z]{2}/.test(top.name) ? top.name : `la ${top.name.toLowerCase()}`}</b>
                <p>{top.description}</p>
                <div className="info-subsections">
                  <span>SÍNTOMAS VISIBLES <small>{top.symptoms}</small></span>
                  <span>QUÉ HACER <small>{top.advice}</small></span>
                </div>
              </div>
            </div>
          )}

          <div className="comparison-card">
            <div className="comparison-heading"><label htmlFor={selectId}>¿CONOCES LA ETIQUETA REAL?</label><span className="simulated-mini">OPCIONAL</span></div>
            <p>Si sabes qué condición tiene la hoja, compárala con la predicción del modelo.</p>
            <select id={selectId} className="label-select" value={p.trueLabel} onChange={(e) => p.onTrueLabel(e.target.value)}>
              <option value="">No la conozco</option>
              {info.classes.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
            {real ? (
              <div className="comparison-result" aria-live="polite">
                <div className="compare-item"><small>ETIQUETA REAL (INDICADA POR TI)</small><b>{real.name}</b></div>
                <div className="compare-item"><small>PREDICCIÓN DEL MODELO</small><b>{r.prediction.label_es}{v.inconclusive ? ' (no concluyente)' : ''}</b></div>
                <p className={match ? 'match-state' : 'mismatch-state'}>
                  {match
                    ? v.inconclusive
                      ? 'La opción más probable coincide, aunque el modelo no estaba seguro.'
                      : 'La clasificación coincide con la etiqueta indicada.'
                    : `El modelo no coincide: asignó ${percentLabel(r.probabilities.find((x) => x.label === real.code)?.probability ?? 0)} % a ${real.name}.`}
                </p>
              </div>
            ) : (
              <div className="unknown-label"><FlaskConical size={16} /><span>Sin etiqueta de referencia: el resultado no se puede comprobar.</span></div>
            )}
          </div>

          <button className="primary-button full-button" onClick={p.onReport}><FileText size={17} /> Ver reporte <ArrowRight size={17} /></button>
          <div className="result-actions">
            <button className="secondary-button" onClick={p.onAnother}><RefreshCw size={16} /> Analizar otra imagen</button>
            <button className="text-button" onClick={p.onChangeCrop}>Cambiar cultivo <ChevronRight size={15} /></button>
            <button className="text-button push-right" onClick={p.onAbout}>Sobre el modelo <ChevronRight size={15} /></button>
          </div>
        </div>
      </div>
    </section>
  )
}
