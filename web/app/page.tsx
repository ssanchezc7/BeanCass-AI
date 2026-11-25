'use client'

import { useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, BadgeCheck, Check, ChevronRight, CircleAlert, Download, FileText, FlaskConical, ImagePlus, Leaf, LoaderCircle, RefreshCw, ShieldCheck, Sprout, Upload, X } from 'lucide-react'

type Crop = 'bean' | 'cassava'
type Stage = 'home' | 'upload' | 'result' | 'report'
type Photo = { src: string; name: string; sample: boolean; label?: string }

const cropInfo = {
  bean: { name: 'Fréjol', english: 'Beans', model: 'MobileNetV2', image: '/bean-leaf.png' },
  cassava: { name: 'Yuca', english: 'Cassava', model: 'EfficientNetB0', image: '/cassava-leaf.png' },
} as const

const beanScores = [
  { name: 'Roya', value: 87, color: 'green' },
  { name: 'Mancha angular', value: 8, color: 'gold' },
  { name: 'Hoja sana', value: 5, color: 'sage' },
]
const cassavaScores = [
  { name: 'CMD — mosaico', value: 78, color: 'green' },
  { name: 'CBB — tizón bacteriano', value: 8, color: 'gold' },
  { name: 'CBSD — estría marrón', value: 7, color: 'sage' },
  { name: 'CGM — daño por ácaro verde', value: 4, color: 'mint' },
  { name: 'Hoja sana', value: 3, color: 'slate' },
]

