import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Props = { children: ReactNode }
type State = { error: Error | null; chunk: boolean }

function isChunkLoadError(error: Error): boolean {
  const msg = error.message || ''
  return (
    /Failed to fetch dynamically imported module/i.test(msg) ||
    /Loading chunk [\d]+ failed/i.test(msg) ||
    /Importing a module script failed/i.test(msg) ||
    error.name === 'ChunkLoadError'
  )
}

/**
 * Erreur de chunk lazy → Réessayer / Accueil, jamais redirect auto Home.
 */
export default class RouteChunkErrorBoundary extends Component<Props, State> {
  state: State = { error: null, chunk: false }

  static getDerivedStateFromError(error: Error): State {
    return { error, chunk: isChunkLoadError(error) }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('RouteChunkErrorBoundary', error, info.componentStack)
  }

  private retry = () => {
    this.setState({ error: null, chunk: false })
  }

  render() {
    const { error, chunk } = this.state
    if (!error) return this.props.children

    return (
      <div className="page" style={{ padding: '2rem', maxWidth: 480 }} data-testid="route-chunk-error">
        <h1>{chunk ? 'Chargement interrompu' : 'Erreur d’affichage'}</h1>
        <p>
          {chunk
            ? 'Une partie de l’application n’a pas pu être téléchargée. Vérifiez votre connexion puis réessayez.'
            : 'Impossible d’afficher cette page pour le moment.'}
        </p>
        <p style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn" onClick={this.retry}>
            Réessayer
          </button>
          <Link className="btn secondary" to="/home">
            Accueil
          </Link>
        </p>
      </div>
    )
  }
}
