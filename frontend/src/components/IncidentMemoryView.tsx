import React, { useEffect, useState } from 'react'
import { CheckCircle2, Clock, Database, RefreshCw, ShieldAlert } from 'lucide-react'
import { api } from '../api/client'
import type { IncidentMemoryItem } from '../types'

export const IncidentMemoryView: React.FC = () => {
  const [records, setRecords] = useState<IncidentMemoryItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRecords = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.getMemoryRecords()
      setRecords(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incident memory records')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchRecords()
  }, [])

  return (
    <div>
      {/* Header explanation */}
      <div className="panel-card">
        <div className="panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={15} color="#bc8cff" />
            <span className="panel-title">Part B — Verified Incident Memory Repository</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fetchRecords}
            disabled={isLoading}
          >
            <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>
        <div className="panel-body">
          <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
            Incident Memory records verified past bug resolutions, candidate patches, and execution test evidence.
            To preserve evaluation integrity, TraceFix enforces strict <strong>chronological isolation</strong>:
            a historical incident can only be retrieved if its creation timestamp is prior to the active bug case.
          </p>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: 12,
            backgroundColor: 'var(--status-danger-bg)',
            border: '1px solid rgba(248, 81, 73, 0.4)',
            color: 'var(--status-danger-text)',
            borderRadius: 'var(--radius-sm)',
            marginBottom: 16,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <ShieldAlert size={16} />
          <span>Error loading memory repository: {error}</span>
        </div>
      )}

      {/* Memory items table / cards */}
      {records.length === 0 && !isLoading ? (
        <div className="panel-card">
          <div className="panel-body empty-placeholder">
            No verified incident records stored in memory yet. Running a verified bug repair will automatically persist it here.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {records.map((rec) => (
            <div key={rec.incident_id} className="panel-card" style={{ marginBottom: 0 }}>
              <div className="panel-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-purple)' }}>
                    {rec.incident_id}
                  </span>
                  <span className="badge badge-neutral mono">{rec.case_id}</span>
                  <span className="badge badge-neutral mono">rev: {rec.revision.slice(0, 8)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="status-pill online" style={{ fontSize: 10 }}>
                    <CheckCircle2 size={10} /> {rec.verification_status}
                  </span>
                  <span className="mono" style={{ color: 'var(--text-muted)', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={10} /> {rec.created_at}
                  </span>
                </div>
              </div>
              <div className="panel-body">
                <div style={{ marginBottom: 8, fontSize: 11, color: 'var(--text-secondary)' }}>
                  <strong>Bug Description:</strong> {rec.bug_report_snippet}
                </div>
                <div className="diff-container" style={{ maxHeight: 180 }}>
                  <pre style={{ margin: 0, padding: 8 }}>{rec.patch_diff}</pre>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
