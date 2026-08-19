import type { AuditCategory } from '../../types/audit'

export default function AuditCategoryBadge({ category }: { category: AuditCategory | string }) {
  return (
    <span className="audit-badge audit-category" title={`Catégorie ${category}`}>
      {category}
    </span>
  )
}
