import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Courbe from '../composants/Courbe'
import Feuille from '../composants/Feuille'
import { Attente, Erreur } from '../composants/Etats'
import { Note } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateLongue, dh, jourEnLettres, moisCourt } from '../format'

const NOMS = { AGENCE: "l'agence", SOCIETE: 'la société', PROJET: 'le projet', PERSO: 'le perso' }

function finDeMois(aaaamm, ref) {
  const [a, m] = aaaamm.split('-').map(Number)
  const fin = new Date(a, m, 0)
  const r = new Date(ref)
  return (fin > r ? r : fin).getTime()
}

function Marge({ structureId }) {
  const b = useDonnees(() => api.ia.briefing(structureId), [structureId])
  if (b.charge) return <p className="ecrit-main">Je relis tes comptes…</p>
  if (b.erreur) return <p className="ecrit-main">Je n'arrive pas à joindre le service IA. Le reste de la page fonctionne.</p>
  return (
    <div className="notes-marge">
      <p className="salut">{b.donnees.salutation}</p>
      {b.donnees.notes.map((n) => (
        <Note key={n.id} note={n} />
      ))}
    </div>
  )
}

function Phrase({ tdb, structure }) {
  if (!structure) {
    return (
      <>
        <p className="phrase-solde">
          <span className="tu-as">Tu as </span>
          {dh(tdb.total)}
          <span className="tu-as"> en banque.</span>
        </p>
        <p className="repartition">
          {tdb.soldes.map((s, i) => (
            <span key={s.id}>
              <span className="pastille" style={{ background: s.couleur }} />
              {s.nom} {dh(s.solde)}
              {i < tdb.soldes.length - 1 ? ', ' : '. '}
            </span>
          ))}
          {tdb.moisDeDepensesCouverts && <>De quoi tenir {String(tdb.moisDeDepensesCouverts).replace('.', ',')} mois de dépenses.</>}
        </p>
      </>
    )
  }
  return (
    <>
      <p className="phrase-solde">
        <span className="tu-as">{structure.nom} a </span>
        {dh(tdb.total)}
        <span className="tu-as"> en banque.</span>
      </p>
      {tdb.moisDeDepensesCouverts && (
        <p className="repartition">
          De quoi tenir {String(tdb.moisDeDepensesCouverts).replace('.', ',')} mois de dépenses pour {NOMS[structure.type]}.
        </p>
      )}
    </>
  )
}

function Graphique({ tdb, structureId }) {
  const prev = useDonnees(() => api.ia.prevision(structureId), [structureId])
  const ref = tdb.dateReference
  const { series, bande, reperes } = useMemo(() => {
    const histo = tdb.serie.map((p) => ({ x: finDeMois(p.mois, ref), y: Number(p.soldeFin), mois: p.mois }))
    const s = [{ points: histo, classe: 'trace', anime: true }]
    let b = []
    if (prev.donnees) {
      const depart = { x: new Date(ref).getTime(), y: Number(tdb.total) }
      const pts = prev.donnees.prevision.filter((p) => new Date(p.semaine).getTime() > depart.x).map((p) => ({ x: new Date(p.semaine).getTime(), y: p.p50, semaine: p.semaine }))
      s.push({ points: [depart, ...pts], classe: 'trace-prevision', prevision: true })
      b = [{ x: depart.x, bas: depart.y, haut: depart.y }, ...prev.donnees.prevision.filter((p) => new Date(p.semaine).getTime() > depart.x).map((p) => ({ x: new Date(p.semaine).getTime(), bas: p.p10, haut: p.p90 }))]
    }
    const r = histo.filter((_, i) => i % 2 === 1).map((p) => ({ x: p.x, libelle: moisCourt(p.mois) }))
    return { series: s, bande: b, reperes: r }
  }, [tdb, prev.donnees, ref])

  return (
    <>
      <Courbe
        titre="Solde sur douze mois et prévision"
        series={series}
        bande={bande}
        reperes={reperes}
        survol={(p) => (p.mois ? `Fin ${moisCourt(p.mois)} : ${dh(p.y)}` : p.semaine ? `Semaine du ${dateLongue(p.semaine)} : ${dh(p.y)} prévus` : `Aujourd'hui : ${dh(p.y)}`)}
      />
      <div className="legende">
        <span><i />Solde en fin de mois</span>
        {prev.donnees && (
          <>
            <span><i className="pointille" />Prévision sur 13 semaines ({prev.donnees.moteur})</span>
            <span>Zone pâle : 8 chances sur 10 que le solde y tombe</span>
          </>
        )}
        {prev.charge && <span>Prévision en cours…</span>}
      </div>
    </>
  )
}

