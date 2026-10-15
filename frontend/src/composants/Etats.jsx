export function Attente({ texte = 'Je fais les comptes' }) {
  return <p className="attente" role="status">{texte}</p>
}

export function Erreur({ erreur, recharger }) {
  if (!erreur) return null
  return (
    <div className="erreur" role="alert">
      <p style={{ margin: 0 }}>{erreur.message}</p>
      {recharger && (
        <button className="bouton-lien" onClick={recharger} style={{ marginTop: '0.4rem' }}>
          Réessayer
        </button>
      )}
    </div>
  )
}
