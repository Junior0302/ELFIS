import { formatEuro } from '../../api'
import type { ElfisAnalysisHistoryItem, ElfisFieldValue, ElfisReport } from '../../elfisTypes'

function fieldText(field?: ElfisFieldValue) {
  if (!field || field.status === 'not_available' || field.value == null || field.value === '') {
    return '—'
  }
  return String(field.value)
}

function FieldGrid({ fields, labels }: { fields: Record<string, ElfisFieldValue>; labels: Record<string, string> }) {
  return (
    <div className="elfis-field-grid">
      {Object.entries(labels).map(([key, label]) => (
        <div key={key} className="elfis-field">
          <span>{label}</span>
          <strong>{fieldText(fields[key])}</strong>
        </div>
      ))}
    </div>
  )
}

type Props = {
  report: ElfisReport
  history: ElfisAnalysisHistoryItem[]
  onCopyJson: () => void
  onExportJson: () => void
  onReanalyze: () => void
  reanalyzing?: boolean
}

export default function ElfisReportPanel({
  report,
  history,
  onCopyJson,
  onExportJson,
  onReanalyze,
  reanalyzing,
}: Props) {
  const card = report.summary_card || {}
  const openSections = true

  return (
    <div className="elfis-report">
      <section className="panel elfis-summary-card">
        <span className="home-eyebrow">Résumé ELFIS</span>
        <h3 style={{ marginTop: 0 }}>Synthèse du document</h3>
        <div className="stats" style={{ marginBottom: '0.75rem' }}>
          <div className="stat">
            <span>Document</span>
            <strong style={{ fontSize: '1rem' }}>{card.document_type || '—'}</strong>
          </div>
          <div className="stat">
            <span>Montant</span>
            <strong style={{ fontSize: '1rem' }}>
              {card.amount_ttc != null ? formatEuro(card.amount_ttc) : '—'}
            </strong>
          </div>
          <div className="stat">
            <span>Confiance</span>
            <strong style={{ fontSize: '1rem' }}>{card.confidence_pct ?? '—'} %</strong>
          </div>
          <div className="stat">
            <span>Risque</span>
            <strong style={{ fontSize: '1rem' }}>{card.risk_level || '—'}</strong>
          </div>
          <div className="stat">
            <span>Anomalies</span>
            <strong style={{ fontSize: '1rem' }}>{card.anomaly_count ?? 0}</strong>
          </div>
          <div className="stat">
            <span>Statut</span>
            <strong style={{ fontSize: '1rem' }}>{card.ready_label || card.status || '—'}</strong>
          </div>
        </div>
        <p className="elfis-cfo-summary">{report.cfo_summary.summary}</p>
        <p className="muted" style={{ marginBottom: 0 }}>
          Champs extraits : {card.fields_extracted ?? '—'} · Analyse {report.metadata.processing_time_ms} ms ·
          Écriture {card.accounting_balanced ? 'équilibrée' : 'à contrôler'}
        </p>
      </section>

      <details className="panel elfis-accordion" open={openSections}>
        <summary>Confiance détaillée</summary>
        <p>{report.confidence.summary}</p>
        <ul className="elfis-factor-list">
          {report.confidence.factors.map((f) => (
            <li key={f.label} className={f.positive ? 'ok' : 'warn'}>
              <strong>{f.label}</strong>
              {f.detail ? <span> — {f.detail}</span> : null}
            </li>
          ))}
        </ul>
        {report.confidence.missing_fields.length > 0 && (
          <p className="muted">Manquants : {report.confidence.missing_fields.join(', ')}</p>
        )}
      </details>

      <details className="panel elfis-accordion">
        <summary>1. Données du fournisseur</summary>
        <FieldGrid
          fields={report.extraction.supplier}
          labels={{
            name: 'Nom',
            address: 'Adresse',
            siret: 'SIRET',
            siren: 'SIREN',
            vat_number: 'TVA',
            email: 'E-mail',
            phone: 'Téléphone',
            iban: 'IBAN',
            bic: 'BIC',
          }}
        />
      </details>

      <details className="panel elfis-accordion">
        <summary>2. Données du client</summary>
        <FieldGrid
          fields={report.extraction.customer}
          labels={{
            name: 'Nom',
            address: 'Adresse',
            siret: 'SIRET',
            vat_number: 'TVA',
            email: 'E-mail',
            phone: 'Téléphone',
          }}
        />
      </details>

      <details className="panel elfis-accordion">
        <summary>3. Informations du document</summary>
        <FieldGrid
          fields={report.extraction.document}
          labels={{
            type: 'Type',
            number: 'Numéro',
            issue_date: 'Date',
            due_date: 'Échéance',
            currency: 'Devise',
            payment_terms: 'Conditions',
            payment_method: 'Mode de paiement',
            order_reference: 'Réf. commande',
          }}
        />
      </details>

      <details className="panel elfis-accordion" open>
        <summary>4. Lignes du document</summary>
        {report.extraction.line_items.length === 0 ? (
          <p className="muted">Aucune ligne détaillée extraite (not_available).</p>
        ) : (
          <div className="elfis-table-wrap">
            <table className="entry-table elfis-lines-table">
              <thead>
                <tr>
                  <th>Désignation</th>
                  <th>Réf.</th>
                  <th>Qté</th>
                  <th>PU HT</th>
                  <th>Remise</th>
                  <th>TVA</th>
                  <th>Total HT</th>
                </tr>
              </thead>
              <tbody>
                {report.extraction.line_items.map((line, idx) => (
                  <tr key={idx}>
                    <td>{line.label || line.description || '—'}</td>
                    <td>{line.reference || '—'}</td>
                    <td>{line.quantity ?? '—'}</td>
                    <td>{line.unit_price_ht != null ? formatEuro(line.unit_price_ht) : '—'}</td>
                    <td>{line.discount != null ? formatEuro(line.discount) : '—'}</td>
                    <td>{line.vat_rate != null ? `${line.vat_rate} %` : '—'}</td>
                    <td>{line.total_ht != null ? formatEuro(line.total_ht) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="elfis-field-grid" style={{ marginTop: '0.75rem' }}>
          <div className="elfis-field">
            <span>Total HT</span>
            <strong>{fieldText(report.extraction.totals.total_ht)}</strong>
          </div>
          <div className="elfis-field">
            <span>Total TVA</span>
            <strong>{fieldText(report.extraction.totals.total_vat)}</strong>
          </div>
          <div className="elfis-field">
            <span>Total TTC</span>
            <strong>{fieldText(report.extraction.totals.total_ttc)}</strong>
          </div>
        </div>
      </details>

      <details className="panel elfis-accordion" open>
        <summary>5. Contrôles et cohérence</summary>
        {report.checks.anomalies.length === 0 ? (
          <p className="muted">Aucune anomalie détectée.</p>
        ) : (
          <ul className="elfis-anomaly-list">
            {report.checks.anomalies.map((a) => (
              <li key={a.id} className={`sev-${a.severity}`}>
                <strong>
                  {a.title} · {a.severity}
                  {a.blocking ? ' · bloquant' : ''}
                </strong>
                <span>{a.description}</span>
                <span className="muted">{a.recommended_action}</span>
              </li>
            ))}
          </ul>
        )}
      </details>

      <details className="panel elfis-accordion" open>
        <summary>6. Analyse comptable</summary>
        <p>
          Journal {report.accounting.journal} · {report.accounting.label}
        </p>
        <p className="muted">
          Débit {formatEuro(report.accounting.total_debit)} · Crédit{' '}
          {formatEuro(report.accounting.total_credit)} ·{' '}
          {report.accounting.balanced ? 'Équilibrée' : 'Déséquilibrée'}
        </p>
        {report.accounting.lines.length > 0 ? (
          <table className="entry-table">
            <thead>
              <tr>
                <th>Compte</th>
                <th>Libellé</th>
                <th>Débit</th>
                <th>Crédit</th>
                <th>Justification</th>
              </tr>
            </thead>
            <tbody>
              {report.accounting.lines.map((line, idx) => (
                <tr key={`${line.account}-${idx}`}>
                  <td>
                    {line.account}
                    <div className="muted">{line.certainty}</div>
                  </td>
                  <td>{line.label}</td>
                  <td>{formatEuro(line.debit)}</td>
                  <td>{formatEuro(line.credit)}</td>
                  <td>{line.justification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">Aucune ligne d’écriture.</p>
        )}
        {report.accounting.explanations.map((e) => (
          <p key={e} className="muted">
            {e}
          </p>
        ))}
      </details>

      <details className="panel elfis-accordion">
        <summary>7. Analyse financière</summary>
        {report.financial_analysis.messages.map((m) => (
          <p key={m}>{m}</p>
        ))}
        {report.financial_analysis.limitations && (
          <p className="muted">{report.financial_analysis.limitations}</p>
        )}
      </details>

      <details className="panel elfis-accordion">
        <summary>8. Analyse fournisseur</summary>
        {report.supplier_intelligence.messages.map((m) => (
          <p key={m}>{m}</p>
        ))}
        {report.supplier_intelligence.iban_history.length > 0 && (
          <p className="muted">IBAN connus : {report.supplier_intelligence.iban_history.join(', ')}</p>
        )}
      </details>

      <details className="panel elfis-accordion">
        <summary>9. Risques et anomalies</summary>
        <p>
          Niveau {report.risk_analysis.level} · score {report.risk_analysis.score}
        </p>
        <p>{report.risk_analysis.explanation}</p>
        <p className="muted">{report.risk_analysis.recommendation}</p>
        <ul>
          {report.risk_analysis.factors.map((f) => (
            <li key={f.code}>
              <strong>{f.label}</strong> — {f.detail}
            </li>
          ))}
        </ul>
      </details>

      <details className="panel elfis-accordion">
        <summary>10. Analyse fiscale</summary>
        {report.tax_analysis.messages.map((m) => (
          <p key={m}>{m}</p>
        ))}
        <p className="muted">{report.tax_analysis.disclaimer}</p>
      </details>

      <details className="panel elfis-accordion">
        <summary>11. Conformité</summary>
        <p>
          Synthèse : {report.compliance.synthesis} — {report.compliance.summary}
        </p>
        <ul className="elfis-compliance-list">
          {report.compliance.items.map((item) => (
            <li key={item.code}>
              <span className={`badge ${item.status === 'conforme' ? '' : 'warn'}`}>{item.status}</span>{' '}
              {item.label}
            </li>
          ))}
        </ul>
      </details>

      <details className="panel elfis-accordion" open>
        <summary>12. Recommandations</summary>
        <ul className="elfis-reco-list">
          {report.recommendations.map((r) => (
            <li key={`${r.title}-${r.reason}`}>
              <strong>
                [{r.priority}] {r.title}
              </strong>
              <span>
                {r.description} — {r.action}
              </span>
            </li>
          ))}
        </ul>
      </details>

      <details className="panel elfis-accordion">
        <summary>13. Synthèse CFO</summary>
        <p>
          <strong>Document :</strong> {report.cfo_summary.what_is_it}
        </p>
        <p>
          <strong>Cohérence :</strong> {report.cfo_summary.is_coherent}
        </p>
        <p>
          <strong>Impact :</strong> {report.cfo_summary.main_impact}
        </p>
        <p>
          <strong>À faire :</strong> {report.cfo_summary.next_action}
        </p>
        <ul>
          {report.cfo_summary.limitations.map((l) => (
            <li key={l} className="muted">
              {l}
            </li>
          ))}
        </ul>
      </details>

      <details className="panel elfis-accordion">
        <summary>14. Historique de l’analyse</summary>
        {history.length === 0 ? (
          <p className="muted">Aucun historique.</p>
        ) : (
          <ul>
            {history.map((h) => (
              <li key={h.id}>
                #{h.id} · {h.created_at ? new Date(h.created_at).toLocaleString('fr-FR') : '—'} · v
                {h.analysis_version} · {h.processing_time_ms} ms · {h.status}
              </li>
            ))}
          </ul>
        )}
      </details>

      <section className="panel">
        <h3>15–16. Exports & actions ELFIS</h3>
        <div className="actions">
          <button className="btn secondary" type="button" onClick={onExportJson}>
            Export JSON
          </button>
          <button className="btn secondary" type="button" onClick={onCopyJson}>
            Copier JSON
          </button>
          <button className="btn secondary" type="button" onClick={onReanalyze} disabled={reanalyzing}>
            {reanalyzing ? 'Réanalyse…' : 'Réanalyser ELFIS'}
          </button>
        </div>
      </section>
    </div>
  )
}
