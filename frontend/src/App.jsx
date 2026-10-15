import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import Intercalaires from './composants/Intercalaires'
import { useMaliya } from './contexte'
import { api } from './api'
import { dateLongue } from './format'
import Aujourdhui from './pages/Aujourdhui'
import Mouvements from './pages/Mouvements'
import Factures from './pages/Factures'
import Projets from './pages/Projets'
import Scenarios from './pages/Scenarios'
import Signaux from './pages/Signaux'
import Demander from './pages/Demander'
import NouvelleStructure from './pages/NouvelleStructure'

function Navigation() {
  const { structures, structureId } = useMaliya()
  const [infos, setInfos] = useState(null)
  useEffect(() => {
    api.ia.modeles().then(setInfos).catch(() => setInfos(null))
  }, [])
  const aClasser = structures
    .filter((s) => !structureId || s.id === structureId)
    .reduce((n, s) => n + Number(s.aClasser || 0), 0)

  const lien = (to, texte, extra) => (
    <li>
      <NavLink to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'actif' : undefined)}>
        {texte}
        {extra}
      </NavLink>
    </li>
  )

  return (
    <header className="nav">
      <NavLink to="/" className="marque" aria-label="Maliya, accueil">
        <span className="marque-ar" lang="ar">مالية</span>
        <span className="marque-lat">Maliya — tes comptes, tenus avec toi</span>
      </NavLink>
      <ul className="nav-liens">
        {lien('/', "Aujourd'hui")}
        {lien('/mouvements', 'Mouvements', aClasser > 0 && <span className="nav-compteur">{aClasser}</span>)}
        {lien('/factures', 'Factures')}
        {lien('/projets', 'Projets')}
        {lien('/scenarios', 'Prévisions')}
        {lien('/signaux', 'Signaux')}
        {lien('/demander', 'Demander à Maliya')}
      </ul>
      <div className="nav-pied">
        {infos ? (
          <>
            <p>Comptes à jour au {dateLongue(infos.date_reference)}.</p>
            <p>L'IA tourne sur ta machine{infos.copilote?.llm_local ? `, avec ${infos.copilote.llm_local}` : ''}.</p>
          </>
        ) : (
          <p>Le service IA démarre…</p>
        )}
      </div>
    </header>
  )
}

export default function App() {
  return (
    <div className="cadre">
      <Navigation />
      <Routes>
        <Route path="/" element={<Aujourdhui />} />
        <Route path="/mouvements" element={<Mouvements />} />
        <Route path="/factures" element={<Factures />} />
        <Route path="/projets" element={<Projets />} />
        <Route path="/scenarios" element={<Scenarios />} />
        <Route path="/signaux" element={<Signaux />} />
        <Route path="/demander" element={<Demander />} />
        <Route path="/structures/nouvelle" element={<NouvelleStructure />} />
        <Route path="*" element={<Aujourdhui />} />
      </Routes>
      <Intercalaires />
    </div>
  )
}
