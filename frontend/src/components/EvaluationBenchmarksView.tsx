import React, { useEffect, useState } from 'react'
import { Award, BarChart3, FileText, Info } from 'lucide-react'
import { api } from '../api/client'
import type { EvaluationReportSummary } from '../types'

export const EvaluationBenchmarksView: React.FC = () => {
  const [reports, setReports] = useState<EvaluationReportSummary[]>([])
  const [selectedReportName, setSelectedReportName] = useState<string>('retrieval_pilot_report.json')
  const [reportData, setReportData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    api.getEvaluations().then((rList) => {
      setReports(rList)
      if (rList.length > 0) {
        setSelectedReportName((prev) => prev || rList[0].file_name)
      }
    })
  }, [])

  useEffect(() => {
    if (selectedReportName) {
      setIsLoading(true)
      api
        .getEvaluationReport(selectedReportName)
        .then((data) => setReportData(data))
        .finally(() => setIsLoading(false))
    }
  }, [selectedReportName])

  const aggregates = reportData?.aggregates || {}

  return (
    <div>
      {/* Header */}
      <div className="panel-card">
        <div className="panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Award size={15} color="#e3b341" />
            <span className="panel-title">Reproducible Evaluation & Research Benchmarks</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <label className="form-label" style={{ margin: 0, fontSize: 10 }} htmlFor="eval-select">
              Select Report:
            </label>
            <select
              id="eval-select"
              className="form-select mono"
              style={{ width: 'auto', padding: '3px 8px', fontSize: 11 }}
              value={selectedReportName}
              onChange={(e) => setSelectedReportName(e.target.value)}
              disabled={isLoading}
            >
              {reports.map((r) => (
                <option key={r.file_name} value={r.file_name}>
                  {r.title} ({r.file_name})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="panel-body">
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--status-warning-bg)',
              border: '1px solid rgba(210, 153, 34, 0.4)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 11,
              color: 'var(--status-warning-text)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Info size={14} style={{ flexShrink: 0 }} />
            <span>
              <strong>Research Integrity Notice:</strong> All metrics shown are reproduced directly from stored experiment records.
              Ground truth remains provisional (Q-B7) and the 5-case pilot is outcome-independent and exploratory ($N=5$).
              Do not infer general statistical superiority.
            </span>
          </div>
        </div>
      </div>

      {/* Aggregate Metrics Table if available */}
      {aggregates && Object.keys(aggregates).length > 0 && (
        <div className="panel-card">
          <div className="panel-header">
            <span className="panel-title" style={{ fontSize: 11 }}>
              <BarChart3 size={13} /> Aggregate Comparison Across Retrieval Arms (N = 5 Cases)
            </span>
            {reportData?.dataset_fingerprint && (
              <span className="badge badge-neutral mono" style={{ fontSize: 9 }}>
                dataset: {reportData.dataset_fingerprint.slice(0, 12)}...
              </span>
            )}
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Experimental Arm</th>
                  <th style={{ width: 90 }}>Fn Hit@5</th>
                  <th style={{ width: 90 }}>Fn Hit@10</th>
                  <th style={{ width: 90 }}>Fn Hit@20</th>
                  <th style={{ width: 90 }}>File Hit@10</th>
                  <th style={{ width: 70 }}>MRR</th>
                  <th style={{ width: 90 }}>Mean Latency</th>
                  <th style={{ width: 110 }}>Token Budget</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(aggregates).map(([key, arm]: [string, any]) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 600 }}>{arm.name || key}</td>
                    <td className="mono">
                      {arm.function_hit_at_k?.['5']?.hits ?? 0}/{arm.cases_evaluated ?? 5} (
                      {((arm.function_hit_at_k?.['5']?.rate ?? 0) * 100).toFixed(1)}%)
                    </td>
                    <td className="mono" style={{ fontWeight: 600, color: '#3fb950' }}>
                      {arm.function_hit_at_k?.['10']?.hits ?? 0}/{arm.cases_evaluated ?? 5} (
                      {((arm.function_hit_at_k?.['10']?.rate ?? 0) * 100).toFixed(1)}%)
                    </td>
                    <td className="mono" style={{ fontWeight: 600 }}>
                      {arm.function_hit_at_k?.['20']?.hits ?? 0}/{arm.cases_evaluated ?? 5} (
                      {((arm.function_hit_at_k?.['20']?.rate ?? 0) * 100).toFixed(1)}%)
                    </td>
                    <td className="mono">
                      {arm.file_hit_at_k?.['10']?.hits ?? 0}/{arm.cases_evaluated ?? 5} (
                      {((arm.file_hit_at_k?.['10']?.rate ?? 0) * 100).toFixed(1)}%)
                    </td>
                    <td className="mono">{arm.mrr?.toFixed(3) ?? '—'}</td>
                    <td className="mono">{arm.latency?.mean_ms?.toFixed(2) ?? '—'} ms</td>
                    <td className="mono">
                      {arm.context_budget?.mean_tokens_used?.toFixed(0) ?? '—'} tokens (
                      {((arm.context_budget?.mean_utilization ?? 0) * 100).toFixed(1)}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Raw JSON viewer */}
      {reportData && (
        <div className="panel-card">
          <div className="panel-header">
            <span className="panel-title" style={{ fontSize: 11 }}>
              <FileText size={12} /> Stored Experiment Artifact ({selectedReportName})
            </span>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <div className="diff-container" style={{ maxHeight: 320, borderRadius: 0, border: 'none' }}>
              <pre style={{ margin: 0, padding: 12 }}>
                {JSON.stringify(reportData, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
