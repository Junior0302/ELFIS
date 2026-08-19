/**
 * Visual vivant du Cockpit Hero — orbite / réseau micro-animé (pas d’image statique).
 */
export function CockpitHeroVisual({ className }: { className?: string }) {
  return (
    <div
      className={`cockpit-hero-visual ${className ?? ''}`.trim()}
      aria-hidden
      data-cockpit-visual="orbit"
    >
      <div className="cockpit-hero-visual__glow" />
      <svg className="cockpit-hero-visual__svg" viewBox="0 0 320 280" fill="none">
        <ellipse
          className="cockpit-hero-visual__ring cockpit-hero-visual__ring--a"
          cx="160"
          cy="140"
          rx="118"
          ry="88"
          stroke="currentColor"
          strokeOpacity="0.28"
        />
        <ellipse
          className="cockpit-hero-visual__ring cockpit-hero-visual__ring--b"
          cx="160"
          cy="140"
          rx="88"
          ry="118"
          stroke="currentColor"
          strokeOpacity="0.18"
        />
        <ellipse
          className="cockpit-hero-visual__ring cockpit-hero-visual__ring--c"
          cx="160"
          cy="140"
          rx="52"
          ry="52"
          stroke="currentColor"
          strokeOpacity="0.34"
        />
        <circle className="cockpit-hero-visual__core" cx="160" cy="140" r="18" fill="currentColor" fillOpacity="0.2" />
        <circle className="cockpit-hero-visual__node cockpit-hero-visual__node--1" cx="278" cy="140" r="4" fill="currentColor" />
        <circle className="cockpit-hero-visual__node cockpit-hero-visual__node--2" cx="160" cy="28" r="3.5" fill="currentColor" />
        <circle className="cockpit-hero-visual__node cockpit-hero-visual__node--3" cx="72" cy="210" r="3.5" fill="currentColor" />
        <path
          className="cockpit-hero-visual__link"
          d="M160 140 L278 140 M160 140 L160 28 M160 140 L72 210"
          stroke="currentColor"
          strokeOpacity="0.2"
          strokeWidth="1"
        />
      </svg>
      <span className="cockpit-hero-visual__mono">E</span>
    </div>
  )
}
