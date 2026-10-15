/** Une page du classeur : la marge (où l'IA écrit) et le contenu, séparés par le trait rouge. */
export default function Feuille({ marge, children, etiquette }) {
  return (
    <main className="feuille" aria-label={etiquette}>
      <aside className="marge" aria-label="Notes de Maliya">
        {marge}
      </aside>
      <div className="trait-marge" aria-hidden="true" />
      <div className="contenu">{children}</div>
    </main>
  )
}
