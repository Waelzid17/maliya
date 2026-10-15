import { useState } from 'react'
import { Link } from 'react-router-dom'

/** Une note manuscrite de Maliya dans la marge. */
export function Note({ note }) {
  const [ouverte, setOuverte] = useState(false)
  // La marge est étroite : on n'écrit que la première phrase, le reste à la demande.
  const phrases = (note.texte || '').match(/[^.!?]+[.!?]+(\s|$)/g) || [note.texte || '']
  const court = phrases[0].trim()
  const long = phrases.length > 1
  return (
    <div className="note" data-gravite={note.gravite}>
      <p className="note-titre">{note.titre}</p>
      {note.texte && (
        <p className="note-texte">
          {ouverte || !long ? note.texte : court}{' '}
          {long && (
            <button className="note-suite" onClick={() => setOuverte(!ouverte)} aria-expanded={ouverte}>
              {ouverte ? 'moins' : 'la suite'}
            </button>
          )}
        </p>
      )}
      {note.action && (
        <Link className="note-action" to={note.action.route}>
          {note.action.label}
        </Link>
      )}
    </div>
  )
}

/** Petite note libre (texte simple) écrite à la main. */
export function Griffonnage({ children }) {
  return <p className="ecrit-main" style={{ margin: 0 }}>{children}</p>
}
