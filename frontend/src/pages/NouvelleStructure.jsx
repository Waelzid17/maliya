import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'

const TYPES = [
  { v: 'AGENCE', l: 'Une agence' },
  { v: 'SOCIETE', l: 'Une société' },
  { v: 'PROJET', l: 'Un projet avec son propre compte' },
  { v: 'PERSO', l: 'Mes finances perso' },
]

export default function NouvelleStructure() {
  const { rafraichir, setStructureId, annoncer } = useMaliya()
  const navigate = useNavigate()
  const [f, setF] = useState({ nom: '', type: 'AGENCE', banque: '', soldeInitial: '', ice: '' })
  const [erreur, setErreur] = useState(null)
  const [occupe, setOccupe] = useState(false)
  const maj = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function envoyer(e) {
    e.preventDefault()
    setOccupe(true)
    setErreur(null)
    try {
      const s = await api.creerStructure({ ...f, soldeInitial: f.soldeInitial ? Number(f.soldeInitial) : 0, ice: f.ice || null })
      rafraichir()
      setStructureId(s.id)
      annoncer(`Intercalaire « ${s.nom} » ajouté`)
      navigate('/mouvements')
    } catch (err) {
      setErreur(err)
    } finally {
      setOccupe(false)
    }
  }

  return (
    <Feuille
      etiquette="Ajouter une structure"
      marge={
        <div className="notes-marge">
          <Griffonnage>Un intercalaire par activité : je sépare les comptes, puis je les additionne pour la vue « Tout ».</Griffonnage>
          <Griffonnage>Les virements entre tes structures sont reconnus et ne comptent pas deux fois.</Griffonnage>
        </div>
      }
    >
      <h1>Ajouter un intercalaire</h1>
      <p className="chapeau">Une nouvelle activité à suivre, avec son compte bancaire.</p>
      <form className="formulaire" onSubmit={envoyer}>
        <div>
          <label className="etiquette" htmlFor="s-nom">Nom</label>
          <input id="s-nom" className="champ-cadre" style={{ width: '100%' }} value={f.nom} onChange={maj('nom')} placeholder="Zidane Digital" required />
        </div>
        <div>
          <label className="etiquette" htmlFor="s-type">C'est…</label>
          <select id="s-type" className="champ-cadre" style={{ width: '100%' }} value={f.type} onChange={maj('type')}>
            {TYPES.map((t) => (
              <option key={t.v} value={t.v}>{t.l}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="etiquette" htmlFor="s-banque">Banque</label>
          <input id="s-banque" className="champ-cadre" style={{ width: '100%' }} value={f.banque} onChange={maj('banque')} placeholder="Attijariwafa Bank" />
        </div>
        <div>
          <label className="etiquette" htmlFor="s-solde">Solde actuel du compte (dh)</label>
          <input id="s-solde" className="champ-cadre" style={{ width: '100%' }} inputMode="decimal" value={f.soldeInitial} onChange={maj('soldeInitial')} placeholder="0" />
        </div>
        {f.type !== 'PERSO' && (
          <div>
            <label className="etiquette" htmlFor="s-ice">ICE (facultatif)</label>
            <input id="s-ice" className="champ-cadre" style={{ width: '100%' }} value={f.ice} onChange={maj('ice')} />
          </div>
        )}
        <Erreur erreur={erreur} />
        <div>
          <button className="bouton" type="submit" disabled={occupe || !f.nom.trim()}>Ajouter l'intercalaire</button>
        </div>
      </form>
    </Feuille>
  )
}
