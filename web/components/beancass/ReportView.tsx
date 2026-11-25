'use client'

import { ArrowLeft, CircleAlert, Download, Sprout } from 'lucide-react'
import { CROPS_CONTENT, classContent, percentLabel } from '@/lib/cultivos'
import type { Crop, Photo, PredictResponse } from '@/lib/tipos'
import { verdict } from './ResultStep'

interface Props {
  crop: Crop
  photo: Photo
  result: PredictResponse
  analyzedAt: Date
  trueLabel: string
  onBack: () => void
}

export function ReportView({ crop, photo, result, analyzedAt, trueLabel, onBack }: Props) {
  const info = CROPS_CONTENT[crop]
  const v = verdict(result)
  const top = classContent(crop, result.prediction.label)
  const real = trueLabel ? classContent(crop, trueLabel) : undefined
  const fecha = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeStyle: 'short' }).format(analyzedAt)

  function download() {
    const anterior = document.title
    const sello = analyzedAt.toISOString().slice(0, 16).replace(/[-:T]/g, '')
    document.title = `BeanCass-AI_reporte_${info.english.toLowerCase()}_${sello}`
    const restaurar = () => { document.title = anterior; window.removeEventListener('afterprint', restaurar) }
    window.addEventListener('afterprint', restaurar)
    window.print()
  }

  return (
    <section className="report-page page-width">
      <div className="report-toolbar">
        <button className="back-link" onClick={onBack}><ArrowLeft size={16} /> Volver al resultado</button>
        <button className="download-button" onClick={download} title="Abre el diálogo de impresión: elige «Guardar como PDF»">
          <Download size={16} /> Descargar PDF
        </button>
      </div>
      <article className="report-sheet" aria-label="Reporte de clasificación">
        <div className="report-brand">
          <span className="brand-mark"><Sprout size={18} /></span>
          <b>BeanCass <span>AI</span></b>
          <small>REPORTE ORIENTATIVO — NO ES UN DIAGNÓSTICO</small>
        </div>
        <div className="report-rule" />
        <div className="report-title">
          <span>REPORTE DE CLASIFICACIÓN ORIENTATIVA</span>
          <h1 tabIndex={-1}>Observación foliar<br />de {info.name.toLowerCase()}</h1>
          <p>Fecha del análisis: {fecha}</p>
        </div>
        <div className="report-crop-line">
          <span>CULTIVO <b>{info.name} ({info.english})</b></span>
          <span>MODELO <b>{result.model.name}</b></span>
          <span>IMAGEN <b>{result.image.width}×{result.image.height} px</b></span>
        </div>
        <div className="report-image-frame"><img src={photo.src} alt="Fotografía original incluida en el reporte" /></div>
        <div className="report-result-line">
          <div>
            <small>{v.overline}</small>
            <h2>{v.title}</h2>
            <p>{v.description ?? top?.description}</p>
          </div>
          <div className="report-score">{percentLabel(result.prediction.confidence)}<small>%</small></div>
        </div>
        <table className="report-probs">
          <caption>Probabilidades por categoría</caption>
          <tbody>
            {result.probabilities.map((p) => (
              <tr key={p.label}><th scope="row">{p.label_es}</th><td>{percentLabel(p.probability)} %</td></tr>
            ))}
          </tbody>
        </table>
        <div className="report-columns">
          <div>
            <h3>Síntomas asociados</h3>
            <p>{v.inconclusive ? 'No se describe una categoría porque el resultado no fue concluyente.' : top?.symptoms}</p>
          </div>
          <div>
            <h3>Recomendación</h3>
            <p>{v.inconclusive ? 'Repite la fotografía enfocando una sola hoja con buena luz.' : top?.advice}</p>
          </div>
        </div>
        {real && (
          <p className="report-note">
            Etiqueta indicada por el usuario: <b>{real.name}</b> — {real.code === result.prediction.label ? 'coincide' : 'no coincide'} con la predicción.
          </p>
        )}
        {result.quality.warnings.length > 0 && (
          <ul className="report-alerts">
            {result.quality.warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
        )}
        <div className="report-warning">
          <CircleAlert size={17} />
          <p>
            Resultado orientativo generado por un modelo entrenado con el dataset {info.dataset}. No sustituye la revisión de un técnico agrícola.
            La puntuación no garantiza que la clasificación sea correcta. Desempeño del modelo en Test: exactitud {(info.metricsTest.accuracy * 100).toFixed(2).replace('.', ',')} %,
            F1 macro {info.metricsTest.f1Macro.toFixed(4).replace('.', ',')}.
          </p>
        </div>
        <div className="report-footer"><span>BeanCass AI · Proyecto universitario UNEMI</span><span>01 / 01</span></div>
      </article>
    </section>
  )
}
