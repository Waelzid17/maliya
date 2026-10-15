import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { dh } from '../format'

const SUGGESTIONS = [
  'Combien j’ai en banque ?',
  'Pourquoi ma tréso a baissé ce mois-ci ?',
  'Qui me doit de l’argent ?',
  'Combien j’ai dépensé en cloud en septembre ?',
  'Quel projet perd de l’argent ?',
  'Combien je peux me verser ?',
  'chhal khlest had chher ?',
  'Y a-t-il des doublons ?',
]

function Reponse({ r }) {
  const max = r.graphique ? Math.max(...r.graphique.donnees.map((d) => Math.abs(d.valeur))) : 1
  return (
    <div className="reponse">
      {r.reponse_llm ? <p style={{ whiteSpace: 'pre-wrap' }}>{r.reponse_llm}</p> : <p>{r.reponse}</p>}
      {!r.reponse_llm && r.points?.length > 0 && (
        <ul>
          {r.points.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
      {r.graphique?.type === 'barres' && (
        <div className="minigraph" role="img" aria-label="Répartition">
          {r.graphique.donnees.map((d) => (
            <div className="poste" key={d.label} style={{ gridTemplateColumns: '9rem 1fr 6rem' }}>
              <span className="poste-nom">{d.label}</span>
              <div className="poste-barre" style={{ width: `${(Math.abs(d.valeur) / max) * 100}%` }} />
              <span className="poste-montant">{dh(d.valeur)}</span>
            </div>
          ))}
        </div>
      )}
      {r.actions?.length > 0 && (
        <p style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
          {r.actions.map((a) => (
            <Link key={a.route} className="note-action" to={a.route} style={{ marginTop: 0 }}>{a.label}</Link>
          ))}
        </p>
      )}
      <div className="signature">— M.</div>
    </div>
  )
}

export default function Demander() {
  const { structureId, structure } = useMaliya()
  const [params, setParams] = useSearchParams()
  const [question, setQuestion] = useState('')
  const [fil, setFil] = useState([])
  const [occupe, setOccupe] = useState(false)
  const [erreur, setErreur] = useState(null)
  const champ = useRef(null)
  const dejaPosee = useRef(null)

  async function poser(q) {
    const texte = q.trim()
    if (!texte || occupe) return
    setOccupe(true)
    setErreur(null)
    setQuestion('')
    setFil((f) => [...f, { question: texte, reponse: null }])
    try {
      const r = await api.ia.copilote(texte, structureId)
      setFil((f) => f.map((x, i) => (i === f.length - 1 ? { ...x, reponse: r } : x)))
    } catch (e) {
      setErreur(e)
      setFil((f) => f.slice(0, -1))
    } finally {
      setOccupe(false)
      champ.current?.focus()
    }
  }

  useEffect(() => {
    const q = params.get('q')
    if (q && dejaPosee.current !== q) {
      dejaPosee.current = q
      setParams({}, { replace: true })
      poser(q)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  const marge = (
    <div className="notes-marge">
      <Griffonnage>
        Pose ta question comme elle vient, en français, en darija ou en anglais.
      </Griffonnage>
      <Griffonnage>
        {structure ? `Je réponds pour ${structure.nom}. Change d'intercalaire pour un autre périmètre.` : 'Je réponds pour toutes tes structures. Choisis un intercalaire pour zoomer.'}
      </Griffonnage>
      <Griffonnage>Chaque chiffre vient de ton grand livre. Je ne devine jamais un montant.</Griffonnage>
    </div>
  )

  return (
    <Feuille etiquette="Demander à Maliya" marge={marge}>
      <h1>Demander à Maliya</h1>
      <p className="chapeau">Une question sur tes comptes, tes clients ou tes projets ? Écris-la.</p>

      <section className="section">
        <div className="fil" aria-live="polite">
          {fil.map((x, i) => (
            <div key={i}>
              <p className="question">{x.question}</p>
              {x.reponse ? <Reponse r={x.reponse} /> : <p className="attente">Je cherche dans tes comptes</p>}
            </div>
          ))}
        </div>
        <Erreur erreur={erreur} />
        <form
          className="ligne-ecriture"
          onSubmit={(e) => {
            e.preventDefault()
            poser(question)
          }}
        >
          <label htmlFor="question" className="visuellement-cache">Ta question</label>
          <input ref={champ} id="question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Écris ta question…" autoComplete="off" autoFocus />
          <button className="bouton" type="submit" disabled={occupe || !question.trim()}>Demander</button>
        </form>
        {fil.length === 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            <p className="discret petit" style={{ margin: '0 0 0.6rem' }}>Pour commencer :</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => poser(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
      </section>
    </Feuille>
  )
}
