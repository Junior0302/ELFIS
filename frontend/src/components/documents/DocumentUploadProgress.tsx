type Props = {
  percent: number
}

export default function DocumentUploadProgress({ percent }: Props) {
  const pct = Math.max(0, Math.min(100, percent))
  return (
    <div className="doc-upload-progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
      <div className="doc-upload-progress__bar" style={{ width: `${pct}%` }} />
      <span className="doc-upload-progress__label">{pct}%</span>
    </div>
  )
}
