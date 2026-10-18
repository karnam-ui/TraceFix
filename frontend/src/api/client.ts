// TraceFix typed API client

import type {
  CaseSummary,
  EvaluationReportSummary,
  GraphSummary,
  HealthResponse,
  IncidentMemoryItem,
  InvestigateRequest,
  InvestigateResponse,
  NeighborhoodResponse,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText
    try {
      const body = await res.json()
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      // Keep statusText fallback
    }
    throw new Error(`API Error ${res.status}: ${errorDetail}`)
  }
  return res.json()
}

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${BASE_URL}/api/health`)
    return handleResponse<HealthResponse>(res)
  },

  async getCases(): Promise<CaseSummary[]> {
    const res = await fetch(`${BASE_URL}/api/cases`)
    return handleResponse<CaseSummary[]>(res)
  },

  async getGraphs(): Promise<GraphSummary[]> {
    const res = await fetch(`${BASE_URL}/api/graphs`)
    return handleResponse<GraphSummary[]>(res)
  },

  async getNeighborhood(graphName: string, entityId?: string): Promise<NeighborhoodResponse> {
    const params = new URLSearchParams()
    if (entityId) {
      params.set('entity_id', entityId)
    }
    const url = `${BASE_URL}/api/graphs/${encodeURIComponent(graphName)}/neighborhood${
      params.toString() ? `?${params.toString()}` : ''
    }`
    const res = await fetch(url)
    return handleResponse<NeighborhoodResponse>(res)
  },

  async getMemoryRecords(): Promise<IncidentMemoryItem[]> {
    const res = await fetch(`${BASE_URL}/api/memory`)
    return handleResponse<IncidentMemoryItem[]>(res)
  },

  async investigate(req: InvestigateRequest): Promise<InvestigateResponse> {
    const res = await fetch(`${BASE_URL}/api/investigate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
    })
    return handleResponse<InvestigateResponse>(res)
  },

  async getEvaluations(): Promise<EvaluationReportSummary[]> {
    const res = await fetch(`${BASE_URL}/api/evaluations`)
    return handleResponse<EvaluationReportSummary[]>(res)
  },

  async getEvaluationReport(reportName: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${BASE_URL}/api/evaluations/${encodeURIComponent(reportName)}`)
    return handleResponse<Record<string, unknown>>(res)
  },
}
