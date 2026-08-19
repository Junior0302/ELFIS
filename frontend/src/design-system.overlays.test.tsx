/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState, type ReactNode } from 'react'
import {
  ConfirmDialog,
  Dialog,
  Drawer,
  OverlayProvider,
  Popover,
  Tooltip,
  useOverlayManager,
  __resetScrollLockForTests,
} from './design-system'
import './design-system/overlays/styles/overlays.css'

afterEach(() => {
  cleanup()
  __resetScrollLockForTests()
  document.getElementById('elfis-overlay-root')?.remove()
})

function wrap(ui: ReactNode) {
  return render(<OverlayProvider>{ui}</OverlayProvider>)
}

function ControlledDialog(props: {
  closeOnEscape?: boolean
  closeOnBackdrop?: boolean
  dismissible?: boolean
}) {
  const [open, setOpen] = useState(true)
  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
      title="Titre dialog"
      description="Description dialog"
      closeOnEscape={props.closeOnEscape}
      closeOnBackdrop={props.closeOnBackdrop}
      dismissible={props.dismissible}
    >
      <button type="button">Action A</button>
      <button type="button">Action B</button>
    </Dialog>
  )
}

describe('E1.4.1 Overlay Dialog', () => {
  it('ouvre avec role dialog et aria', async () => {
    wrap(<ControlledDialog />)
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText('Titre dialog')).toBeInTheDocument()
    expect(screen.getByText('Description dialog')).toBeInTheDocument()
  })

  it('ferme via bouton close', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog />)
    await user.click(screen.getByRole('button', { name: 'Fermer' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('ferme via Escape', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog />)
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('closeOnEscape=false ignore Escape', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog closeOnEscape={false} />)
    await user.keyboard('{Escape}')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('ferme via backdrop', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog />)
    const backdrop = document.querySelector('.ds-overlay-backdrop')!
    await user.click(backdrop)
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('closeOnBackdrop=false ignore backdrop', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog closeOnBackdrop={false} />)
    const backdrop = document.querySelector('.ds-overlay-backdrop')!
    await user.click(backdrop)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('clic contenu ne ferme pas', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog />)
    await user.click(screen.getByRole('button', { name: 'Action A' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('applique scroll lock', async () => {
    wrap(<ControlledDialog />)
    await screen.findByRole('dialog')
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('non dismissible masque close et ignore Escape', async () => {
    const user = userEvent.setup()
    wrap(<ControlledDialog dismissible={false} />)
    expect(screen.queryByRole('button', { name: 'Fermer' })).toBeNull()
    await user.keyboard('{Escape}')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})

describe('E1.4.1 ConfirmDialog', () => {
  it('confirm / cancel / danger focus Annuler', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    function Demo() {
      const [open, setOpen] = useState(true)
      return (
        <ConfirmDialog
          open={open}
          onOpenChange={setOpen}
          title="Supprimer ?"
          description="Irréversible"
          tone="danger"
          onConfirm={onConfirm}
        />
      )
    }
    wrap(<Demo />)
    const cancel = await screen.findByRole('button', { name: 'Annuler' })
    await waitFor(() => expect(cancel).toHaveFocus())
    await user.click(cancel)
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('bloque double clic pendant loading async', async () => {
    const user = userEvent.setup()
    let resolve!: () => void
    const onConfirm = vi.fn(
      () =>
        new Promise<void>((r) => {
          resolve = r
        }),
    )
    function Demo() {
      const [open, setOpen] = useState(true)
      return (
        <ConfirmDialog
          open={open}
          onOpenChange={setOpen}
          title="Confirmer"
          description="…"
          onConfirm={onConfirm}
        />
      )
    }
    wrap(<Demo />)
    const confirmBtn = await screen.findByRole('button', { name: 'Confirmer' })
    await user.click(confirmBtn)
    await user.click(confirmBtn)
    expect(onConfirm).toHaveBeenCalledTimes(1)
    resolve()
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
})

describe('E1.4.1 Drawer', () => {
  it('ouvre à droite et ferme Escape', async () => {
    const user = userEvent.setup()
    function Demo() {
      const [open, setOpen] = useState(true)
      return (
        <Drawer open={open} onOpenChange={setOpen} title="Panneau" side="right">
          Contenu drawer
        </Drawer>
      )
    }
    wrap(<Demo />)
    expect(await screen.findByText('Contenu drawer')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('bottom sheet', async () => {
    wrap(
      <Drawer open onOpenChange={() => undefined} title="Mobile" side="bottom">
        Bottom
      </Drawer>,
    )
    const dialog = await screen.findByRole('dialog')
    expect(dialog.className).toContain('ds-drawer--bottom')
  })
})

describe('E1.4.1 Tooltip / Popover', () => {
  it('tooltip focus + aria-describedby', async () => {
    const user = userEvent.setup()
    wrap(
      <Tooltip content="Aide">
        <button type="button">Info</button>
      </Tooltip>,
    )
    const btn = screen.getByRole('button', { name: 'Info' })
    await user.tab()
    expect(btn).toHaveFocus()
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Aide'))
    expect(btn).toHaveAttribute('aria-describedby')
  })

  it('popover ouverture trigger et Escape', async () => {
    const user = userEvent.setup()
    function Demo() {
      const [open, setOpen] = useState(false)
      return (
        <Popover
          open={open}
          onOpenChange={setOpen}
          trigger={<button type="button">Menu</button>}
        >
          <button type="button">Item</button>
        </Popover>
      )
    }
    wrap(<Demo />)
    await user.click(screen.getByRole('button', { name: 'Menu' }))
    expect(await screen.findByRole('button', { name: 'Item' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Item' })).toBeNull())
  })
})

describe('E1.4.1 nested overlays', () => {
  it('Escape ferme uniquement le top overlay', async () => {
    const user = userEvent.setup()
    function Demo() {
      const [outer, setOuter] = useState(true)
      const [inner, setInner] = useState(true)
      return (
        <>
          <Dialog open={outer} onOpenChange={setOuter} title="Outer" description="o">
            outer
          </Dialog>
          <Dialog open={inner} onOpenChange={setInner} title="Inner" description="i">
            inner
          </Dialog>
        </>
      )
    }
    wrap(<Demo />)
    const dialogs = await screen.findAllByRole('dialog')
    expect(dialogs.length).toBe(2)
    await user.keyboard('{Escape}')
    await waitFor(() => {
      expect(screen.getByText('Outer')).toBeInTheDocument()
      expect(screen.queryByText('Inner')).toBeNull()
    })
  })
})

describe('E1.4.1 Overlay Orchestrator integration', () => {
  it('enregistre Dialog / Drawer / Popover', async () => {
    let api: ReturnType<typeof useOverlayManager> | null = null
    function Probe() {
      api = useOverlayManager()
      return null
    }
    function Demo() {
      const [d, setD] = useState(true)
      const [dr, setDr] = useState(true)
      const [p, setP] = useState(true)
      return (
        <>
          <Probe />
          <Dialog open={d} onOpenChange={setD} title="D" description="x">
            dialog
          </Dialog>
          <Drawer open={dr} onOpenChange={setDr} title="Dr" side="right">
            drawer
          </Drawer>
          <Popover open={p} onOpenChange={setP} trigger={<button type="button">T</button>}>
            pop
          </Popover>
        </>
      )
    }
    wrap(<Demo />)
    await screen.findByText('dialog')
    await waitFor(() => expect(api!.getStackDepth()).toBe(3))
    const types = api!.getStack().map((s) => s.type)
    expect(types).toContain('dialog')
    expect(types).toContain('drawer')
    expect(types).toContain('popover')
  })

  it('closeAll logout nettoie stack et body', async () => {
    let api: ReturnType<typeof useOverlayManager> | null = null
    function Probe() {
      api = useOverlayManager()
      return null
    }
    function Demo() {
      const [a, setA] = useState(true)
      const [b, setB] = useState(true)
      return (
        <>
          <Probe />
          <Dialog open={a} onOpenChange={setA} title="A" description="a">
            a
          </Dialog>
          <Dialog open={b} onOpenChange={setB} title="B" description="b">
            b
          </Dialog>
        </>
      )
    }
    wrap(<Demo />)
    await screen.findAllByRole('dialog')
    expect(document.body.style.overflow).toBe('hidden')
    api!.closeAll('logout')
    await waitFor(() => expect(api!.getStackDepth()).toBe(0))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(document.body.style.overflow).not.toBe('hidden'))
  })

  it('émet elfis:overlay-opened sans payload sensible', async () => {
    const events: CustomEvent[] = []
    const handler = (e: Event) => events.push(e as CustomEvent)
    window.addEventListener('elfis:overlay-opened', handler)
    wrap(
      <Dialog open onOpenChange={() => undefined} title="Ev" description="d">
        x
      </Dialog>,
    )
    await screen.findByRole('dialog')
    window.removeEventListener('elfis:overlay-opened', handler)
    expect(events.length).toBeGreaterThanOrEqual(1)
    const detail = events[0]!.detail
    expect(detail.overlayId).toBeTruthy()
    expect(detail.overlayType).toBe('dialog')
    expect(detail).not.toHaveProperty('title')
  })
})
