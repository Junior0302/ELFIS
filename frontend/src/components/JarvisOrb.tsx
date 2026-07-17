import type { VoicePhase } from '../hooks/useVoiceAssistant'

const STATUS: Record<VoicePhase, string> = {
  idle: 'En veille — appuyez pour parler',
  listening: 'Je vous écoute…',
  processing: 'Analyse en cours…',
  speaking: 'Je réponds…',
  unsupported: 'Vocal indisponible sur ce navigateur',
}

export default function JarvisOrb({
  phase,
  interim,
  onToggle,
  disabled,
}: {
  phase: VoicePhase
  interim?: string
  onToggle: () => void
  disabled?: boolean
}) {
  const active = phase === 'listening' || phase === 'processing' || phase === 'speaking'
  return (
    <div className={`jarvis-dock ${phase}`}>
      <button
        type="button"
        className={`jarvis-orb ${phase}`}
        onClick={onToggle}
        disabled={disabled || phase === 'unsupported' || phase === 'processing'}
        aria-pressed={phase === 'listening'}
        aria-label={
          phase === 'listening' ? 'Arrêter l’écoute' : 'Activer l’assistant vocal'
        }
      >
        <span className="jarvis-orb-ring ring-a" aria-hidden />
        <span className="jarvis-orb-ring ring-b" aria-hidden />
        <span className="jarvis-orb-ring ring-c" aria-hidden />
        <span className="jarvis-orb-core" aria-hidden>
          <span className="jarvis-orb-core-glow" />
          {phase === 'listening' ? '●' : phase === 'speaking' ? '♪' : 'AI'}
        </span>
      </button>
      <div className="jarvis-status" role="status" aria-live="polite">
        <strong className={active ? 'is-live' : undefined}>{STATUS[phase]}</strong>
        {interim ? <span className="jarvis-interim">« {interim} »</span> : null}
      </div>
    </div>
  )
}
