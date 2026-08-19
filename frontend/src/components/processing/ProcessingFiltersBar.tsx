type Filters = {
  status: string
  pipeline_key: string
  document_id: string
}

export default function ProcessingFiltersBar({
  filters,
  onChange,
}: {
  filters: Filters
  onChange: (next: Filters) => void
}) {
  return (
    <div className="processing-filters">
      <label>
        Statut
        <select
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value })}
        >
          <option value="">Tous</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="retrying">retrying</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
          <option value="timed_out">timed_out</option>
          <option value="blocked">blocked</option>
        </select>
      </label>
      <label>
        Pipeline
        <input
          value={filters.pipeline_key}
          onChange={(e) => onChange({ ...filters, pipeline_key: e.target.value })}
          placeholder="document_basic_v1"
        />
      </label>
      <label>
        Document
        <input
          value={filters.document_id}
          onChange={(e) => onChange({ ...filters, document_id: e.target.value })}
          placeholder="document_id"
        />
      </label>
    </div>
  )
}
