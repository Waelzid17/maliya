import { useEffect, useMemo, useRef, useState } from 'react'
import { compact } from '../format'

function pasJoli(etendue, cible = 4) {
  const brut = etendue / cible
  const p = 10 ** Math.floor(Math.log10(brut || 1))
  const n = brut / p
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * p
}

const chemin = (pts, sx, sy) =>
  pts.map((p, i) => `${i ? 'L' : 'M'}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ')

/**
 * Courbe en SVG, dessinée comme au crayon.
 * series : [{ points: [{x, y}], classe: 'trace' | 'trace-prevision' | 'trace-scenario', anime }]
 * bande  : [{ x, bas, haut }] — fourchette d'incertitude
 * reperes: [{ x, libelle }] — étiquettes de l'axe horizontal
 * survol : (x) => texte de la bulle pour le point le plus proche (sur la première série)
 */
export default function Courbe({ series, bande = [], reperes = [], hauteur = 260, survol, titre }) {
  const boite = useRef(null)
  const [largeur, setLargeur] = useState(720)
  const [actif, setActif] = useState(null)

  useEffect(() => {
    if (!boite.current) return
    const obs = new ResizeObserver(([e]) => setLargeur(Math.max(320, Math.round(e.contentRect.width))))
    obs.observe(boite.current)
    return () => obs.disconnect()
  }, [])

  const m = { g: 48, d: 14, h: 14, b: 30 }
  const calc = useMemo(() => {
    const xs = [...series.flatMap((s) => s.points.map((p) => p.x)), ...bande.map((b) => b.x)]
    const ys = [...series.flatMap((s) => s.points.map((p) => p.y)), ...bande.flatMap((b) => [b.bas, b.haut])]
    if (!xs.length) return null
    const xmin = Math.min(...xs)
    const xmax = Math.max(...xs)
    let ymin = Math.min(...ys)
    let ymax = Math.max(...ys)
    const marge = (ymax - ymin) * 0.12 || Math.abs(ymax) * 0.1 || 1
    ymin -= marge
    ymax += marge
    if (ymin > 0 && ymin < (ymax - ymin) * 0.6) ymin = 0
    const pas = pasJoli(ymax - ymin)
    const ticks = []
    for (let v = Math.ceil(ymin / pas) * pas; v <= ymax; v += pas) ticks.push(v)
    return { xmin, xmax: xmax === xmin ? xmin + 1 : xmax, ymin, ymax, ticks }
  }, [series, bande])

  if (!calc) return null
  const sx = (x) => m.g + ((x - calc.xmin) / (calc.xmax - calc.xmin)) * (largeur - m.g - m.d)
  const sy = (y) => m.h + ((calc.ymax - y) / (calc.ymax - calc.ymin)) * (hauteur - m.h - m.b)

  const reference = series[0]?.points || []
  const bouger = (evt) => {
    if (!survol || !reference.length) return
    const r = evt.currentTarget.getBoundingClientRect()
    const x = ((evt.clientX - r.left) / r.width) * largeur
    let meilleur = null
    for (const s of series) {
      for (const p of s.points) {
        const d = Math.abs(sx(p.x) - x)
        if (!meilleur || d < meilleur.d) meilleur = { d, p }
      }
    }
    setActif(meilleur?.p || null)
  }

  const bandePath = bande.length
    ? `${bande.map((b, i) => `${i ? 'L' : 'M'}${sx(b.x).toFixed(1)},${sy(b.haut).toFixed(1)}`).join(' ')} ${[...bande]
        .reverse()
        .map((b) => `L${sx(b.x).toFixed(1)},${sy(b.bas).toFixed(1)}`)
        .join(' ')} Z`
    : null

  return (
    <div ref={boite} style={{ position: 'relative' }}>
      <svg
        className="courbe"
        viewBox={`0 0 ${largeur} ${hauteur}`}
        role="img"
        aria-label={titre}
        onMouseMove={bouger}
        onMouseLeave={() => setActif(null)}
      >
        <g className="axe">
          {calc.ticks.map((t) => (
            <g key={t}>
              <line className="grille" x1={m.g} x2={largeur - m.d} y1={sy(t)} y2={sy(t)} />
              <text x={m.g - 8} y={sy(t) + 4} textAnchor="end">
                {compact(t)}
              </text>
            </g>
          ))}
          {reperes.map((r) => (
            <text key={r.x} x={sx(r.x)} y={hauteur - 8} textAnchor="middle">
              {r.libelle}
            </text>
          ))}
        </g>
        {calc.ymin < 0 && calc.ymax > 0 && <line className="zero" x1={m.g} x2={largeur - m.d} y1={sy(0)} y2={sy(0)} />}
        {bandePath && <path className="bande" d={bandePath} />}
        {series.map((s, i) => (
          <path
            key={i}
            className={`${s.classe || 'trace'}${s.anime ? ' trace-anime' : ''}`}
            d={chemin(s.points, sx, sy)}
            pathLength={s.anime ? 1 : undefined}
          />
        ))}
        {actif && (
          <>
            <line x1={sx(actif.x)} x2={sx(actif.x)} y1={m.h} y2={hauteur - m.b} stroke="var(--seyes)" />
            <circle className="point-survol" cx={sx(actif.x)} cy={sy(actif.y)} r="4.5" />
          </>
        )}
      </svg>
      {actif && survol && (
        <div className="bulle" style={{ left: `${(sx(actif.x) / largeur) * 100}%`, top: `${(sy(actif.y) / hauteur) * 100}%` }}>
          {survol(actif)}
        </div>
      )}
    </div>
  )
}