export default function Page() {
  const [stage, setStage] = useState<Stage>('home')
  const [crop, setCrop] = useState<Crop>('bean')
  const [photo, setPhoto] = useState<Photo | null>(null)
  const [checking, setChecking] = useState<false | 'confused' | 'correct'>(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const info = cropInfo[crop]

  function chooseCrop(next: Crop) {
    setCrop(next)
    setPhoto(null)
    setStage('upload')
  }
  function loadFile(file?: File) {
    if (!file || !['image/jpeg', 'image/png'].includes(file.type)) return
    const reader = new FileReader()
    reader.onload = () => setPhoto({ src: String(reader.result), name: file.name, sample: false })
    reader.readAsDataURL(file)
  }
  function setExample() {
    setPhoto({ src: info.image, name: `Ejemplo de ${info.name.toLowerCase()}`, sample: true, ...(crop === 'cassava' ? { label: 'CBB — tizón bacteriano' } : {}) })
  }
  function analyze() {
    if (!photo) return
    setAnalyzing(true)
    window.setTimeout(() => { setAnalyzing(false); setStage('result') }, 850)
  }
  function resetToUpload() { setChecking(false); setStage('upload') }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => setStage('home')} aria-label="BeanCass AI, inicio"><span className="brand-mark"><Sprout size={21} strokeWidth={2.2} /></span><span>BeanCass <b>AI</b></span></button>
        <div className="top-right"><span className="prototype-pill"><span /> Prototipo visual</span><span className="top-divider" /><span className="model-caption">Clasificación foliar</span></div>
      </header>

      {stage === 'home' && <section className="home-page page-width">
        <div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line" /> AGRICULTURA + TECNOLOGÍA</div><h1>Una mirada más clara<br />a la salud de tus <em>cultivos.</em></h1><p className="hero-description">Explora la clasificación de condiciones foliares de fréjol y yuca.</p></div>
        <div className="crop-grid">
          {(['bean', 'cassava'] as Crop[]).map((key, i) => <article className={`crop-card crop-${key}`} key={key}>
            <div className="crop-photo-wrap"><img src={cropInfo[key].image} alt={`Hoja de ${cropInfo[key].name.toLowerCase()}`} /><span className="photo-index">0{i + 1} / CULTIVO</span></div>
            <div className="crop-card-content"><div><span className="crop-english">{cropInfo[key].english}</span><h2>{cropInfo[key].name}</h2><p>{key === 'bean' ? 'Mancha angular · Roya · Hoja sana' : 'CBB · CBSD · CGM · CMD · Hoja sana'}</p></div><button className="round-arrow" aria-label={`Comenzar con ${cropInfo[key].name}`} onClick={() => chooseCrop(key)}><ArrowRight size={20} /></button></div>
            <button className="card-cta" onClick={() => chooseCrop(key)}>Comenzar <ArrowRight size={15} /></button>
          </article>)}
        </div>
        <div className="notice"><CircleAlert size={17} /><span><b>Prototipo visual:</b> los resultados mostrados son simulados.</span></div>
        <div className="home-footer"><span>Exploración educativa</span><span>Dos cultivos · Un recorrido visual</span></div>
      </section>}

      {stage === 'upload' && <section className="workflow-page page-width">
        <button className="back-link" onClick={() => setStage('home')}><ArrowLeft size={16} /> Volver al inicio</button>
        <div className="flow-heading"><div className="step-label">PASO 01 <span>—</span> FOTOGRAFÍA</div><h1>Empecemos con tu <em>hoja.</em></h1><p>Selecciona una fotografía clara de una hoja del cultivo elegido.</p></div>
        <div className="upload-layout"><div className="upload-main">
          <div className="selected-crop"><div className="selected-icon"><Leaf size={19} /></div><div><span>CULTIVO SELECCIONADO</span><strong>{info.name}</strong></div><button onClick={() => setStage('home')}>Cambiar</button></div>
          <div className={`dropzone ${dragging ? 'is-dragging' : ''} ${photo ? 'has-photo' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={(e) => { e.preventDefault(); setDragging(false); loadFile(e.dataTransfer.files[0]) }}>
            {photo ? <div className="preview-image-wrap"><img className="preview-image" src={photo.src} alt="Vista previa de la hoja seleccionada" /><div className="preview-file"><span className="file-thumb"><ImagePlus size={18} /></span><span><b>{photo.name}</b><small>{photo.sample ? 'Imagen de ejemplo' : 'Fotografía seleccionada'}</small></span><button className="remove-photo" aria-label="Quitar imagen" onClick={() => setPhoto(null)}><X size={17} /></button></div></div> : <button className="dropzone-inner" onClick={() => fileRef.current?.click()}><div className="upload-icon"><Upload size={23} /></div><strong>Arrastra tu imagen aquí</strong><span>o <u>selecciona un archivo</u> desde tu dispositivo</span><small>JPG o PNG · Solo para esta demostración</small></button>}
            <input ref={fileRef} className="sr-only" type="file" accept="image/jpeg,image/png" aria-label="Seleccionar imagen JPG o PNG" onChange={(e) => loadFile(e.target.files?.[0])} />
          </div>
          <button className="example-button" onClick={setExample}><ImagePlus size={16} /> Usar imagen de ejemplo</button>
          <div className="analysis-note"><ShieldCheck size={17} /><span>Tu fotografía se muestra únicamente como referencia visual. <b>No se analiza realmente.</b></span></div>
          <button className="primary-button analyze-button" disabled={!photo || analyzing} onClick={analyze}>{analyzing ? <><LoaderCircle size={18} className="spin" /> Preparando resultado de ejemplo…</> : <>Analizar imagen <ArrowRight size={17} /></>}</button>
        </div><aside className="upload-aside"><div className="aside-kicker">RECORRIDO</div><div className="steps"><div className="step active"><span>1</span><div><b>Fotografía</b><small>Selecciona una imagen</small></div></div><div className="step"><span>2</span><div><b>Resultado</b><small>Explora un ejemplo simulado</small></div></div>{crop === 'bean' && <div className="step"><span>3</span><div><b>Reporte</b><small>Vista previa del documento</small></div></div>}</div><div className="model-chip"><FlaskConical size={16} /><span><small>ARQUITECTURA DE REFERENCIA</small><b>{info.model}</b></span></div></aside></div>
      </section>}

      {stage === 'result' && photo && <section className="workflow-page result-page page-width">
        <button className="back-link" onClick={resetToUpload}><ArrowLeft size={16} /> Volver a la fotografía</button>
        <div className="result-top"><div><div className="step-label">PASO 02 <span>—</span> RESULTADO SIMULADO</div><h1>{crop === 'bean' ? 'Resultado orientativo' : <>Yuca — demostración<br className="mobile-break" /> experimental</>}</h1><p>{crop === 'bean' ? 'Una referencia visual de cómo se presentaría un resultado.' : 'Explora un ejemplo de predicción y sus posibles confusiones.'}</p></div><div className="simulated-tag"><span /> EJEMPLO SIMULADO</div></div>
        <div className="result-grid"><div className="result-photo-panel"><img src={photo.src} alt="Fotografía seleccionada para la demostración" /><div className="photo-caption"><ImagePlus size={15} /><span>Fotografía original</span><small>{photo.name}</small></div><div className="image-unchanged"><Check size={13} /> Proporción original conservada</div></div>
          <div className="result-content"><div className="result-crop-label"><Leaf size={16} /> {info.name.toUpperCase()}</div><div className="prediction-card"><div className="prediction-top"><div><span className="result-overline">CATEGORÍA SIMULADA</span><h2>{crop === 'bean' ? 'Roya' : 'CMD — mosaico'}</h2></div><div className="score-circle"><strong>{crop === 'bean' ? '87' : '78'}<small>%</small></strong></div></div><p className="prediction-description">{crop === 'bean' ? 'La imagen presenta características compatibles con roya.' : 'Predicción de ejemplo para visualizar la salida experimental.'}</p></div>
            <div className="scores-block"><div className="section-mini-heading"><b>Distribución de ejemplo</b><span>SIMULADA</span></div>{(crop === 'bean' ? beanScores : cassavaScores).map((item) => <div className="score-row" key={item.name}><div className="score-row-label"><span>{item.name}</span><b>{item.value}%</b></div><div className="score-track"><span className={`score-fill ${item.color}`} style={{ width: `${item.value}%` }} /></div></div>)}</div>
            {crop === 'bean' ? <><div className="disclaimer"><CircleAlert size={16} /><span>La puntuación del modelo no garantiza que la clasificación sea correcta.</span></div><div className="info-card"><div className="info-icon"><Leaf size={17} /></div><div><b>Sobre la roya</b><p>La roya es una condición foliar que puede presentarse en el fréjol. Esta descripción es ilustrativa y no confirma la condición de la fotografía.</p><div className="info-subsections"><span>MANEJO <small>Información ilustrativa pendiente de revisión especializada.</small></span><span>PREVENCIÓN <small>Contenido ilustrativo; no constituye una recomendación.</small></span></div></div></div><button className="primary-button full-button" onClick={() => setStage('report')}><FileText size={17} /> Ver reporte <ArrowRight size={17} /></button></> : <><div className="disclaimer"><FlaskConical size={16} /><span>Este módulo permite explorar las predicciones y sus posibles confusiones.</span></div><div className="comparison-card"><div className="comparison-heading"><span>COMPROBACIÓN DE EJEMPLOS</span><span className="simulated-mini">SIMULADO</span></div>{photo.sample ? checking ? <div className="comparison-result"><div className="compare-item"><small>CLASE REAL DEL EJEMPLO</small><b>{photo.label ?? 'CBB — tizón bacteriano'}</b></div><div className="compare-item"><small>PREDICCIÓN SIMULADA</small><b>{checking === 'correct' ? 'CBB — tizón bacteriano' : 'CMD — mosaico'}</b></div><p className={checking === 'correct' ? 'match-state' : 'mismatch-state'}>{checking === 'correct' ? 'En este ejemplo, la clasificación coincide.' : 'En este ejemplo, el modelo se confundió entre dos categorías.'}</p></div> : <><p>Compara estados simulados usando una etiqueta de referencia conocida.</p><div className="compare-actions"><button onClick={() => setChecking('confused')}>Ver ejemplo confundido</button><button onClick={() => setChecking('correct')}>Ver ejemplo correcto</button></div></> : <div className="unknown-label"><CircleAlert size={16} /><span>No hay una etiqueta de referencia para comprobar este resultado.</span></div>}</div></>}
            <div className="result-actions"><button className="secondary-button" onClick={resetToUpload}><RefreshCw size={16} /> Analizar otra imagen</button><button className="text-button" onClick={() => { setPhoto(null); setChecking(false); setStage('home') }}>Cambiar cultivo <ChevronRight size={15} /></button></div>
          </div>
        </div>
      </section>}

      {stage === 'report' && photo && crop === 'bean' && <section className="report-page page-width"><div className="report-toolbar"><button className="back-link" onClick={() => setStage('result')}><ArrowLeft size={16} /> Volver al resultado</button><button className="download-button" onClick={() => window.alert('Descarga disponible en la versión funcional')}><Download size={16} /> Descargar PDF</button></div><div className="report-sheet"><div className="report-brand"><span className="brand-mark"><Sprout size={18} /></span><b>BeanCass <span>AI</span></b><small>MUESTRA DEL REPORTE — DATOS SIMULADOS</small></div><div className="report-rule" /><div className="report-title"><span>REPORTE DE CLASIFICACIÓN ORIENTATIVA</span><h1>Observación foliar<br />de fréjol</h1><p>Fecha de demostración: {new Intl.DateTimeFormat('es-EC', { dateStyle: 'long' }).format(new Date())}</p></div><div className="report-crop-line"><span>CULTIVO <b>Fréjol (Beans)</b></span><span>MODELO DE REFERENCIA <b>MobileNetV2</b></span></div><div className="report-image-frame"><img src={photo.src} alt="Fotografía original incluida en el reporte" /></div><div className="report-result-line"><div><small>CATEGORÍA SIMULADA</small><h2>Roya</h2><p>La imagen presenta características compatibles con roya.</p></div><div className="report-score">87<small>%</small></div></div><div className="report-columns"><div><h3>Factores asociados</h3><p>Contenido ilustrativo pendiente de revisión y validación especializada. No representa un diagnóstico confirmado.</p></div><div><h3>Cuidados generales</h3><p>Información ilustrativa. Esta muestra no incluye tratamientos ni recomendaciones específicas.</p></div></div><div className="report-warning"><CircleAlert size={17} /><p>Este resultado es simulado y no sustituye una revisión especializada. La puntuación no garantiza que la clasificación sea correcta.</p></div><div className="report-footer"><span>BeanCass AI · Muestra educativa</span><span>01 / 01</span></div></div></section>}

      <footer className="site-footer"><span>BeanCass AI <span className="footer-dot">·</span> Prototipo universitario</span><span>Los resultados son simulados y no constituyen un diagnóstico.</span></footer>
    </main>
  )
}
