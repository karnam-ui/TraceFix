import React, { useEffect, useState } from 'react'
import { api } from './api/client'
import { AppHeader } from './components/AppHeader'
import { BugInvestigationForm } from './components/BugInvestigationForm'
import { ContextBudgetPanel } from './components/ContextBudgetPanel'
import { EvaluationBenchmarksView } from './components/EvaluationBenchmarksView'
import { EvidenceExplorer } from './components/EvidenceExplorer'
import { GraphExplorerView } from './components/GraphExplorerView'
import { IncidentMemoryView } from './components/IncidentMemoryView'
import { InvestigationTimeline } from './components/InvestigationTimeline'
import { PatchVerificationPanel } from './components/PatchVerificationPanel'
import type {
  CaseSummary,
  HealthResponse,
  InvestigateRequest,
  InvestigateResponse,
} from './types'

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [cases, setCases] = useState<CaseSummary[]>([])
  const [activeTab, setActiveTab] = useState<'workspace' | 'graph' | 'memory' | 'eval'>('workspace')
  const [currentCaseId, setCurrentCaseId] = useState<string>('psf__requests-1142')
  const [investigateResult, setInvestigateResult] = useState<InvestigateResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [investigateError, setInvestigateError] = useState<string | null>(null)

  // Probe health on mount and every 15 seconds
  const fetchHealth = async () => {
    try {
      const h = await api.getHealth()
      setHealth(h)
      setHealthError(null)
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : 'Backend unreachable')
      setHealth(null)
    }
  }

  // Load available benchmark cases on mount
  const fetchCases = async () => {
    try {
      const cList = await api.getCases()
      setCases(cList)
    } catch (err) {
      console.warn('Failed to fetch cases:', err)
    }
  }

  useEffect(() => {
    fetchHealth()
    fetchCases()
    const timer = setInterval(fetchHealth, 15000)
    return () => clearInterval(timer)
  }, [])

  const handleInvestigate = async (req: InvestigateRequest) => {
    setIsLoading(true)
    setInvestigateError(null)
    if (req.case_id) {
      setCurrentCaseId(req.case_id)
    }

    try {
      const res = await api.investigate(req)
      setInvestigateResult(res)
    } catch (err) {
      setInvestigateError(err instanceof Error ? err.message : 'Investigation failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setInvestigateResult(null)
    setInvestigateError(null)
  }

  return (
    <div className="app-container">
      <AppHeader
        health={health}
        healthError={healthError}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        currentRevision={investigateResult?.revision}
      />

      <main className="workspace-main">
        {activeTab === 'workspace' && (
          <div className="workspace-grid">
            {/* Left column: Configuration & Execution Progress */}
            <div>
              <BugInvestigationForm
                cases={cases}
                isLoading={isLoading}
                onSubmit={handleInvestigate}
                onReset={handleReset}
                currentCaseId={currentCaseId}
              />

              <InvestigationTimeline
                stages={investigateResult?.stages || []}
                isLoading={isLoading}
              />
            </div>

            {/* Right column: Evidence, Context Budget, Repair & Verification */}
            <div>
              {investigateError && (
                <div
                  style={{
                    padding: 12,
                    backgroundColor: 'var(--status-danger-bg)',
                    border: '1px solid rgba(248, 81, 73, 0.4)',
                    color: 'var(--status-danger-text)',
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: 16,
                    fontSize: 12,
                  }}
                >
                  <strong>Execution Error:</strong> {investigateError}
                </div>
              )}

              {investigateResult ? (
                <>
                  <EvidenceExplorer
                    items={investigateResult.retrieval}
                    strategyUsed={investigateResult.strategy_used}
                  />

                  <ContextBudgetPanel
                    budget={investigateResult.context_budget}
                    items={investigateResult.context_items}
                  />

                  <PatchVerificationPanel
                    proposedPatch={investigateResult.proposed_patch}
                    patchSafety={investigateResult.patch_safety}
                    verification={investigateResult.verification}
                  />
                </>
              ) : (
                <div className="panel-card">
                  <div className="panel-header">
                    <span className="panel-title">TraceFix Investigation Workspace</span>
                  </div>
                  <div className="panel-body" style={{ color: 'var(--text-secondary)' }}>
                    <p style={{ marginBottom: 12, fontSize: 13 }}>
                      Welcome to TraceFix. This workspace connects live to the graph-native bug resolution engine.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                      <div>
                        1. <strong>Select a target bug:</strong> Choose from the 5 frozen pilot cases or enter a custom bug report.
                      </div>
                      <div>
                        2. <strong>Select retrieval strategy:</strong> Compare Graph-Guided (FalkorDB), Fused RRF, or Lexical baseline.
                      </div>
                      <div>
                        3. <strong>Run investigation:</strong> Observe codebase localization, context budgeting, AST safety validation, sandbox verification, and Part B incident memory storage.
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'graph' && <GraphExplorerView />}
        {activeTab === 'memory' && <IncidentMemoryView />}
        {activeTab === 'eval' && <EvaluationBenchmarksView />}
      </main>
    </div>
  )
}
