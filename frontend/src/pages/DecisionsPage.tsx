import { Navigate } from 'react-router-dom'

/** Alias C1.17 — la liste décisions est remplacée par la Boîte de travail. */
export default function DecisionsPage() {
  return <Navigate to="/work-queue" replace />
}
