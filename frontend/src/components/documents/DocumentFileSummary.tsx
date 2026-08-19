type Props = {
  name: string
  sizeBytes: number
  mime?: string | null
}

function formatSize(n: number): string {
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

export default function DocumentFileSummary({ name, sizeBytes, mime }: Props) {
  return (
    <div className="doc-file-summary">
      <strong>{name}</strong>
      <span className="muted">
        {formatSize(sizeBytes)}
        {mime ? ` · ${mime}` : ''}
      </span>
    </div>
  )
}
