const NODES = [
  { id: 'sales', label: 'Sales', mod: 'sales' },
  { id: 'compta', label: 'Compta', mod: 'compta' },
  { id: 'doc', label: 'Docs', mod: 'doc' },
  { id: 'hr', label: 'RH', mod: 'hr' },
] as const

/** Illustration légère — Mark central + Pilot reliés (CSS only). */
export function LoginIllustration() {
  return (
    <div className="elfis-login__illu" role="img" aria-label="Applications Pilot connectées à ELFIS Core">
      <span className="elfis-login__illu-ring" aria-hidden="true" />
      <span className="elfis-login__illu-flow elfis-login__illu-flow--a" aria-hidden="true" />
      <span className="elfis-login__illu-flow elfis-login__illu-flow--b" aria-hidden="true" />
      <div className="elfis-login__illu-core">
        <img src="/favicon.svg" alt="" width={48} height={48} decoding="async" />
        <span>ELFIS</span>
      </div>
      {NODES.map((node) => (
        <span key={node.id} className={`elfis-login__illu-node elfis-login__illu-node--${node.mod}`}>
          {node.label}
        </span>
      ))}
    </div>
  )
}
