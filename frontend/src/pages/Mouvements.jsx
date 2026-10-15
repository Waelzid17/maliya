import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Attente, Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateCourte, dateLongue, dh, joliLibelle, pluriel } from '../format'

const SOURCES = { SMS: 'SMS bancaire', WHATSAPP: 'WhatsApp', VOCAL: 'Note vocale', IMPORT: 'Relevé', MANUEL: 'Saisi à la main' }
const niveau = (c) => (c >= 0.6 ? 'sûr' : c >= 0.35 ? 'plutôt sûr' : 'à vérifier')

/** Dictée vocale du navigateur (Chrome, Edge, Safari). */
function useDictee(surTexte) {
  const [ecoute, setEcoute] = useState(false)
  const reco = useRef(null)
  const Reco = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  const basculer = () => {
    if (!Reco) return
    if (ecoute) {
      reco.current?.stop()
      return
    }
    const r = new Reco()
    r.lang = 'fr-FR'
    r.interimResults = false
    r.onresult = (e) => surTexte(e.results[0][0].transcript)
    r.onend = () => setEcoute(false)
    r.onerror = () => setEcoute(false)
    reco.current = r
    r.start()
    setEcoute(true)
  }
  return { disponible: Boolean(Reco), ecoute, basculer }
}

function Saisie({ structures, onEnregistre }) {
  const [texte, setTexte] = useState('')
  const [apercu, setApercu] = useState(null)
  const [structureChoisie, setStructureChoisie] = useState('')
  const [occupe, setOccupe] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [vocal, setVocal] = useState(false)
  const dictee = useDictee((t) => {
    setTexte(t)
    setVocal(true)
    analyser(t)
  })

  async function analyser(t = texte) {
    if (!t.trim()) return
    setOccupe(true)
    setErreur(null)
    try {
      const r = await api.ia.saisie(t)
      setApercu(r)
      setStructureChoisie(r.structure?.id ? String(r.structure.id) : '')
    } catch (e) {
      setErreur(e)
    } finally {
      setOccupe(false)
    }
  }

  async function enregistrer() {
    setOccupe(true)
    setErreur(null)
    try {
      const m = await api.creerMouvement({
        structureId: Number(structureChoisie),
        date: apercu.date,
        libelle: apercu.texte,
        montant: apercu.montant,
        categorieId: apercu.categorie.confiance >= 0.35 ? apercu.categorie.categorie_id : null,
        projetId: apercu.projet?.id ?? null,
        clientId: apercu.client?.id ?? null,
        source: vocal ? 'VOCAL' : 'MANUEL',
      })
      onEnregistre(m)
      setTexte('')
      setApercu(null)
    } catch (e) {
      setErreur(e)
    } finally {
      setOccupe(false)
    }
  }

  return (
    <section className="section" aria-labelledby="titre-saisie">
      <h2 id="titre-saisie">Noter un mouvement</h2>
      <form
        className="ligne-ecriture"
        onSubmit={(e) => {
          e.preventDefault()
          analyser()
        }}
      >
        <label htmlFor="saisie" className="visuellement-cache">Décris la dépense ou l'encaissement</label>
        <input
          id="saisie"
          value={texte}
          onChange={(e) => {
            setTexte(e.target.value)
            setVocal(false)
          }}
          placeholder="« khlesst 1200 dh l'hébergement dial projet kasbah lbare7 »"
          autoComplete="off"
        />
        {dictee.disponible && (
          <button type="button" className="micro" data-ecoute={dictee.ecoute} onClick={dictee.basculer} aria-label={dictee.ecoute ? 'Arrêter la dictée' : 'Dicter'}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
          </button>
        )}
        <button className="bouton" type="submit" disabled={occupe || !texte.trim()}>Comprendre</button>
      </form>
      <p className="discret petit" style={{ margin: '0.4rem 0 0' }}>
        En français, en darija ou en anglais. Maliya devine le montant, la date, le projet et la catégorie.
      </p>
      <Erreur erreur={erreur} />
      {apercu && (
        <div className="apercu">
          <Griffonnage>Voilà ce que je comprends :</Griffonnage>
          <dl>
            <dt>Montant</dt>
            <dd className={apercu.montant > 0 ? 'positif' : ''}>{apercu.montant ? dh(apercu.montant, { signe: true }) : 'pas trouvé'}</dd>
            <dt>Date</dt>
            <dd>{dateLongue(apercu.date)}</dd>
            <dt>Catégorie</dt>
            <dd>
              {apercu.categorie.categorie_libelle} <span className="par-ia">({apercu.categorie.niveau})</span>
            </dd>
            {apercu.projet && (
              <>
                <dt>Projet</dt>
                <dd>{apercu.projet.nom}</dd>
              </>
            )}
            {apercu.client && (
              <>
                <dt>Client</dt>
                <dd>{apercu.client.nom}</dd>
              </>
            )}
            <dt>
              <label htmlFor="structure-saisie">Structure</label>
            </dt>
            <dd>
              <select id="structure-saisie" className="champ-cadre" value={structureChoisie} onChange={(e) => setStructureChoisie(e.target.value)}>
                <option value="">Choisir…</option>
                {structures.map((s) => (
                  <option key={s.id} value={s.id}>{s.nom}</option>
                ))}
              </select>
            </dd>
          </dl>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <button className="bouton" onClick={enregistrer} disabled={occupe || !apercu.montant || !structureChoisie}>
              Enregistrer le mouvement
            </button>
            <button className="bouton-lien" onClick={() => setApercu(null)}>Annuler</button>
          </div>
        </div>
      )}
    </section>
  )
}

