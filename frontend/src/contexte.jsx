import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api'

const Contexte = createContext(null)

/** La structure choisie (intercalaire) et la liste des structures, partagées par toutes les pages. */
export function FournisseurMaliya({ children }) {
  const [structures, setStructures] = useState([])
  const [structureId, setStructureIdBrut] = useState(() => {
    try {
      const v = localStorage.getItem('maliya.structure')
      return v ? Number(v) : null
    } catch {
      return null
    }
  })
  const [version, setVersion] = useState(0)
  const [toast, setToast] = useState(null)

  const setStructureId = useCallback((id) => {
    setStructureIdBrut(id)
    try {
      if (id) localStorage.setItem('maliya.structure', String(id))
      else localStorage.removeItem('maliya.structure')
    } catch {
      /* stockage indisponible : ce n'est qu'un confort */
    }
  }, [])

  const rafraichir = useCallback(() => setVersion((v) => v + 1), [])

  const annoncer = useCallback((message) => {
    setToast(message)
    window.clearTimeout(window.__maliyaToast)
    window.__maliyaToast = window.setTimeout(() => setToast(null), 3200)
  }, [])

  useEffect(() => {
    api.structures().then(setStructures).catch(() => setStructures([]))
  }, [version])

  const structure = structures.find((s) => s.id === structureId) || null

  return (
    <Contexte.Provider value={{ structures, structureId, structure, setStructureId, version, rafraichir, annoncer }}>
      {children}
      {toast && <div className="toast" role="status">{toast}</div>}
    </Contexte.Provider>
  )
}

export const useMaliya = () => useContext(Contexte)
