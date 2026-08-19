import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { Dialog } from './Dialog'
import { Button } from '../components/Button'
import { cx } from '../components/cx'

export type ConfirmTone = 'neutral' | 'warning' | 'danger'

export type ConfirmDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void | Promise<void>
  loading?: boolean
  tone?: ConfirmTone
  confirmDisabled?: boolean
  details?: ReactNode
  irreversible?: boolean
  error?: string | null
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirmer',
  cancelLabel = 'Annuler',
  onConfirm,
  loading: loadingProp,
  tone = 'neutral',
  confirmDisabled = false,
  details,
  irreversible = false,
  error = null,
}: ConfirmDialogProps) {
  const [internalLoading, setInternalLoading] = useState(false)
  const loading = loadingProp ?? internalLoading
  const cancelRef = useRef<HTMLButtonElement>(null)
  const confirmRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) setInternalLoading(false)
  }, [open])

  useLayoutEffect(() => {
    if (!open) return
    const target = tone === 'danger' ? cancelRef.current : confirmRef.current
    target?.focus()
  }, [open, tone])

  const handleConfirm = async () => {
    if (loading || confirmDisabled) return
    try {
      setInternalLoading(true)
      await onConfirm()
      onOpenChange(false)
    } catch {
      /* parent may set error prop */
    } finally {
      setInternalLoading(false)
    }
  }

  const initialFocusRef = tone === 'danger' ? cancelRef : confirmRef

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      size="sm"
      closeOnEscape={!loading}
      closeOnBackdrop={!loading}
      dismissible={!loading}
      overlayType="confirm_dialog"
      initialFocusRef={initialFocusRef}
      className={cx('ds-confirm', `ds-confirm--${tone}`)}
      footer={
        <>
          <Button
            ref={cancelRef}
            type="button"
            variant="secondary"
            disabled={loading}
            onClick={() => onOpenChange(false)}
          >
            {cancelLabel}
          </Button>
          <Button
            ref={confirmRef}
            type="button"
            variant={tone === 'danger' ? 'danger' : 'primary'}
            disabled={loading || confirmDisabled}
            aria-busy={loading || undefined}
            onClick={() => void handleConfirm()}
          >
            {loading ? '…' : confirmLabel}
          </Button>
        </>
      }
    >
      {irreversible ? (
        <p className="ds-confirm__irreversible" role="note">
          Cette action est irréversible.
        </p>
      ) : null}
      {details}
      {error ? (
        <p className="ds-confirm__error" role="alert">
          {error}
        </p>
      ) : null}
    </Dialog>
  )
}
