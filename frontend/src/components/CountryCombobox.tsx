import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from 'react'
import {
  countriesForCombobox,
  getCountryLabel,
  normalizeCountryCode,
  type IsoCountry,
} from '../countries'
import { canSubmitCountry } from '../enterpriseSetup'

type CountryComboboxProps = {
  value: string
  onChange: (code: string) => void
  onBlur?: () => void
  id?: string
  describedBy?: string
  disabled?: boolean
}

/**
 * Combobox pays accessible — une seule source de sélection (pas de select natif).
 */
export default function CountryCombobox({
  value,
  onChange,
  onBlur,
  id,
  describedBy,
  disabled = false,
}: CountryComboboxProps) {
  const autoId = useId()
  const inputId = id || autoId
  const listboxId = `${inputId}-listbox`
  const inputRef = useRef<HTMLInputElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)

  const selectedLabel = canSubmitCountry(value) ? getCountryLabel(value) : ''
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(selectedLabel)
  const [activeIndex, setActiveIndex] = useState(0)
  const confirmedRef = useRef(canSubmitCountry(value))

  const options = useMemo(() => countriesForCombobox(query), [query])

  useEffect(() => {
    if (canSubmitCountry(value)) {
      const label = getCountryLabel(value)
      setQuery(label)
      confirmedRef.current = true
    } else if (!value) {
      setQuery('')
      confirmedRef.current = false
    }
  }, [value])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        closeList(true)
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [open, query, value])

  const openList = () => {
    if (disabled) return
    setOpen(true)
    const nextOptions = countriesForCombobox(query)
    const selectedIdx = nextOptions.findIndex((item) => item.code === value)
    setActiveIndex(selectedIdx >= 0 ? selectedIdx : 0)
  }

  const closeList = (revertUnconfirmed: boolean) => {
    setOpen(false)
    if (revertUnconfirmed && !confirmedRef.current) {
      if (canSubmitCountry(value)) {
        setQuery(getCountryLabel(value))
        confirmedRef.current = true
      } else {
        setQuery('')
      }
    } else if (confirmedRef.current && canSubmitCountry(value)) {
      setQuery(getCountryLabel(value))
    }
  }

  const selectOption = (country: IsoCountry) => {
    const code = normalizeCountryCode(country.code)
    confirmedRef.current = true
    setQuery(country.label)
    onChange(code)
    setOpen(false)
    inputRef.current?.focus()
  }

  const onInputChange = (next: string) => {
    setQuery(next)
    confirmedRef.current = false
    if (canSubmitCountry(value)) {
      onChange('')
    }
    setOpen(true)
    setActiveIndex(0)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!open) {
        openList()
        return
      }
      setActiveIndex((prev) => (options.length ? (prev + 1) % options.length : 0))
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (!open) {
        openList()
        return
      }
      setActiveIndex((prev) =>
        options.length ? (prev - 1 + options.length) % options.length : 0,
      )
      return
    }
    if (event.key === 'Enter') {
      if (open && options[activeIndex]) {
        event.preventDefault()
        selectOption(options[activeIndex])
      }
      return
    }
    if (event.key === 'Escape') {
      if (open) {
        event.preventDefault()
        closeList(true)
      }
      return
    }
    if (event.key === 'Tab') {
      closeList(true)
    }
  }

  const activeOption = options[activeIndex]
  const activeDescendant = activeOption ? `${listboxId}-opt-${activeOption.code}` : undefined

  const onOptionMouseDown = (event: MouseEvent, country: IsoCountry) => {
    event.preventDefault()
    selectOption(country)
  }

  return (
    <div className="enterprise-setup-combobox" ref={rootRef}>
      <input
        ref={inputRef}
        id={inputId}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={open ? activeDescendant : undefined}
        aria-describedby={describedBy}
        autoComplete="off"
        spellCheck={false}
        disabled={disabled}
        placeholder="Rechercher ou sélectionner un pays"
        value={query}
        onChange={(e) => onInputChange(e.target.value)}
        onFocus={openList}
        onClick={openList}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
      />
      {open ? (
        <ul
          id={listboxId}
          className="enterprise-setup-combobox-list"
          role="listbox"
          aria-label="Pays"
        >
          {options.length === 0 ? (
            <li className="enterprise-setup-combobox-empty" role="presentation">
              Aucun pays trouvé.
            </li>
          ) : (
            options.map((country, index) => {
              const selected = value === country.code && confirmedRef.current
              const active = index === activeIndex
              return (
                <li
                  key={country.code}
                  id={`${listboxId}-opt-${country.code}`}
                  role="option"
                  aria-selected={selected}
                  className={`enterprise-setup-combobox-option${active ? ' is-active' : ''}${
                    selected ? ' is-selected' : ''
                  }`}
                  onMouseDown={(event) => onOptionMouseDown(event, country)}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  {country.label}
                </li>
              )
            })
          )}
        </ul>
      ) : null}
    </div>
  )
}
