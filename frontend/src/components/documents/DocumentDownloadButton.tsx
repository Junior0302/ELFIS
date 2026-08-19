import { can } from '../../types/permissions'
import { downloadRegistryDocument } from '../../services/documentRegistryApi'

type Props = {
  documentId: string
  token: string
  orgId?: number | null
  permissions?: readonly string[]
  label?: string
}

export default function DocumentDownloadButton({
  documentId,
  token,
  orgId,
  permissions,
  label = 'Télécharger',
}: Props) {
  const allowed =
    can(permissions, 'documents.download') ||
    can(permissions, 'documents.read') ||
    can(permissions, '*')
  if (!allowed) return null

  async function onClick() {
    const { blob, filename } = await downloadRegistryDocument(documentId, token, orgId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <button type="button" className="platform-action" onClick={onClick}>
      {label}
    </button>
  )
}
