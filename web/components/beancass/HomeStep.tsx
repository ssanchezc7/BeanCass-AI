import { ArrowRight, CircleAlert } from 'lucide-react'
import { CROPS_CONTENT } from '@/lib/cultivos'
import type { Crop } from '@/lib/tipos'

export function HomeStep({ onChoose, onAbout }: { onChoose: (crop: Crop) => void; onAbout: () => void }) {
  return (
    <section className="home-page page-width">
      <div className="hero-copy">
        <div className="eyebrow"><span className="eyebrow-line" /> AGRICULTURA + TECNOLOGÍA</div>
        <h1 tabIndex={-1}>Una mirada más clara<br />a la salud de tus <em>cultivos.</em></h1>
        <p className="hero-description">Clasifica condiciones foliares de fréjol y yuca con modelos de visión entrenados.</p>
      </div>
      <div className="crop-grid">
        {(['bean', 'cassava'] as Crop[]).map((key, i) => {
          const c = CROPS_CONTENT[key]
          return (
            <article className={`crop-card crop-${key}`} key={key}>
              <div className="crop-photo-wrap">
                <img src={c.image} alt={`Hoja de ${c.name.toLowerCase()}`} />
                <span className="photo-index">0{i + 1} / CULTIVO</span>
              </div>
              <div className="crop-card-content">
                <div>
                  <span className="crop-english">{c.english}</span>
                  <h2>{c.name}</h2>
                  <p>{c.classesSummary}</p>
                </div>
                <button className="round-arrow" aria-label={`Comenzar con ${c.name}`} onClick={() => onChoose(key)}>
                  <ArrowRight size={20} />
                </button>
              </div>
              <button className="card-cta" onClick={() => onChoose(key)} tabIndex={-1} aria-hidden="true">
                Comenzar <ArrowRight size={15} />
              </button>
            </article>
          )
        })}
      </div>
      <div className="notice">
        <CircleAlert size={17} />
        <span>
          <b>Resultado orientativo:</b> basado en modelos entrenados; no es un diagnóstico.{' '}
          <button className="inline-link" onClick={onAbout}>Sobre los modelos</button>
        </span>
      </div>
      <div className="home-footer"><span>Exploración educativa</span><span>Dos cultivos · Dos modelos entrenados</span></div>
    </section>
  )
}
