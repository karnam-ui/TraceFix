import React from 'react'
import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'
import type { LifecycleStage } from '../types'

interface InvestigationTimelineProps {
  stages: LifecycleStage[]
  isLoading?: boolean
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  stages,
  isLoading,
}) => {
  if (!stages || stages.length === 0) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <span className="panel-title">Lifecycle & Progress Timeline</span>
        </div>
        <div className="panel-body empty-placeholder">
          Submit an investigation to inspect execution stages.
        </div>
      </div>
    )
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 size={13} color="#3fb950" />
      case 'failed':
        return <AlertCircle size={13} color="#f85149" />
      case 'running':
        return <Loader2 size={13} color="#58a6ff" className="animate-spin" />
      default:
        return <Clock size={13} color="#6e7681" />
    }
  }

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">
          Lifecycle & Execution Timeline ({stages.length} Stages)
        </span>
        {isLoading && (
          <span className="badge badge-blue">
            <Loader2 size={10} className="animate-spin" /> RUNNING
          </span>
        )}
      </div>

      <div className="panel-body">
        <div className="timeline-list">
          {stages.map((st, idx) => (
            <div key={st.stage_id} className={`timeline-item ${st.status}`}>
              <div className="timeline-badge">{getStatusIcon(st.status)}</div>
              <div className="timeline-content">
                <div className="timeline-title-row">
                  <span className="timeline-name">
                    {idx + 1}. {st.name}
                  </span>
                  {st.elapsed_ms > 0 && (
                    <span className="timeline-elapsed">{st.elapsed_ms.toFixed(1)} ms</span>
                  )}
                </div>
                {st.detail && <div className="timeline-detail">{st.detail}</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
