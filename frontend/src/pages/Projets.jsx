import { api } from '../api'
import { useMaliya } from '../contexte'
import Feuille from '../composants/Feuille'
import { Attente, Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateLongue, dh } from '../format'

const STATUTS = { EN_COURS: 'En cours', TERMINE: 'Terminé', PAUSE: 'En pause' }

function Projet({ p }) {
  const conso = Number(p.consommation || 0)
  const classe = conso > 100 ? 'deborde' : conso >= 85 ? 'chaud' : ''
  return (
    <article className="projet">
      <div className="projet-entete">
        <h3>
          <span className="pastille" style={{ background: p.couleur }} />
          {p.nom}
        </h3>
        <span className="discret petit">
          {STATUTS[p.statut]} · {p.interne ? 'projet interne' : p.client}
        </span>
      </div>
      <div className="jauge" role="img" aria-label={`Budget consommé à ${conso} %`}>
        <div className={`jauge-remplie ${classe}`} style={{ width: `${Math.min(conso, 100)}%` }} />
      </div>
      <div className="chiffres-projet">
        <span>
          <b>{dh(p.coutReel)}</b> dépensés sur {dh(p.budget)} ({String(conso).replace('.', ',')} %)
        </span>
        {!p.interne && (
          <span>
            Facturé <b>{dh(p.factureHt)}</b> HT
          </span>
        )}
        {!p.interne && p.margePct !== null && (
          <span>
            Marge <b className={Number(p.marge) < 0 ? 'negatif' : ''}>{dh(p.marge)}</b> ({String(p.margePct).replace('.', ',')} %)
          </span>
        )}
      </div>
      {p.statut === 'EN_COURS' && conso > 100 && (
        <p className="ecrit-main" style={{ margin: '0.5rem 0 0' }}>
          Budget dépassé de {dh(Number(p.coutReel) - Number(p.budget))}. Il reste du travail à facturer ? C'est le moment de parler hors-périmètre.
        </p>
      )}
      {p.statut === 'EN_COURS' && conso >= 85 && conso <= 100 && p.budgetEpuiseVers && (
        <p className="ecrit-main" style={{ margin: '0.5rem 0 0' }}>
          Au rythme de {dh(p.rythmeMensuel)} par mois, le budget sera épuisé vers le {dateLongue(p.budgetEpuiseVers)}.
        </p>
      )}
    </article>
  )
}

export default function Projets() {
  const { structureId, version } = useMaliya()
  const projets = useDonnees(() => api.projets(structureId), [structureId, version])
  const liste = projets.donnees || []
  const actifs = liste.filter((p) => p.statut === 'EN_COURS')
  const tendus = actifs.filter((p) => Number(p.consommation) >= 85)
  const fragiles = actifs.filter((p) => !p.interne && p.margePct !== null && Number(p.margePct) < 25)

  const marge = (
    <div className="notes-marge">
      {tendus.map((p) => (
        <div className="note" data-gravite="ATTENTION" key={p.id}>
          <p className="note-titre">{p.nom}</p>
          <p className="note-texte">{String(p.consommation).replace('.', ',')} % du budget déjà dépensé.</p>
        </div>
      ))}
      {fragiles.map((p) => (
        <Griffonnage key={`f${p.id}`}>
          {p.nom} ne laisse que {String(p.margePct).replace('.', ',')} % de marge. À surveiller.
        </Griffonnage>
      ))}
      {liste.length > 0 && !tendus.length && !fragiles.length && <Griffonnage>Tous les projets tiennent leur budget.</Griffonnage>}
      <Griffonnage>
        Les coûts viennent des mouvements rattachés à chaque projet : freelances, cloud, outils.
      </Griffonnage>
    </div>
  )

  return (
    <Feuille etiquette="Projets" marge={marge}>
      <h1>Projets</h1>
      <p className="chapeau">Pour chaque projet : ce qu'il coûte vraiment, ce qu'il rapporte, et combien de budget il reste.</p>
      {projets.charge && !projets.donnees && <Attente />}
      <Erreur erreur={projets.erreur} recharger={projets.recharger} />
      {projets.donnees?.length === 0 && <p className="vide">Aucun projet pour cette structure.</p>}
      <div className="section">
        {liste.map((p) => (
          <Projet key={p.id} p={p} />
        ))}
      </div>
    </Feuille>
  )
}
