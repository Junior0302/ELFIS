import { forwardRef, type KeyboardEvent } from 'react'
import { cx } from '../design-system/components/cx'

export type CommandInputProps = {
  id: string
  value: string
  onChange: (value: string) => void
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void
  commandMode?: boolean
  className?: string
}

export const CommandInput = forwardRef<HTMLInputElement, CommandInputProps>(function CommandInput(
  { id, value, onChange, onKeyDown, commandMode, className },
  ref,
) {
  return (
    <div className={cx('cc-input-wrap', commandMode && 'cc-input-wrap--command', className)}>
      <label className="sr-only" htmlFor={id}>
        Recherche ou commande ELFIS
      </label>
      {commandMode ? (
        <span className="cc-input__mode" aria-hidden>
          &gt;
        </span>
      ) : (
        <span className="cc-input__icon" aria-hidden>
          ⌕
        </span>
      )}
      <input
        ref={ref}
        id={id}
        className="cc-input"
        type="search"
        role="combobox"
        aria-expanded
        aria-controls="cc-results-listbox"
        aria-autocomplete="list"
        placeholder={
          commandMode
            ? 'Commande… (ex. nouvelle facture)'
            : 'Que souhaitez-vous faire aujourd’hui ?'
        }
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
      />
      {commandMode ? (
        <span className="cc-input__badge" aria-live="polite">
          Mode commande
        </span>
      ) : null}
    </div>
  )
})
