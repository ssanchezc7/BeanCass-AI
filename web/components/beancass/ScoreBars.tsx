import { SCORE_COLORS, percentLabel } from '@/lib/cultivos'
import type { ApiProbability } from '@/lib/tipos'

export function ScoreBars({ probabilities, tag }: { probabilities: ApiProbability[]; tag: string }) {
  return (
    <div className="scores-block">
      <div className="section-mini-heading">
        <b id="dist-heading">Distribución de probabilidades</b>
        <span>{tag.toUpperCase()}</span>
      </div>
      <ul className="score-list" aria-labelledby="dist-heading">
        {probabilities.map((item, i) => (
          <li className="score-row" key={item.label}>
            <div className="score-row-label">
              <span>{item.label_es}</span>
              <b>{percentLabel(item.probability)}%</b>
            </div>
            <div
              className="score-track"
              role="progressbar"
              aria-label={item.label_es}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(item.probability * 100)}
            >
              <span
                className={`score-fill ${SCORE_COLORS[i % SCORE_COLORS.length]}`}
                style={{ width: `${Math.max(0, Math.min(100, item.probability * 100))}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
