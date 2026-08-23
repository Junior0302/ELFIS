import { Outlet } from 'react-router-dom'
import { ElfisAuthShell } from '../login/ElfisAuthShell'
import './auth.css'

/**
 * Layout auth public (register / forgot-password) — même chrome ELFIS Core que /login.
 */
export default function AuthLayout() {
  return (
    <ElfisAuthShell>
      <Outlet />
    </ElfisAuthShell>
  )
}