export default function Aujourdhui() {
  const { structureId, structure, version } = useMaliya()
  const navigate = useNavigate()
  const [question, setQuestion] = useState('')
  const tdb = useDonnees(() => api.tableauDeBord(structureId), [structureId, version])

  const t = tdb.donnees
  const postes = t ? t.depensesParCategorie.slice(0, 7) : []
  const maxPoste = postes.length ? Math.max(...postes.map((p) => Number(p.montant))) : 1
  const variation = (a, b) => {
    const d = Number(a) - Number(b)
    return d === 0 ? 'pareil que' : `${dh(Math.abs(d))} de ${d > 0 ? 'plus' : 'moins'} que`
  }

  return (
    <Feuille etiquette="Aujourd'hui" marge={<Marge structureId={structureId} />}>
      {tdb.charge && !t && <Attente />}
      <Erreur erreur={tdb.erreur} recharger={tdb.recharger} />
      {t && (
        <>
          <section className="section">
            <p className="date-du-jour">{jourEnLettres(t.dateReference)}</p>
            <Phrase tdb={t} structure={structure} />
          </section>

          <section className="section" aria-labelledby="titre-courbe">
            <h2 id="titre-courbe" className="visuellement-cache">Évolution du solde</h2>
            <Graphique tdb={t} structureId={structureId} />
          </section>

          <section className="section" aria-labelledby="titre-mois">
            <div className="section-entete">
              <h2 id="titre-mois">Ce mois-ci, jusqu'à aujourd'hui</h2>
            </div>
            <div className="colonnes">
              <div>
                <div className="chiffre positif">{dh(t.moisEnCours.entrees)}</div>
                <p className="chiffre-legende">encaissés, {variation(t.moisEnCours.entrees, t.moisEnCours.entreesPrecedent)} à la même date le mois dernier</p>
              </div>
              <div>
                <div className="chiffre">{dh(t.moisEnCours.sorties)}</div>
                <p className="chiffre-legende">dépensés, {variation(t.moisEnCours.sorties, t.moisEnCours.sortiesPrecedent)} à la même date le mois dernier</p>
              </div>
              <div>
                <div className={`chiffre ${Number(t.factures.enRetard) > 0 ? 'negatif' : ''}`}>{dh(t.factures.aEncaisser)}</div>
                <p className="chiffre-legende">
                  à encaisser sur {t.factures.nbOuvertes} factures
                  {Number(t.factures.nbEnRetard) > 0 && <>, dont {dh(t.factures.enRetard)} déjà échus</>}
                </p>
              </div>
            </div>
          </section>

          <section className="section" aria-labelledby="titre-postes">
            <h2 id="titre-postes">Où part l'argent ce mois-ci</h2>
            {postes.length === 0 ? (
              <p className="vide">Aucune dépense ce mois-ci pour l'instant.</p>
            ) : (
              <div className="postes">
                {postes.map((p) => (
                  <div className="poste" key={p.categorie}>
                    <span className="poste-nom">{p.categorie}</span>
                    <div className={`poste-barre ${p.code ? '' : 'inconnu'}`} style={{ width: `${(Number(p.montant) / maxPoste) * 100}%` }} />
                    <span className="poste-montant">{dh(p.montant)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <hr className="rature" />

          <form
            className="ligne-ecriture"
            onSubmit={(e) => {
              e.preventDefault()
              if (question.trim()) navigate(`/demander?q=${encodeURIComponent(question.trim())}`)
            }}
          >
            <label htmlFor="question-rapide" className="visuellement-cache">Poser une question à Maliya</label>
            <input
              id="question-rapide"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Une question ? « Pourquoi j'ai moins d'argent ce mois-ci ? »"
            />
            <button className="bouton" type="submit" disabled={!question.trim()}>Demander</button>
          </form>
        </>
      )}
    </Feuille>
  )
}
