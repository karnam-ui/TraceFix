import React from 'react'
import { Activity, Database, GitBranch, Terminal } from 'lucide-react'
import type { HealthResponse } from '../types'

interface AppHeaderProps {
  health: HealthResponse | null
  healthError: string | null
  activeTab: 'workspace' | 'graph' | 'memory' | 'eval'
  onSelectTab: (tab: 'workspace' | 'graph' | 'memory' | 'eval') => void
  currentRevision?: string
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  health,
  healthError,
  activeTab,
  onSelectTab,
  currentRevision,
}) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="logo-badge">
          <Terminal size={18} color="#388bfd" />
          <span>TRACEFIX</span>
        </div>
        <span className="tagline">Graph-Native Bug Resolution & Verified Repair</span>
      </div>

      <div className="header-meta">
        <nav className="nav-tabs">
          <button
            type="button"
            className={`nav-tab ${activeTab === 'workspace' ? 'active' : ''}`}
            onClick={() => onSelectTab('workspace')}
          >
            <Activity size={14} />
            Investigation
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === 'graph' ? 'active' : ''}`}
            onClick={() => onSelectTab('graph')}
          >
            <GitBranch size={14} />
            Graph Explorer
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === 'memory' ? 'active' : ''}`}
            onClick={() => onSelectTab('memory')}
          >
            <Database size={14} />
            Incident Memory (Part B)
          </button>
          <button
            type="button"
            className={`nav-tab ${activeTab === 'eval' ? 'active' : ''}`}
            onClick={() => onSelectTab('eval')}
          >
            Evaluation & Benchmarks
          </button>
        </nav>

        {currentRevision && (
          <span className="badge badge-neutral mono" title={`Target Revision: ${currentRevision}`}>
            rev: {currentRevision.slice(0, 8)}
          </span>
        )}

        {/* Real Live Backend Health Badge */}
        {health ? (
          <div
            className={`status-pill ${
              health.status === 'ok' && health.falkordb_connected ? 'online' : 'degraded'
            }`}
            title={`API: ${health.status} | FalkorDB: ${
              health.falkordb_connected ? 'Connected' : 'Disconnected'
            } | Cases: ${health.active_cases_count} | Graphs: ${health.persisted_graphs_count}`}
          >
            <span className="status-dot" />
            <span>
              {health.falkordb_connected ? 'LIVE (FalkorDB OK)' : 'DEGRADED (FalkorDB OFFLINE)'}
            </span>
          </div>
        ) : healthError ? (
          <div className="status-pill offline" title={healthError}>
            <span className="status-dot" />
            <span>BACKEND DISCONNECTED</span>
          </div>
        ) : (
          <div className="status-pill degraded">
            <span className="status-dot" />
            <span>CONNECTING...</span>
          </div>
        )}
      </div>
    </header>
  )
}
