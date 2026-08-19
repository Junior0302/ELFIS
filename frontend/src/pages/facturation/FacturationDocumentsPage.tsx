/**
 * Espace Documents — CRUD FacturationPage + outlet nested `/documents/new`.
 * Le Composer modal est orchestré par DocumentCreateFlow (URL sync).
 */
import { Outlet } from 'react-router-dom'
import FacturationPage from '../FacturationPage'

export default function FacturationDocumentsPage() {
  return (
    <>
      <FacturationPage />
      {/* Route nested `new` : marqueur URL ; rendu Composer via DocumentCreateFlow */}
      <Outlet />
    </>
  )
}
