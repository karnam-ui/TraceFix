import React from 'react'
import { AlertTriangle, CheckCircle2, FileCode, ShieldCheck, XCircle } from 'lucide-react'
import type { VerificationSummary } from '../types'

interface PatchVerificationPanelProps {
  proposedPatch?: string
  patchSafety?: {
    is_valid?: boolean
    errors?: string[]
    prohibited_files?: string[]
    warnings?: string[]
  }
  verification?: VerificationSummary
}

export const PatchVerificationPanel: React.FC<PatchVerificationPanelProps> = ({
  proposedPatch,
  patchSafety,
  verification,
}) => {
  if (!proposedPatch && !verification) {
    return (
      <div className="panel-card">
        <div className="panel-header">
          <span className="panel-title">Patch Proposal & Sandbox Verification</span>
        </div>
        <div className="panel-body empty-placeholder">
          No repair executed yet. Enable &quot;Run Repair State Machine&quot; to generate and verify candidate fixes.
        </div>
      </div>
    )
  }

  // Format diff lines into syntax elements
  const renderDiffLines = (rawDiff: string) => {
    return rawDiff.split('\n').map((line, idx) => {
      let className = 'diff-line'
      if (line.startsWith('+') && !line.startsWith('+++')) {
        className += ' diff-add'
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        className += ' diff-del'
      } else if (line.startsWith('@@')) {
        className += ' diff-hunk'
      } else if (line.startsWith('---') || line.startsWith('+++')) {
        className += ' diff-header'
      }
      return (
        <div key={idx} className={className}>
          {line || ' '}
        </div>
      )
    })
  }

  const isVerified = verification?.status === 'VERIFIED'

  return (
    <div className="panel-card">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="panel-title">
            <FileCode size={14} />
            Repair Proposal & Verification
          </span>
          {patchSafety && patchSafety.is_valid !== undefined && (
            <span
              className={`badge ${patchSafety.is_valid ? 'badge-green' : 'badge-red'}`}
              style={{ display: 'inline-flex', gap: 3, alignItems: 'center' }}
            >
              <ShieldCheck size={10} />
              {patchSafety.is_valid ? 'AST SAFETY: PASS' : 'AST SAFETY: VIOLATION'}
            </span>
          )}
        </div>

        {verification && (
          <span
            className={`status-pill ${isVerified ? 'online' : 'offline'}`}
            style={{ fontSize: 11 }}
          >
            <span className="status-dot" />
            {verification.status} (exit {verification.exit_code})
          </span>
        )}
      </div>

      <div className="panel-body">
        {/* Verification Status Banner */}
        {verification && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 12,
              backgroundColor: isVerified ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
              border: `1px solid ${isVerified ? 'rgba(46, 160, 67, 0.4)' : 'rgba(248, 81, 73, 0.4)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {isVerified ? (
                <CheckCircle2 size={16} color="var(--status-success-text)" />
              ) : (
                <XCircle size={16} color="var(--status-danger-text)" />
              )}
              <span style={{ fontWeight: 600, fontSize: 12, color: isVerified ? 'var(--status-success-text)' : 'var(--status-danger-text)' }}>
                {isVerified
                  ? 'Candidate Patch Successfully Verified in Isolated Sandbox'
                  : 'Sandbox Verification Failed or Incomplete'}
              </span>
            </div>

            <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              Duration: {verification.duration_seconds.toFixed(2)}s | Passed: {verification.passed_tests.length} | Failed: {verification.failed_tests.length}
            </span>
          </div>
        )}

        {/* Safety Warnings if any */}
        {patchSafety && patchSafety.errors && patchSafety.errors.length > 0 && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 10,
              backgroundColor: 'var(--status-danger-bg)',
              border: '1px solid rgba(248, 81, 73, 0.4)',
              fontSize: 11,
              color: 'var(--status-danger-text)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600 }}>
              <AlertTriangle size={13} /> Safety Violations Detected:
            </div>
            <ul style={{ paddingLeft: 18, marginTop: 4 }}>
              {patchSafety.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Unified Diff Box */}
        {proposedPatch ? (
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
              Candidate Unified Diff:
            </div>
            <div className="diff-container">{renderDiffLines(proposedPatch)}</div>
          </div>
        ) : (
          <div className="empty-placeholder">No patch generated.</div>
        )}

        {/* Executed Tests Box */}
        {verification && verification.passed_tests.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Verified Test Executions (fail_to_pass target suite):
            </span>
            <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {verification.passed_tests.map((t, idx) => (
                <div
                  key={idx}
                  className="mono"
                  style={{
                    fontSize: 11,
                    padding: '3px 8px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: 'var(--bg-primary)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--status-success-text)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  <CheckCircle2 size={11} /> {t}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