function Ligne({ m, proposition, categories, onModifie }) {
  const [edition, setEdition] = useState(false)
  const [occupe, setOccupe] = useState(false)

  async function choisir(categorieId) {
    setOccupe(true)
    try {
      onModifie(await api.modifierMouvement(m.id, { categorieId: Number(categorieId) }), 'Catégorie enregistrée')
      setEdition(false)
    } finally {
      setOccupe(false)
    }
  }

  async function accepter() {
    setOccupe(true)
    try {
      await api.validerPropositions([{ transactionId: m.id, categorieId: proposition.categorie_id, confiance: proposition.confiance }])
      onModifie({ ...m, categorieId: proposition.categorie_id, categorie: proposition.categorie_libelle, categorieParIa: true, confianceIa: proposition.confiance }, 'Proposition acceptée')
    } finally {
      setOccupe(false)
    }
  }

  const selecteur = (
    <select
      className="champ-cadre"
      aria-label="Choisir une catégorie"
      defaultValue=""
      disabled={occupe}
      onChange={(e) => e.target.value && choisir(e.target.value)}
      style={{ padding: '0.15rem 0.4rem', fontSize: 'var(--t-xs)' }}
    >
      <option value="">Choisir une catégorie…</option>
      {categories.map((c) => (
        <option key={c.id} value={c.id}>{c.libelle}</option>
      ))}
    </select>
  )

  return (
    <div className={`ligne-livre ${m.categorieId ? '' : 'a-classer'}`}>
      <span className="date">{dateCourte(m.date)}</span>
      <div style={{ minWidth: 0 }}>
        <div className="libelle" title={m.libelle}>{joliLibelle(m.libelle)}</div>
        <div className="meta">
          <span>
            <span className="pastille" style={{ background: m.couleur }} />
            {m.structure}
          </span>
          {m.categorieId && !edition && (
            <button className="etiquette-cat" onClick={() => setEdition(true)} style={{ cursor: 'pointer' }} title="Changer la catégorie">
              {m.categorie}
              {m.categorieParIa && <span className="par-ia"> · classé par Maliya ({niveau(Number(m.confianceIa || 0))})</span>}
            </button>
          )}
          {edition && selecteur}
          {m.projet && <span>{m.projet}</span>}
          {m.source !== 'IMPORT' && <span>{SOURCES[m.source] || m.source}</span>}
        </div>
        {!m.categorieId && (
          <div className="proposition">
            {proposition ? (
              <>
                <span className="ecrit-main">{proposition.categorie_libelle} ?</span>
                <button className="bouton-lien ia" onClick={accepter} disabled={occupe}>Oui, c'est ça</button>
                {selecteur}
              </>
            ) : (
              selecteur
            )}
          </div>
        )}
      </div>
      <span className={`montant ${Number(m.montant) > 0 ? 'positif' : ''}`}>{dh(m.montant, { signe: Number(m.montant) > 0 })}</span>
    </div>
  )
}

