import { Sprout } from 'lucide-react'
import type { ServiceStatus } from '@/lib/api'

const ESTADOS: Record<ServiceStatus, string> = {
  checking: 'Verificando servicio…',
  online: 'Modelos activos',
  degraded: 'Servicio parcial',
  offline: 'Servicio sin conexión',
}

export function Topbar({ status, onHome, onAbout }: { status: ServiceStatus; onHome: () => void; onAbout: () => void }) {
  return (
    <header className="topbar">
      <button className="brand" onClick={onHome} aria-label="BeanCass AI, inicio">
        <span className="brand-mark"><Sprout size={21} strokeWidth={2.2} /></span>
        <span>BeanCass <b>AI</b></span>
      </button>
      <div className="top-right">
        <span className={`prototype-pill is-${status}`} role="status" aria-live="polite">
          <span aria-hidden="true" /> {ESTADOS[status]}
        </span>
        <span className="top-divider" />
        <button className="model-caption about-trigger" onClick={onAbout}>Sobre los modelos</button>
      </div>
    </header>
  )
}
