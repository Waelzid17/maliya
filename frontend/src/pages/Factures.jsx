import { useMemo, useState } from 'react'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Attente, Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateCourte, dateLongue, dh, pluriel } from '../format'

function Tampon({ f }) {
  if (f.datePaiement) return <span className="tampon paye">Payée le {dateCourte(f.datePaiement)}</span>
  const j = Number(f.joursDepasses)
  if (j > 0) return <span className="tampon retard">Échue depuis {pluriel(j, 'jour')}</span>
  if (j === 0) return <span className="tampon bientot">Échue aujourd'hui</span>
  return <span className="tampon bientot">À payer dans {pluriel(-j, 'jour')}</span>
}

function Facture({ f, prevision, onEncaisse }) {
  const [relance, setRelance] = useState(null)
  const [occupe, setOccupe] = useState(false)
  const [erreur, setErreur] = useState(null)
  const { annoncer } = useMaliya()

  async function rediger() {
    setOccupe(true)
    setErreur(null)
    try {
      setRelance(await api.ia.relance(f.id))
    } catch (e) {
      setErreur(e)
    } finally {
      setOccupe(false)
    }
  }

  async function encaisser() {
    setOccupe(true)
    try {
      await api.encaisser(f.id)
      onEncaisse(f)
    } catch (e) {
      setErreur(e)
    } finally {
      setOccupe(false)
    }
  }

  return (
    <article className="facture">
      <div>
        <div className="facture-titre">
          {f.client} <span className="discret" style={{ fontWeight: 500 }}>· {f.numero}</span>
        </div>
        <div className="discret petit">
          {f.objet}
          {f.projet && <> — {f.projet}</>}
        </div>
        <div style={{ marginTop: '0.4rem', display: 'flex', gap: '0.9rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <Tampon f={f} />
          <span className="discret petit">Émise le {dateCourte(f.dateEmission)}, échéance le {dateCourte(f.dateEcheance)}</span>
        </div>
        {prevision && (
          <p className="ecrit-main" style={{ margin: '0.5rem 0 0' }}>
            Je la vois payée vers le {dateLongue(prevision.date_paiement_probable).replace(/ \d{4}$/, '')}
            {prevision.risque !== 'faible' && <> — risque {prevision.risque}</>}. {prevision.risque !== 'faible' && prevision.raison}
          </p>
        )}
        {!f.datePaiement && (
          <div className="facture-actions">
            <button className="bouton-lien ia" onClick={rediger} disabled={occupe}>
              {Number(f.joursDepasses) > 0 ? 'Rédiger une relance' : 'Préparer un rappel'}
            </button>
            <button className="bouton-lien" onClick={encaisser} disabled={occupe}>Marquer comme payée</button>
          </div>
        )}
        <Erreur erreur={erreur} />
        {relance && (
          <div>
            <div className="brouillon">{relance.message}</div>
            <div className="facture-actions">
              <span className="discret petit">Ton {relance.ton}, à envoyer plutôt par {relance.canal_conseille}. Rien ne part sans toi.</span>
              <button
                className="bouton-lien"
                onClick={() => {
                  navigator.clipboard?.writeText(relance.message)
                  annoncer('Relance copiée')
                }}
              >
                Copier le texte
              </button>
              <a className="bouton-lien" href={`https://wa.me/?text=${encodeURIComponent(relance.message)}`} target="_blank" rel="noreferrer">
                Ouvrir dans WhatsApp
              </a>
            </div>
          </div>
        )}
      </div>
      <div className="facture-montant">{dh(f.montantTtc)}</div>
    </article>
  )
}

export default function Factures() {
  const { structureId, version, rafraichir, annoncer } = useMaliya()
  const [etat, setEtat] = useState('OUVERTES')
  const factures = useDonnees(() => api.factures(structureId, etat === 'TOUTES' ? null : etat), [structureId, etat, version])
  const previsions = useDonnees(() => api.ia.paiements(structureId), [structureId, version])
  const parId = useMemo(() => Object.fromEntries((previsions.donnees || []).map((p) => [p.facture_id, p])), [previsions.donnees])

  const ouvertes = (previsions.donnees || [])
  const enRetard = ouvertes.filter((p) => p.jours_depasses > 0)
  const risquees = ouvertes.filter((p) => p.risque === 'élevé')
  const attendu30 = ouvertes
    .filter((p) => p.retard_prevu - p.jours_depasses <= 30) // jours restants avant le paiement prévu
    .reduce((s, p) => s + p.montant_ttc, 0)

  const marge = (
    <div className="notes-marge">
      {previsions.charge && <Griffonnage>Je regarde qui paie quand…</Griffonnage>}
      {enRetard.length > 0 && (
        <div className="note" data-gravite="URGENT">
          <p className="note-titre">{dh(enRetard.reduce((s, p) => s + p.montant_ttc, 0))} en retard.</p>
          <p className="note-texte">{enRetard.map((p) => p.client).filter((c, i, a) => a.indexOf(c) === i).join(', ')}.</p>
        </div>
      )}
      {risquees.map((p) => (
        <div className="note" data-gravite="ATTENTION" key={p.facture_id}>
          <p className="note-titre">{p.numero}</p>
          <p className="note-texte">{p.raison}</p>
        </div>
      ))}
      {ouvertes.length > 0 && (
        <Griffonnage>
          Ce que je pense voir arriver dans le mois : environ {dh(attendu30)}. Mes estimations se trompent en moyenne de quelques jours.
        </Griffonnage>
      )}
    </div>
  )

  return (
    <Feuille etiquette="Factures" marge={marge}>
      <h1>Factures</h1>
      <p className="chapeau">Ce qu'on te doit, ce qui est réglé, et quand Maliya pense que l'argent arrivera.</p>
      <div className="filtres">
        <div className="onglets-etat" role="group" aria-label="Afficher">
          <button aria-pressed={etat === 'OUVERTES'} onClick={() => setEtat('OUVERTES')}>À encaisser</button>
          <button aria-pressed={etat === 'PAYEES'} onClick={() => setEtat('PAYEES')}>Payées</button>
          <button aria-pressed={etat === 'TOUTES'} onClick={() => setEtat('TOUTES')}>Toutes</button>
        </div>
      </div>
      {factures.charge && !factures.donnees && <Attente texte="Je sors les factures" />}
      <Erreur erreur={factures.erreur} recharger={factures.recharger} />
      {factures.donnees?.length === 0 && <p className="vide">{etat === 'OUVERTES' ? 'Tout est encaissé. Bravo.' : 'Aucune facture ici.'}</p>}
      <div>
        {(factures.donnees || []).map((f) => (
          <Facture
            key={f.id}
            f={f}
            prevision={parId[f.id]}
            onEncaisse={(x) => {
              annoncer(`${x.numero} marquée payée, encaissement ajouté au grand livre`)
              rafraichir()
            }}
          />
        ))}
      </div>
    </Feuille>
  )
}
