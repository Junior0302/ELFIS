import {
  Children,
  cloneElement,
  createContext,
  isValidElement,
  useContext,
  useId,
  useState,
  type ReactElement,
  type ReactNode,
} from 'react'
import { cx } from './cx'

export type TabsProps = {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: ReactNode
  className?: string
  scrollable?: boolean
}

export type TabListProps = {
  children: ReactNode
  className?: string
  scrollable?: boolean
}

export type TabProps = {
  value: string
  children: ReactNode
  disabled?: boolean
  className?: string
}

export type TabPanelProps = {
  value: string
  children: ReactNode
  className?: string
}

type TabsCtx = {
  value: string
  setValue: (v: string) => void
  baseId: string
}

const TabsContext = createContext<TabsCtx | null>(null)

function useTabsCtx() {
  const ctx = useContext(TabsContext)
  if (!ctx) throw new Error('Tabs.* must be used within <Tabs>')
  return ctx
}

/** Accessible tabs primitive — Design System. */
export function Tabs({
  value: controlled,
  defaultValue,
  onValueChange,
  children,
  className,
  scrollable = true,
}: TabsProps) {
  const baseId = useId()
  const [uncontrolled, setUncontrolled] = useState(defaultValue ?? '')
  const value = controlled ?? uncontrolled
  const setValue = (v: string) => {
    if (controlled === undefined) setUncontrolled(v)
    onValueChange?.(v)
  }

  return (
    <TabsContext.Provider value={{ value, setValue, baseId }}>
      <div className={cx('ds-tabs', scrollable && 'ds-tabs--scrollable', className)}>{children}</div>
    </TabsContext.Provider>
  )
}

export function TabList({ children, className, scrollable }: TabListProps) {
  return (
    <div
      role="tablist"
      className={cx('ds-tabs__list', scrollable && 'ds-tabs__list--scroll', className)}
    >
      {Children.map(children, (child) => {
        if (!isValidElement(child)) return child
        return cloneElement(child as ReactElement)
      })}
    </div>
  )
}

export function Tab({ value, children, disabled, className }: TabProps) {
  const { value: current, setValue, baseId } = useTabsCtx()
  const selected = current === value
  return (
    <button
      type="button"
      role="tab"
      id={`${baseId}-tab-${value}`}
      aria-selected={selected}
      aria-controls={`${baseId}-panel-${value}`}
      tabIndex={selected ? 0 : -1}
      disabled={disabled}
      className={cx('ds-tabs__tab', selected && 'is-active', className)}
      onClick={() => setValue(value)}
    >
      {children}
    </button>
  )
}

export function TabPanel({ value, children, className }: TabPanelProps) {
  const { value: current, baseId } = useTabsCtx()
  if (current !== value) return null
  return (
    <div
      role="tabpanel"
      id={`${baseId}-panel-${value}`}
      aria-labelledby={`${baseId}-tab-${value}`}
      className={cx('ds-tabs__panel', className)}
    >
      {children}
    </div>
  )
}
