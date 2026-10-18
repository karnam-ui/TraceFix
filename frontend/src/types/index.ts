// TraceFix API TypeScript definitions

export interface HealthResponse {
  status: string
  version: string
  falkordb_connected: boolean
  redis_endpoint: string
  active_cases_count: number
  persisted_graphs_count: number
  incident_memory_count: number
}

export interface CaseSummary {
  case_id: string
  repo: string
  revision: string
  short_sha: string
  localizable: boolean
  bug_report_preview: string
  ground_truth_files: string[]
  ground_truth_functions: string[]
  created_at?: string
  pre_cutoff?: boolean
}

export interface GraphSummary {
  case_id?: string
  revision: string
  short_sha: string
  graph_name: string
  node_count: number
  edge_count: number
  sha256: string
  is_live: boolean
}

export interface NodeDetail {
  entity_id: string
  kind: string
  repo: string
  revision: string
  path: string
  qualified_name: string
  start_line: number
  end_line: number
}

export interface EdgeDetail {
  source_id: string
  target_id: string
  edge_type: string
  provenance: string
  source: string
  confidence?: string
}

export interface NeighborhoodResponse {
  graph_name: string
  revision: string
  center_id?: string
  nodes: NodeDetail[]
  edges: EdgeDetail[]
}

export interface RetrievalItem {
  evidence_id: string
  strategy: string
  rank: number
  score: number
  file: string
  symbol: string
  lines?: [number, number]
  provenance: string
  source_revision: string
  is_ground_truth_function: boolean
  is_ground_truth_file: boolean
}

export interface ContextItem {
  candidate_id: string
  file_path: string
  symbol: string
  token_cost: number
  strategy: string
  rank: number
  score: number
  included: boolean
  exclusion_reason?: string
}

export interface VerificationSummary {
  status: 'VERIFIED' | 'FAILED' | 'REJECTED' | 'TIMEOUT' | string
  exit_code: number
  passed_tests: string[]
  failed_tests: string[]
  duration_seconds: number
}

export interface MemoryMatch {
  incident_id: string
  case_id: string
  revision: string
  similarity_score: number
  patch_preview: string
  status: string
  executed_at: string
}

export interface LifecycleStage {
  stage_id: string
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  detail: string
  elapsed_ms: number
}

export interface InvestigateRequest {
  case_id?: string
  repo?: string
  revision?: string
  bug_report?: string
  strategy: 'graph' | 'fused' | 'lexical' | 'memory' | string
  budget?: number
  mock?: boolean
  execute_repair?: boolean
}

export interface InvestigateResponse {
  case_id: string
  repo: string
  revision: string
  strategy_used: string
  stages: LifecycleStage[]
  retrieval: RetrievalItem[]
  context_budget: {
    budget_limit: number
    tokens_used: number
    utilization: number
    included_count: number
    excluded_count: number
  }
  context_items: ContextItem[]
  proposed_patch?: string
  patch_safety: {
    is_valid?: boolean
    errors?: string[]
    prohibited_files?: string[]
    warnings?: string[]
  }
  verification?: VerificationSummary
  memory_matches: MemoryMatch[]
  memory_stored: boolean
  ground_truth_functions: string[]
  ground_truth_files: string[]
  overall_status: string
  error?: string
}

export interface IncidentMemoryItem {
  incident_id: string
  case_id: string
  revision: string
  repo: string
  bug_report_snippet: string
  patch_diff: string
  verification_status: string
  created_at: string
}

export interface EvaluationReportSummary {
  file_name: string
  title: string
  dataset_fingerprint?: string
  cases_count: number
}
