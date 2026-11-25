'use client'

import { useEffect, useRef } from 'react'
import { FlaskConical, X } from 'lucide-react'
import { CROPS_CONTENT, GENERAL_LIMITATIONS } from '@/lib/cultivos'
import type { Crop } from '@/lib/tipos'

function pct(n: number) {
  return `${(n * 100).toFixed(2).replace('.', ',')} %`
}

export function AboutModelDialog({ open, onClose, focusCrop }: { open: boolean; onClose: () => void; focusCrop?: Crop }) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])

  const orden: Crop[] = focusCrop === 'cassava' ? ['cassava', 'bean'] : ['bean', 'cassava']

  return (
    <dialog
      ref={ref}
      className="about-dialog"
      aria-labelledby="about-title"
      onClose={onClose}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="about-inner">
        <div className="about-head">
          <div>
            <span className="result-overline">ESTUDIO COMPARATIVO · UNEMI</span>
            <h2 id="about-title">Sobre los modelos</h2>
          </div>
          <button className="remove-photo" onClick={onClose} aria-label="Cerrar"><X size={18} /></button>
        </div>
        <p className="about-lead">
          Se compararon una CNN propia, MobileNetV2, EfficientNetB0 y DenseNet121 por cultivo. El modelo de cada cultivo se
          eligió con el conjunto de Validation; las métricas de Test se midieron una sola vez sobre el modelo elegido.
        </p>
        <div className="about-grid">
          {orden.map((crop) => {
            const c = CROPS_CONTENT[crop]
            const m = c.metricsTest
            return (
              <section className="about-card" key={crop} aria-labelledby={`about-${crop}`}>
                <div className="model-chip"><FlaskConical size={16} /><span><small>{c.name.toUpperCase()}</small><b id={`about-${crop}`}>{c.model}</b></span></div>
                <dl className="about-metrics">
                  <div><dt>Dataset</dt><dd>{c.dataset}</dd></div>
                  <div><dt>Clases</dt><dd>{c.classes.length}: {c.classes.map((x) => x.name).join(', ')}</dd></div>
                  <div><dt>Parámetros</dt><dd>{c.parameters}</dd></div>
                  <div><dt>Exactitud (Test)</dt><dd>{pct(m.accuracy)} · {m.images} imágenes</dd></div>
                  <div><dt>F1 macro (Test)</dt><dd>{m.f1Macro.toFixed(4).replace('.', ',')}</dd></div>
                  <div><dt>Errores</dt><dd>{m.errors} · enfermas clasificadas como sanas: {m.diseasedAsHealthy}</dd></div>
                </dl>
                <p className="about-note">{m.note}</p>
                <ul className="about-list">{c.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
              </section>
            )
          })}
        </div>
        <h3 className="about-subtitle">Limitaciones generales</h3>
        <ul className="about-list">{GENERAL_LIMITATIONS.map((l) => <li key={l}>{l}</li>)}</ul>
        <p className="about-credits">
          Proyecto de Inteligencia Artificial, Universidad Estatal de Milagro (UNEMI), Grupo 1: Daniela Geraldin Arriaga Alvarez,
          Frank Obed Cedeño Peña y Laddy Lisset Rocha León. Datasets: iCassava 2019 y Makerere AI Lab Beans.
        </p>
      </div>
    </dialog>
  )
}
