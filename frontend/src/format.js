const nombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 })
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
const MOIS_COURTS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']

/** 12400.5 -> "12 401 dh" */
export function dh(v, { signe = false } = {}) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—'
  const n = Number(v)
  const corps = `${nombre.format(Math.abs(Math.round(n)))}\u00a0dh`
  if (signe) return `${n >= 0 ? '+' : '−'}${corps}`
  return n < 0 ? `−${corps}` : corps
}

/** 438132 -> "438 k" pour les axes de graphique */
export function compact(v) {
  const n = Math.abs(v)
  const s = v < 0 ? '−' : ''
  if (n >= 1e6) return `${s}${(n / 1e6).toFixed(1).replace('.', ',')} M`
  if (n >= 1e3) return `${s}${Math.round(n / 1e3)} k`
  return `${s}${Math.round(n)}`
}

const dateLocale = (iso) => {
  const [a, m, j] = iso.split('-').map(Number)
  return new Date(a, m - 1, j)
}

export const dateCourte = (iso) => {
  if (!iso) return ''
  const d = dateLocale(iso)
  return `${d.getDate()} ${MOIS_COURTS[d.getMonth()]}`
}

export const dateLongue = (iso) => {
  if (!iso) return ''
  const d = dateLocale(iso)
  return `${d.getDate() === 1 ? '1er' : d.getDate()} ${MOIS[d.getMonth()]} ${d.getFullYear()}`
}

export const jourEnLettres = (iso) => {
  const d = dateLocale(iso)
  const j = JOURS[d.getDay()]
  return `${j.charAt(0).toUpperCase()}${j.slice(1)} ${d.getDate() === 1 ? '1er' : d.getDate()} ${MOIS[d.getMonth()]}`
}

export const moisCourt = (aaaamm) => {
  const [a, m] = aaaamm.split('-').map(Number)
  return `${MOIS_COURTS[m - 1]}${m === 1 ? ` ${String(a).slice(2)}` : ''}`
}

export const moisLong = (aaaamm) => {
  const [a, m] = aaaamm.split('-').map(Number)
  return `${MOIS[m - 1]} ${a}`
}

export const pluriel = (n, mot, motPluriel) => `${n} ${n > 1 ? motPluriel || `${mot}s` : mot}`

/** "CB AMAZON MKTPLACE EU" -> "Amazon Mktplace Eu" */
export function joliLibelle(lib = '') {
  return lib
    .replace(/^(CB|PRLV|VIR RECU|VIR|PAIEMENT|ACHAT)\s+/i, '')
    .toLowerCase()
    .replace(/(^|\s|\.)([a-zà-ÿ])/g, (m, a, b) => a + b.toUpperCase())
    .replace(/\b(Aws|Ui|Ux|Sre|Erp|Cnss|Tva|Dgi|Seo)\b/g, (m) => m.toUpperCase())
    .replace(/\b([a-z]{2}-\d{4}-\d{3})\b/gi, (m) => m.toUpperCase())
}
