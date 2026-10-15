import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Attente, Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateCourte, dh, joliLibelle, moisLong } from '../format'

function derniersMois(ref, n = 6) {
  const [a, m] = ref.split('-').map(Number)
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(a, m - 1 - i, 1)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })
}

function Analyse({ structureId, version }) {
  const [mois, setMois] = useState('')
  const rca = useDonnees(() => api.ia.rca(structureId, mois || undefined), [structureId, mois, version])
  const r = rca.donnees
  const choix = r ? derniersMois(r.periode.mois) : []
  return (
    <section className="section" aria-labelledby="titre-rca">
      <div className="section-entete">
        <h2 id="titre-rca">Pourquoi ça a bougé</h2>
        {r && (
          <label className="petit">
            <span className="visuellement-cache">Période</span>
            <select className="champ-cadre" value={mois} onChange={(e) => setMois(e.target.value)}>
              <option value="">Ce mois-ci</option>
              {choix.slice(1).map((m) => (
                <option key={m} value={m}>{moisLong(m)}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      {rca.charge && !r && <Attente texte="Je remonte la piste" />}
      <Erreur erreur={rca.erreur} recharger={rca.recharger} />
      {r && (
        <>
          <p className="verdict">{r.resume}</p>
          <p className="discret petit" style={{ marginTop: '0.4rem' }}>
            {r.periode.libelle.charAt(0).toUpperCase() + r.periode.libelle.slice(1)} : {dh(r.net_actuel, { signe: true })}, contre {dh(r.net_precedent, { signe: true })} {r.periode.compare_a}.
          </p>
          {r.causes.length > 0 && (
            <ol className="chaine" style={{ marginTop: '1.5rem' }}>
              {r.causes.map((c) => (
                <li key={c.categorie}>
                  <h3>{c.titre}</h3>
                  <p style={{ margin: '0.25rem 0 0', maxWidth: '64ch' }}>{c.explication}</p>
                  {c.preuves.length > 0 && (
                    <div className="preuves">
                      {c.preuves.slice(0, 6).map((p) => (
                        <span className="preuve" key={`${p.type}${p.id}`}>
                          {p.type === 'facture' ? 'Facture ' : ''}
                          {p.type === 'facture' ? p.libelle : joliLibelle(p.libelle)} · {dh(p.montant)} · {dateCourte(p.date)}
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
          {r.compensations.length > 0 && (
            <p className="discret" style={{ marginTop: '1.25rem' }}>
              Ce qui a compensé : {r.compensations.map((c) => c.titre.toLowerCase()).join(', ')}.
            </p>
          )}
        </>
      )}
    </section>
  )
}

export default function Signaux() {
  const { structureId, version } = useMaliya()
  const anomalies = useDonnees(() => api.ia.anomalies(structureId), [structureId, version])
  const liste = anomalies.donnees || []

  const marge = (
    <div className="notes-marge">
      <Griffonnage>
        Pour chaque cause, je montre les mouvements et les factures qui la prouvent. Je ne calcule rien de tête : tout vient de ton grand livre.
      </Griffonnage>
      {liste.length > 0 && (
        <Griffonnage>
          {liste.length === 1 ? 'Un mouvement me paraît bizarre.' : `${liste.length} mouvements me paraissent bizarres.`} Je croise deux modèles, une forêt d'isolement et un autoencodeur, avant de signaler quoi que ce soit.
        </Griffonnage>
      )}
    </div>
  )

  return (
    <Feuille etiquette="Signaux" marge={marge}>
      <h1>Signaux</h1>
      <p className="chapeau">Ce qui explique les variations de ta trésorerie, et les mouvements qui sortent de l'ordinaire.</p>

      <Analyse structureId={structureId} version={version} />

      <hr className="rature" />

      <section aria-labelledby="titre-anomalies">
        <h2 id="titre-anomalies">À vérifier</h2>
        {anomalies.charge && !anomalies.donnees && <Attente texte="Je cherche ce qui cloche" />}
        <Erreur erreur={anomalies.erreur} recharger={anomalies.recharger} />
        {anomalies.donnees && liste.length === 0 && <p className="vide">Rien d'anormal sur les deux derniers mois.</p>}
        {liste.map((a) => (
          <div className="anomalie" key={a.transaction_id}>
            <div>
              <div style={{ fontWeight: 700 }}>
                {joliLibelle(a.libelle)} <span className="discret" style={{ fontWeight: 500 }}>· {a.structure} · {dateCourte(a.date)}</span>
              </div>
              <p className="ecrit-main" style={{ margin: '0.2rem 0 0' }}>{a.raisons.join(' ')}</p>
              {a.raisons.some((x) => x.includes('catégorie')) && (
                <Link className="note-action" to="/mouvements?a_classer=1">Le classer</Link>
              )}
            </div>
            <div style={{ fontWeight: 800 }}>{dh(a.montant)}</div>
          </div>
        ))}
      </section>
    </Feuille>
  )
}
