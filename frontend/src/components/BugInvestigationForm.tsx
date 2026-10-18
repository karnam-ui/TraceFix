import React, { useState } from 'react'
import { Play, RotateCcw } from 'lucide-react'
import type { CaseSummary, InvestigateRequest } from '../types'

interface BugInvestigationFormProps {
  cases: CaseSummary[]
  isLoading: boolean
  onSubmit: (req: InvestigateRequest) => void
  onReset: () => void
  currentCaseId?: string
}

export const BugInvestigationForm: React.FC<BugInvestigationFormProps> = ({
  cases,
  isLoading,
  onSubmit,
  onReset,
  currentCaseId,
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>(currentCaseId || 'psf__requests-1142')
  const [strategy, setStrategy] = useState<'graph' | 'fused' | 'lexical' | 'memory'>('graph')
  const [budget, setBudget] = useState<number>(4000)
  const [mockMode, setMockMode] = useState<boolean>(true)
  const [executeRepair, setExecuteRepair] = useState<boolean>(true)
  const [customReport, setCustomReport] = useState<string>('')
  const [customRevision, setCustomRevision] = useState<string>('22623bd8c265b78b161542663ee980738441c307')
  const [customRepo, setCustomRepo] = useState<string>('requests')

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId)
    if (caseId && caseId !== 'custom') {
      const found = cases.find((c) => c.case_id === caseId)
      if (found) {
        setCustomReport(found.bug_report_preview)
        setCustomRevision(found.revision)
        setCustomRepo(found.repo)
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isLoading) return

    const req: InvestigateRequest = {
      case_id: selectedCaseId === 'custom' ? undefined : selectedCaseId,
      repo: customRepo,
      revision: customRevision,
      bug_report: customReport,
      strategy,
      budget,
      mock: mockMode,
      execute_repair: executeRepair,
    }
    onSubmit(req)
  }

  const selectedCase = cases.find((c) => c.case_id === selectedCaseId)

  return (
    <div className="panel-card">
      <div className="panel-header">
        <span className="panel-title">Bug Investigation Configuration</span>
        {selectedCase && (
          <span className="badge badge-blue mono">
            {selectedCase.localizable ? 'LOCALIZABLE' : 'NON-LOCALIZABLE'}
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="panel-body">
        {/* Preset Case Picker */}
        <div className="form-group">
          <label className="form-label" htmlFor="case-select">
            Target Bug Case (Frozen Benchmark Pool)
          </label>
          <select
            id="case-select"
            className="form-select mono"
            value={selectedCaseId}
            onChange={(e) => handleSelectCase(e.target.value)}
            disabled={isLoading}
          >
            <optgroup label="Frozen Pilot Subset (A6c)">
              <option value="psf__requests-1142">psf__requests-1142 (22623bd8)</option>
              <option value="psf__requests-1376">psf__requests-1376 (2aabb71d)</option>
              <option value="psf__requests-1537">psf__requests-1537 (d8268fb7)</option>
              <option value="psf__requests-1724">psf__requests-1724 (1ba83c47)</option>
              <option value="psf__requests-1766">psf__requests-1766 (84773555)</option>
            </optgroup>
            {cases.length > 5 && (
              <optgroup label="Full Benchmark Pool (44 Cases)">
                {cases
                  .filter(
                    (c) =>
                      ![
                        'psf__requests-1142',
                        'psf__requests-1376',
                        'psf__requests-1537',
                        'psf__requests-1724',
                        'psf__requests-1766',
                      ].includes(c.case_id)
                  )
                  .map((c) => (
                    <option key={c.case_id} value={c.case_id}>
                      {c.case_id} ({c.short_sha})
                    </option>
                  ))}
              </optgroup>
            )}
            <option value="custom">[Custom Bug Input]</option>
          </select>
        </div>

        {/* Ground Truth Summary */}
        {selectedCase && selectedCase.ground_truth_functions.length > 0 && (
          <div className="form-group">
            <span className="form-label">Provisional Ground Truth</span>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }} className="mono">
              <strong>Fn:</strong> {selectedCase.ground_truth_functions.join(', ')}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }} className="mono">
              <strong>Files:</strong> {selectedCase.ground_truth_files.join(', ')}
            </div>
          </div>
        )}

        {/* Bug Report Input */}
        <div className="form-group">
          <label className="form-label" htmlFor="bug-report-input">
            Bug Description & Symptoms
          </label>
          <textarea
            id="bug-report-input"
            className="form-textarea"
            rows={4}
            value={customReport}
            onChange={(e) => setCustomReport(e.target.value)}
            disabled={isLoading}
            placeholder="Describe the bug, traceback, or reproduction steps..."
            required
          />
        </div>

        {/* Strategy & Budget Grid */}
        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="strategy-select">
              Retrieval Strategy
            </label>
            <select
              id="strategy-select"
              className="form-select"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as any)}
              disabled={isLoading}
            >
              <option value="graph">Graph-Guided (FalkorDB Live)</option>
              <option value="fused">Fused RRF (Lexical + Graph)</option>
              <option value="lexical">Lexical Baseline (BM25)</option>
              <option value="memory">Incident Memory (Part B)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="budget-input">
              Context Budget (Tokens)
            </label>
            <select
              id="budget-input"
              className="form-select mono"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              disabled={isLoading}
            >
              <option value={2000}>2,000 tokens</option>
              <option value={4000}>4,000 tokens (Standard)</option>
              <option value={8000}>8,000 tokens (Expanded)</option>
            </select>
          </div>
        </div>

        {/* Execution Mode Row */}
        <div className="form-row" style={{ marginTop: 4 }}>
          <div className="form-group">
            <label className="form-label" htmlFor="mode-select">
              Verification Mode
            </label>
            <select
              id="mode-select"
              className="form-select"
              value={mockMode ? 'mock' : 'live'}
              onChange={(e) => setMockMode(e.target.value === 'mock')}
              disabled={isLoading}
            >
              <option value="mock">Deterministic Sandbox (Reproducible Demo)</option>
              <option value="live">Live Git Worktree Sandbox (Test Runner)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="repair-toggle">
              Repair & Verification
            </label>
            <select
              id="repair-toggle"
              className="form-select"
              value={executeRepair ? 'yes' : 'no'}
              onChange={(e) => setExecuteRepair(e.target.value === 'yes')}
              disabled={isLoading}
            >
              <option value="yes">Run Repair State Machine</option>
              <option value="no">Retrieval & Context Only</option>
            </select>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <button
            type="submit"
            className="btn btn-primary"
            style={{ flex: 1 }}
            disabled={isLoading || !customReport.trim()}
          >
            <Play size={14} />
            {isLoading ? 'Running Investigation...' : 'Investigate Bug'}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onReset}
            disabled={isLoading}
            title="Reset form"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </form>
    </div>
  )
}
