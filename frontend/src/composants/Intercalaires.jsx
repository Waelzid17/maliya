import { useNavigate } from 'react-router-dom'
import { useMaliya } from '../contexte'
import { dh } from '../format'

const NOMS_TYPES = { AGENCE: 'Agence', SOCIETE: 'Société', PROJET: 'Projet', PERSO: 'Perso' }

/** Les intercalaires du classeur : une structure par onglet, plus « Tout » pour la vue consolidée. */
export default function Intercalaires() {
  const { structures, structureId, setStructureId } = useMaliya()
  const navigate = useNavigate()
  const total = structures.reduce((s, x) => s + Number(x.solde), 0)
  // Un seul intercalaire d'un type : on l'appelle par son type. Plusieurs : par leur nom.
  const parType = structures.reduce((n, s) => ({ ...n, [s.type]: (n[s.type] || 0) + 1 }), {})
  const etiquette = (s) => (parType[s.type] > 1 ? s.nom : NOMS_TYPES[s.type] || s.nom)
  return (
    <nav className="intercalaires" aria-label="Choisir une structure">
      <button className="onglet" style={{ '--c': '#1E2A5A' }} aria-pressed={structureId === null} onClick={() => setStructureId(null)}>
        Tout
        <small>{structures.length ? dh(total) : '…'}</small>
      </button>
      {structures.map((s) => (
        <button
          key={s.id}
          className="onglet"
          style={{ '--c': s.couleur }}
          aria-pressed={structureId === s.id}
          onClick={() => setStructureId(s.id)}
          title={s.nom}
        >
          {etiquette(s)}
          <small>{dh(s.solde)}</small>
        </button>
      ))}
      <button className="onglet onglet-ajout" style={{ '--c': '#9AA0B5' }} onClick={() => navigate('/structures/nouvelle')}>
        + Ajouter
      </button>
    </nav>
  )
}
