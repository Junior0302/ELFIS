import { cx } from './cx'

export type ProgressProps = {
  value: number
  label?: string
  className?: string
}

/** Presentational progress bar — no domain math beyond clamp. */
export function Progress({ value, label, className }: ProgressProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value)))
  return (
    <div
      className={cx('ui-progress', 'ds-progress', className)}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label || 'Progression'}
    >
      {label ? <p className="ui-progress-label">{label}</p> : null}
      <div className="ui-progress-track">
        <div className="ui-progress-fill ds-progress__fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="muted ui-progress-pct">{pct} %</span>
    </div>
  )
}
