import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type ToastTone = 'info' | 'success' | 'error'

export type ToastItem = {
  id: string
  message: string
  tone: ToastTone
}

type ToastContextValue = {
  toasts: ToastItem[]
  push: (message: string, tone?: ToastTone) => void
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message: string, tone: ToastTone = 'info') => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      setToasts((prev) => [...prev.slice(-4), { id, message, tone }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="ui-toast-stack" role="region" aria-label="Notifications toast" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`ui-toast ui-toast--${t.tone}`} role="status">
            <span>{t.message}</span>
            <button type="button" className="ui-toast-close" aria-label="Fermer" onClick={() => dismiss(t.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    return { toasts: [], push: () => undefined, dismiss: () => undefined }
  }
  return ctx
}