export default function Mouvements() {
  const { structureId, structures, version, rafraichir, annoncer } = useMaliya()
  const [params, setParams] = useSearchParams()
  const aClasser = params.get('a_classer') === '1'
  const [recherche, setRecherche] = useState('')
  const [rechercheActive, setRechercheActive] = useState('')
  const [categorieId, setCategorieId] = useState('')
  const [elements, setElements] = useState([])
  const [page, setPage] = useState(0)
  const [total, setTotal] = useState(0)

  const categories = useDonnees(() => api.categories(), [])
  const propositions = useDonnees(() => api.ia.aClasser(structureId), [structureId, version])
  const liste = useDonnees(
    () => api.mouvements({ structureId, q: rechercheActive, categorieId, aClasser, page: 0, taille: 50 }),
    [structureId, rechercheActive, categorieId, aClasser, version],
  )

  useEffect(() => {
    const t = setTimeout(() => setRechercheActive(recherche), 300)
    return () => clearTimeout(t)
  }, [recherche])

  useEffect(() => {
    if (liste.donnees) {
      setElements(liste.donnees.elements)
      setTotal(liste.donnees.total)
      setPage(0)
    }
  }, [liste.donnees])

  async function suite() {
    const r = await api.mouvements({ structureId, q: rechercheActive, categorieId, aClasser, page: page + 1, taille: 50 })
    setElements((e) => [...e, ...r.elements])
    setPage(page + 1)
  }

  const parId = useMemo(() => Object.fromEntries((propositions.donnees || []).map((p) => [p.transaction_id, p])), [propositions.donnees])
  const sures = (propositions.donnees || []).filter((p) => p.confiance >= 0.6)

  async function toutValider() {
    const r = await api.validerPropositions(sures.map((p) => ({ transactionId: p.transaction_id, categorieId: p.categorie_id, confiance: p.confiance })))
    annoncer(`${pluriel(r.valides, 'mouvement classé', 'mouvements classés')}`)
    rafraichir()
  }

  const remplacer = (nouveau, message) => {
    setElements((es) => (aClasser && nouveau.categorieId ? es.filter((e) => e.id !== nouveau.id) : es.map((e) => (e.id === nouveau.id ? { ...e, ...nouveau } : e))))
    annoncer(message)
    rafraichir()
  }

  const marge = (
    <div className="notes-marge">
      {propositions.donnees?.length ? (
        <div className="note" data-gravite="ATTENTION">
          <p className="note-titre">{pluriel(propositions.donnees.length, 'mouvement attend', 'mouvements attendent')} une catégorie.</p>
          <p className="note-texte">
            J'ai une proposition pour chacun.
            {sures.length > 0 && <> Je suis sûre de moi pour {sures.length}.</>}
          </p>
          {sures.length > 0 && (
            <button className="bouton-lien ia" onClick={toutValider} style={{ marginTop: '0.4rem' }}>
              Accepter les {sures.length} propositions sûres
            </button>
          )}
        </div>
      ) : (
        propositions.donnees && <Griffonnage>Tout est classé. Rien à faire ici.</Griffonnage>
      )}
      <Griffonnage>
        Les SMS de ta banque, tes messages WhatsApp et tes notes vocales arrivent ici, déjà rangés.
      </Griffonnage>
    </div>
  )

  return (
    <Feuille etiquette="Mouvements" marge={marge}>
      <h1>Mouvements</h1>
      <p className="chapeau">Toutes les entrées et sorties de tes comptes, ligne par ligne.</p>

      <Saisie
        structures={structures}
        onEnregistre={(m) => {
          annoncer(`Mouvement enregistré${m.categorie ? ` dans « ${m.categorie} »` : ''}`)
          rafraichir()
        }}
      />

      <section className="section" aria-labelledby="titre-livre">
        <h2 id="titre-livre" className="visuellement-cache">Grand livre</h2>
        <div className="filtres">
          <div>
            <label className="etiquette" htmlFor="recherche">Chercher</label>
            <input id="recherche" className="champ-cadre" value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="aws, Atlas, loyer…" />
          </div>
          <div>
            <label className="etiquette" htmlFor="filtre-cat">Catégorie</label>
            <select id="filtre-cat" className="champ-cadre" value={categorieId} onChange={(e) => setCategorieId(e.target.value)}>
              <option value="">Toutes</option>
              {(categories.donnees || []).map((c) => (
                <option key={c.id} value={c.id}>{c.libelle}</option>
              ))}
            </select>
          </div>
          <div className="onglets-etat" role="group" aria-label="Afficher">
            <button aria-pressed={!aClasser} onClick={() => setParams({})}>Tout</button>
            <button aria-pressed={aClasser} onClick={() => setParams({ a_classer: '1' })}>À classer</button>
          </div>
        </div>

        {liste.charge && !elements.length && <Attente texte="J'ouvre le grand livre" />}
        <Erreur erreur={liste.erreur} recharger={liste.recharger} />
        {!liste.charge && !elements.length && !liste.erreur && (
          <p className="vide">{aClasser ? 'Aucun mouvement à classer.' : 'Aucun mouvement ne correspond à cette recherche.'}</p>
        )}
        <div className="grand-livre">
          {elements.map((m) => (
            <Ligne key={m.id} m={m} proposition={parId[m.id]} categories={categories.donnees || []} onModifie={remplacer} />
          ))}
        </div>
        {elements.length < total && (
          <p style={{ marginTop: '1.25rem' }}>
            <button className="bouton bouton-clair" onClick={suite}>
              Afficher 50 lignes de plus ({total - elements.length} restantes)
            </button>
          </p>
        )}
      </section>
    </Feuille>
  )
}
