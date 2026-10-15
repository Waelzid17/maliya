import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { useMaliya } from '../contexte'
import Courbe from '../composants/Courbe'
import Feuille from '../composants/Feuille'
import { Erreur } from '../composants/Etats'
import { Griffonnage } from '../composants/Notes'
import { useDonnees } from '../composants/useDonnees'
import { dateLongue, dh, moisCourt, moisLong } from '../format'

const DEPART = {
  embauche: { actif: true, salaire_net: 12000, dans_mois: 2 },
  perte_client: { actif: false, client_id: '' },
  nouveau_contrat: { actif: false, montant_mensuel: 15000, dans_mois: 1 },
  retard_paiement: { actif: false, jours: 45, dans_mois: 1 },
  depense: { actif: false, montant: 30000, dans_mois: 2 },
  remuneration: { actif: false, variation_mensuelle: 5000, dans_mois: 1 },
}

const DANS = [1, 2, 3, 4, 6, 9]

function Dans({ valeur, onChange, id }) {
  return (
    <label htmlFor={id}>
      à partir de{' '}
      <select id={id} value={valeur} onChange={(e) => onChange(Number(e.target.value))}>
        {DANS.map((d) => (
          <option key={d} value={d}>{d === 1 ? 'le mois prochain' : `dans ${d} mois`}</option>
        ))}
      </select>
    </label>
  )
}

function Curseur({ id, valeur, min, max, pas, onChange, rendu }) {
  return (
    <label htmlFor={id} style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
      <input id={id} type="range" min={min} max={max} step={pas} value={valeur} onChange={(e) => onChange(Number(e.target.value))} />
      <b style={{ minWidth: '7rem' }}>{rendu(valeur)}</b>
    </label>
  )
}

