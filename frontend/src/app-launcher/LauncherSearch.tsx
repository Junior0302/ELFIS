import type { Ref } from 'react'

import { cx } from '../design-system/components/cx'



export type LauncherSearchProps = {

  value: string

  onChange: (value: string) => void

  inputRef?: Ref<HTMLInputElement>

  resultsId?: string

  className?: string

}



export function LauncherSearch({

  value,

  onChange,

  inputRef,

  resultsId = 'launcher-app-results',

  className,

}: LauncherSearchProps) {

  return (

    <div className={cx('launcher-search', className)}>

      <label className="launcher-search__field">

        <span className="launcher-search__label">Rechercher un espace ou une fonction</span>

        <input

          ref={inputRef}

          type="search"

          value={value}

          onChange={(e) => onChange(e.target.value)}

          placeholder="Rechercher un espace, une fonction…"

          autoComplete="off"

          aria-controls={resultsId}

          data-launcher-search

        />

      </label>

      {value ? (

        <button

          type="button"

          className="launcher-search__clear"

          onClick={() => onChange('')}

          aria-label="Effacer la recherche"

        >

          Effacer

        </button>

      ) : null}

    </div>

  )

}


