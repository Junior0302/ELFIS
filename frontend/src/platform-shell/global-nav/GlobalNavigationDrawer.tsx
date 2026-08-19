/**

 * Drawer hamburger — délègue à ElfisGlobalNavigation (même config que sidebar).

 */



import type { RefObject } from 'react'

import { ElfisGlobalNavigation, ELFIS_GLOBAL_NAV_ID } from './ElfisGlobalNavigation'



export { ELFIS_GLOBAL_NAV_ID }



type GlobalNavigationDrawerProps = {

  open: boolean

  onOpenChange: (open: boolean) => void

  returnFocusRef: RefObject<HTMLElement | null>

}



export function GlobalNavigationDrawer({

  open,

  onOpenChange,

  returnFocusRef,

}: GlobalNavigationDrawerProps) {

  return (

    <ElfisGlobalNavigation

      mode="drawer"

      open={open}

      onOpenChange={onOpenChange}

      returnFocusRef={returnFocusRef}

    />

  )

}


