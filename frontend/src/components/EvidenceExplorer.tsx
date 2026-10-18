import React, { useState } from 'react'
import { Check, Filter, Layers } from 'lucide-react'
import type { RetrievalItem } from '../types'

interface EvidenceExplorerProps {
  items: RetrievalItem[]
  strategyUsed?: string
}

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({
  items,
  strategyUsed,
}) => {
  const [filterText, setFilterText] = useState('')
  const [showOnlyHits, setShowOnlyHits] = useState(false)

  if (!items || items.length === 0) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <span className="panel-title">Retrieved Evidence & Codebase Localization</span>
        </div>
        <div className="panel-body empty-placeholder">
          No retrieval results yet. Run an investigation to view ranked evidence.
        </div>
      </div>
    )
  }

  const filteredItems = items.filter((it) => {
    if (showOnlyHits && !it.is_ground_truth_function && !it.is_ground_truth_file) {
      return false
    }
    if (!filterText) return true
    const q = filterText.toLowerCase()
    return (
      it.file.toLowerCase().includes(q) ||
      it.symbol.toLowerCase().includes(q) ||
      it.strategy.toLowerCase().includes(q)
    )
  })

  const functionHits = items.filter((it) => it.is_ground_truth_function).length
  const fileHits = items.filter((it) => it.is_ground_truth_file).length

  return (
    <div className="panel-card">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="panel-title">
            <Layers size={14} />
            Retrieved Evidence ({items.length} Candidates)
          </span>
          {strategyUsed && (
            <span className="badge badge-neutral mono">strategy: {strategyUsed}</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            className={`badge ${functionHits > 0 ? 'badge-green' : 'badge-neutral'}`}
            title="Function-level ground truth matches"
          >
            Fn Hits: {functionHits} / {items.length}
          </span>
          <span
            className={`badge ${fileHits > 0 ? 'badge-blue' : 'badge-neutral'}`}
            title="File-level ground truth matches"
          >
            File Hits: {fileHits} / {items.length}
          </span>
        </div>
      </div>

      <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--border-default)', display: 'flex', gap: 10 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            className="form-input"
            style={{ paddingLeft: 26, fontSize: 11 }}
            placeholder="Filter by file, symbol, or strategy..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
          <Filter
            size={12}
            color="var(--text-muted)"
            style={{ position: 'absolute', left: 8, top: 9 }}
          />
        </div>
        <button
          type="button"
          className={`btn btn-sm ${showOnlyHits ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setShowOnlyHits(!showOnlyHits)}
        >
          {showOnlyHits && <Check size={12} />} Only GT Hits
        </button>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 45 }}>Rank</th>
              <th style={{ width: 60 }}>Score</th>
              <th>Target Symbol / Function</th>
              <th>File Path</th>
              <th style={{ width: 75 }}>Strategy</th>
              <th style={{ width: 85 }}>Ground Truth</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((it) => (
              <tr
                key={it.evidence_id}
                className={it.is_ground_truth_function ? 'gt-hit' : ''}
              >
                <td className="mono" style={{ fontWeight: 600 }}>
                  #{it.rank}
                </td>
                <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                  {it.score.toFixed(3)}
                </td>
                <td className="mono">
                  <span style={{ color: it.is_ground_truth_function ? 'var(--status-success-text)' : 'inherit', fontWeight: 600 }}>
                    {it.symbol || '<file root>'}
                  </span>
                  {it.lines && (
                    <span style={{ color: 'var(--text-muted)', marginLeft: 6, fontSize: 10 }}>
                      L{it.lines[0]}-{it.lines[1]}
                    </span>
                  )}
                </td>
                <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                  {it.file}
                </td>
                <td>
                  <span className="badge badge-neutral mono" style={{ fontSize: 9 }}>
                    {it.strategy}
                  </span>
                </td>
                <td>
                  {it.is_ground_truth_function ? (
                    <span className="badge badge-green mono">FN HIT</span>
                  ) : it.is_ground_truth_file ? (
                    <span className="badge badge-blue mono">FILE HIT</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
