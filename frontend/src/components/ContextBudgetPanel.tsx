import React from 'react'
import { CheckCircle2, Sliders, XCircle } from 'lucide-react'
import type { ContextItem } from '../types'

interface ContextBudgetPanelProps {
  budget?: {
    budget_limit: number
    tokens_used: number
    utilization: number
    included_count: number
    excluded_count: number
  }
  items?: ContextItem[]
}

export const ContextBudgetPanel: React.FC<ContextBudgetPanelProps> = ({
  budget,
  items = [],
}) => {
  if (!budget || !items || items.length === 0) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <span className="panel-title">Context Selection & Token Budget</span>
        </div>
        <div className="panel-body empty-placeholder">
          Context selection details will appear here following retrieval.
        </div>
      </div>
    )
  }

  const pct = Math.min(100, budget.utilization * 100)
  const barClass =
    pct > 95 ? 'danger' : pct > 80 ? 'warning' : ''

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          <Sliders size={13} />
          Context Selection & Token Budget Accounting
        </span>
        <span className="badge badge-neutral mono">
          {budget.tokens_used.toLocaleString()} / {budget.budget_limit.toLocaleString()} tokens
        </span>
      </div>

      <div className="panel-body">
        {/* Progress Bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            Utilization: <strong>{pct.toFixed(1)}%</strong>
          </span>
          <span style={{ color: 'var(--text-secondary)' }}>
            {budget.included_count} included, {budget.excluded_count} excluded
          </span>
        </div>

        <div className="budget-bar-bg">
          <div
            className={`budget-bar-fill ${barClass}`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Selected / Excluded breakdown table */}
        <div className="table-wrapper" style={{ marginTop: 12 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 65 }}>Status</th>
                <th>Target Symbol</th>
                <th>File Path</th>
                <th style={{ width: 65 }}>Tokens</th>
                <th>Selection Decision</th>
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 15).map((it) => (
                <tr key={it.candidate_id}>
                  <td>
                    {it.included ? (
                      <span className="badge badge-green mono" style={{ display: 'inline-flex', gap: 3, alignItems: 'center' }}>
                        <CheckCircle2 size={10} /> IN
                      </span>
                    ) : (
                      <span className="badge badge-red mono" style={{ display: 'inline-flex', gap: 3, alignItems: 'center' }}>
                        <XCircle size={10} /> OUT
                      </span>
                    )}
                  </td>
                  <td className="mono" style={{ fontWeight: 600 }}>
                    {it.symbol || '<file root>'}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {it.file_path}
                  </td>
                  <td className="mono">{it.token_cost}</td>
                  <td style={{ color: it.included ? 'var(--text-secondary)' : 'var(--status-danger-text)', fontSize: 11 }}>
                    {it.included ? 'Packed in context manifest' : it.exclusion_reason || 'Excluded by budget'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
