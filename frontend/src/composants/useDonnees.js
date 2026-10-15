import { useCallback, useEffect, useState } from 'react'

/** Charge des données et suit l'état (chargement, erreur). Se recharge quand les dépendances changent. */
export function useDonnees(charger, deps) {
  const [etat, setEtat] = useState({ donnees: null, erreur: null, charge: true })
  const [tour, setTour] = useState(0)

  useEffect(() => {
    let actif = true
    setEtat((e) => ({ ...e, charge: true, erreur: null }))
    charger()
      .then((donnees) => actif && setEtat({ donnees, erreur: null, charge: false }))
      .catch((erreur) => actif && setEtat({ donnees: null, erreur, charge: false }))
    return () => {
      actif = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tour])

  const recharger = useCallback(() => setTour((t) => t + 1), [])
  return { ...etat, recharger }
}
