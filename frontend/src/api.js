// Toutes les données passent par le backend Spring Boot (/api). Les routes /api/ia/* sont relayées au service IA.

async function appel(chemin, options = {}) {
  let reponse
  try {
    reponse = await fetch(`/api${chemin}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    })
  } catch {
    throw new Error("Le serveur ne répond pas. Vérifie que le backend tourne sur le port 8080.")
  }
  const texte = await reponse.text()
  const donnees = texte ? JSON.parse(texte) : null
  if (!reponse.ok) {
    const message = donnees?.message || donnees?.detail || `Erreur ${reponse.status}`
    throw new Error(message)
  }
  return donnees
}

const qs = (params) => {
  const p = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, v)
  })
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const api = {
  structures: () => appel('/structures'),
  creerStructure: (s) => appel('/structures', { method: 'POST', body: s }),
  tableauDeBord: (structureId) => appel(`/tableau-de-bord${qs({ structureId })}`),
  mouvements: (filtres) => appel(`/mouvements${qs(filtres)}`),
  creerMouvement: (m) => appel('/mouvements', { method: 'POST', body: m }),
  modifierMouvement: (id, m) => appel(`/mouvements/${id}`, { method: 'PATCH', body: m }),
  validerPropositions: (propositions) => appel('/mouvements/valider-propositions', { method: 'POST', body: { propositions } }),
  factures: (structureId, etat) => appel(`/factures${qs({ structureId, etat })}`),
  encaisser: (id) => appel(`/factures/${id}/encaisser`, { method: 'POST', body: {} }),
  projets: (structureId) => appel(`/projets${qs({ structureId })}`),
  categories: () => appel('/categories'),
  clients: () => appel('/clients'),

  ia: {
    briefing: (structure_id) => appel(`/ia/briefing${qs({ structure_id })}`),
    prevision: (structure_id, semaines = 13) => appel(`/ia/prevision${qs({ structure_id, semaines })}`),
    anomalies: (structure_id) => appel(`/ia/anomalies${qs({ structure_id })}`),
    paiements: (structure_id) => appel(`/ia/paiements${qs({ structure_id })}`),
    rca: (structure_id, mois) => appel(`/ia/rca${qs({ structure_id, mois })}`),
    aClasser: (structure_id) => appel(`/ia/a-classer${qs({ structure_id })}`),
    copilote: (question, structure_id) => appel('/ia/copilote', { method: 'POST', body: { question, structure_id } }),
    simulation: (structure_id, scenarios) => appel('/ia/simulation', { method: 'POST', body: { structure_id, scenarios } }),
    saisie: (texte) => appel('/ia/saisie', { method: 'POST', body: { texte } }),
    relance: (facture_id) => appel('/ia/relance', { method: 'POST', body: { facture_id } }),
    modeles: () => appel('/ia/modeles'),
  },
}