export default function Scenarios() {
  const { structureId, version } = useMaliya()
  const [h, setH] = useState(DEPART)
  const [resultat, setResultat] = useState(null)
  const [erreur, setErreur] = useState(null)
  const clients = useDonnees(() => api.clients(), [])
  const prevision = useDonnees(() => api.ia.prevision(structureId), [structureId, version])

  const maj = (cle, champ, valeur) => setH((x) => ({ ...x, [cle]: { ...x[cle], [champ]: valeur } }))

  const scenarios = useMemo(
    () =>
      Object.entries(h)
        .filter(([cle, v]) => v.actif && !(cle === 'perte_client' && !v.client_id))
        .map(([type, v]) => {
          const { actif, ...reste } = v
          return { type, ...reste, client_id: reste.client_id ? Number(reste.client_id) : undefined }
        }),
    [h],
  )

  useEffect(() => {
    const t = setTimeout(() => {
      api.ia
        .simulation(structureId, scenarios)
        .then((r) => {
          setResultat(r)
          setErreur(null)
        })
        .catch(setErreur)
    }, 250)
    return () => clearTimeout(t)
  }, [scenarios, structureId, version])

  const series = resultat
    ? [
        { points: resultat.mois.map((m, i) => ({ x: i, y: resultat.base[i], mois: m, quoi: 'Sans tes hypothèses' })), classe: 'trace' },
        { points: resultat.mois.map((m, i) => ({ x: i, y: resultat.scenario[i], mois: m, quoi: 'Avec tes hypothèses' })), classe: 'trace-scenario' },
      ]
    : []

  const p = prevision.donnees
  const fin = p?.prevision.at(-1)

  const marge = (
    <div className="notes-marge">
      {p && (
        <div className="note" data-gravite={p.proba_solde_negatif > 0.05 ? 'ATTENTION' : 'INFO'}>
          <p className="note-titre">Sans rien changer : {dh(fin.p50)} vers le {dateLongue(fin.semaine).replace(/ \d{4}$/, '')}.</p>
          <p className="note-texte">
            Fourchette de {dh(fin.p10)} à {dh(fin.p90)}. Calculé par un réseau {p.moteur.startsWith('LSTM') ? 'LSTM' : 'de neurones'} entraîné sur tes flux de chaque semaine.
          </p>
        </div>
      )}
      <Griffonnage>
        Coche une hypothèse et bouge les curseurs, je recalcule tout de suite. Les charges sociales sont approximées : demande confirmation à ton comptable.
      </Griffonnage>
    </div>
  )

  return (
    <Feuille etiquette="Prévisions et scénarios" marge={marge}>
      <h1>Et si…</h1>
      <p className="chapeau">Teste une décision avant de la prendre. La courbe noire est ta trajectoire actuelle, la rouge celle avec tes hypothèses.</p>

      <section className="section">
        <div className="hypotheses">
          <div className="hypothese">
            <input type="checkbox" id="h-emb" checked={h.embauche.actif} onChange={(e) => maj('embauche', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-emb"><b>J'embauche quelqu'un</b></label>
              {h.embauche.actif && (
                <div className="hypothese-reglages">
                  <Curseur id="h-emb-s" valeur={h.embauche.salaire_net} min={5000} max={35000} pas={500} onChange={(v) => maj('embauche', 'salaire_net', v)} rendu={(v) => `${dh(v)} net`} />
                  <Dans id="h-emb-d" valeur={h.embauche.dans_mois} onChange={(v) => maj('embauche', 'dans_mois', v)} />
                </div>
              )}
            </div>
          </div>

          <div className="hypothese">
            <input type="checkbox" id="h-perte" checked={h.perte_client.actif} onChange={(e) => maj('perte_client', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-perte"><b>Je perds un client</b></label>
              {h.perte_client.actif && (
                <div className="hypothese-reglages">
                  <select aria-label="Client perdu" value={h.perte_client.client_id} onChange={(e) => maj('perte_client', 'client_id', e.target.value)}>
                    <option value="">Lequel ?</option>
                    {(clients.donnees || []).map((c) => (
                      <option key={c.id} value={c.id}>{c.nom}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          <div className="hypothese">
            <input type="checkbox" id="h-contrat" checked={h.nouveau_contrat.actif} onChange={(e) => maj('nouveau_contrat', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-contrat"><b>Je signe un nouveau contrat mensuel</b></label>
              {h.nouveau_contrat.actif && (
                <div className="hypothese-reglages">
                  <Curseur id="h-contrat-m" valeur={h.nouveau_contrat.montant_mensuel} min={2000} max={60000} pas={1000} onChange={(v) => maj('nouveau_contrat', 'montant_mensuel', v)} rendu={(v) => `${dh(v)} HT`} />
                  <Dans id="h-contrat-d" valeur={h.nouveau_contrat.dans_mois} onChange={(v) => maj('nouveau_contrat', 'dans_mois', v)} />
                </div>
              )}
            </div>
          </div>

          <div className="hypothese">
            <input type="checkbox" id="h-retard" checked={h.retard_paiement.actif} onChange={(e) => maj('retard_paiement', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-retard"><b>Mes clients paient en retard</b></label>
              {h.retard_paiement.actif && (
                <div className="hypothese-reglages">
                  <Curseur id="h-retard-j" valeur={h.retard_paiement.jours} min={15} max={90} pas={5} onChange={(v) => maj('retard_paiement', 'jours', v)} rendu={(v) => `${v} jours`} />
                </div>
              )}
            </div>
          </div>

          <div className="hypothese">
            <input type="checkbox" id="h-dep" checked={h.depense.actif} onChange={(e) => maj('depense', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-dep"><b>Je fais une grosse dépense</b></label>
              {h.depense.actif && (
                <div className="hypothese-reglages">
                  <Curseur id="h-dep-m" valeur={h.depense.montant} min={5000} max={200000} pas={5000} onChange={(v) => maj('depense', 'montant', v)} rendu={(v) => dh(v)} />
                  <Dans id="h-dep-d" valeur={h.depense.dans_mois} onChange={(v) => maj('depense', 'dans_mois', v)} />
                </div>
              )}
            </div>
          </div>

          <div className="hypothese">
            <input type="checkbox" id="h-remu" checked={h.remuneration.actif} onChange={(e) => maj('remuneration', 'actif', e.target.checked)} />
            <div>
              <label htmlFor="h-remu"><b>Je change ma rémunération</b></label>
              {h.remuneration.actif && (
                <div className="hypothese-reglages">
                  <Curseur id="h-remu-v" valeur={h.remuneration.variation_mensuelle} min={-10000} max={25000} pas={1000} onChange={(v) => maj('remuneration', 'variation_mensuelle', v)} rendu={(v) => `${dh(v, { signe: true })} / mois`} />
                  <Dans id="h-remu-d" valeur={h.remuneration.dans_mois} onChange={(v) => maj('remuneration', 'dans_mois', v)} />
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="section" aria-live="polite">
        <Erreur erreur={erreur} />
        {resultat && (
          <>
            <p className="verdict">{resultat.verdict}</p>
            {resultat.notes.length > 0 && (
              <ul className="discret petit" style={{ paddingLeft: '1.1rem', marginTop: '0.6rem' }}>
                {resultat.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            )}
            <div style={{ marginTop: '1.25rem' }}>
              <Courbe
                titre="Projection sur douze mois"
                series={series}
                reperes={resultat.mois.map((m, i) => ({ x: i, libelle: moisCourt(m) })).filter((_, i) => i % 2 === 0)}
                survol={(pt) => `${pt.quoi}, ${moisLong(pt.mois)} : ${dh(pt.y)}`}
              />
              <div className="legende">
                <span><i />Trajectoire actuelle</span>
                <span><i className="rouge" />Avec tes hypothèses</span>
                <span>
                  Base : prévision du LSTM sur {resultat.mois_prevus_par_lstm} mois, puis ta moyenne des 12 derniers mois ({dh(resultat.flux_mensuel_base, { signe: true })} par mois)
                </span>
              </div>
            </div>
          </>
        )}
      </section>
    </Feuille>
  )
}
