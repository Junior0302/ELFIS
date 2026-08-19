import { forwardRef } from 'react'

import { cx } from '../design-system/components/cx'



export type AppLauncherTriggerProps = {

  open: boolean

  onClick?: () => void

  controlsId: string

  className?: string

  compact?: boolean

}



function GridIcon() {

  return (

    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden className="app-launcher-trigger__icon">

      <rect x="1" y="1" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="7" y="1" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="13" y="1" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="1" y="7" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="7" y="7" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="13" y="7" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="1" y="13" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="7" y="13" width="4" height="4" rx="1" fill="currentColor" />

      <rect x="13" y="13" width="4" height="4" rx="1" fill="currentColor" />

    </svg>

  )

}



export const AppLauncherTrigger = forwardRef<HTMLButtonElement, AppLauncherTriggerProps>(

  function AppLauncherTrigger({ open, onClick, controlsId, className, compact }, ref) {

    return (

      <button

        ref={ref}

        type="button"

        className={cx('app-launcher-trigger', compact && 'app-launcher-trigger--compact', className)}

        aria-expanded={open}

        aria-haspopup="dialog"

        aria-controls={controlsId}

        title="Espaces ELFIS"

        onClick={onClick}

      >

        <GridIcon />

        <span className="app-launcher-trigger__label">Espaces</span>

      </button>

    )

  },

)


