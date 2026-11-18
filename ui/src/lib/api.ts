export type ToolEvent = {
  type: 'tool'
  tool: string
  args: Record<string, unknown>
  ok: boolean
  error_code: string | null
  ms: number
}

export type ModelEvent = {
  type: 'model'
  model: string | null
  tokens_in: number
  tokens_out: number
  cost_usd: number
  ms: number
}

export type SeizurePreview = {
  tool: 'apply_seizure'
  args: { notice_id: string; contract_id: string; expected_version: number }
  contract: ContractPreview
  source: {
    notice_id: string
    court_id: string
    judge_role: string
    procedure_type: string
    case_reference: string
  }
  match: { outcome: string; evidence: string[] }
  effect: { restrictions: string[]; rule: string }
}

export type OperationPreview = {
  tool: 'execute_operation'
  args: { request_id: string; contract_id: string; expected_version: number }
  contract: ContractPreview
  source: {
    request_id: string
    type: string
    origin: string
    amount_eur: number | null
    target_allocation: Record<string, number> | null
  }
  effect: { type: string; amount_eur?: number; target_allocation?: Record<string, number> }
  active_restrictions: string[]
}

type ContractPreview = {
  contract_id: string
  policy_number: string
  status: string
  version: number
}

export type ApprovalPreview = SeizurePreview | OperationPreview

export type FinishedEvent = {
  type: 'finished'
  stop_reason: string
  steps: number
  model_calls: number
  tokens_in: number
  tokens_out: number
  cost_usd: number
  latency_s: number
  answer: string | null
}

export type RunEvent =
  | ModelEvent
  | ToolEvent
  | { type: 'approval_needed'; preview: ApprovalPreview }
  | { type: 'approval_decided'; approve: boolean; reason: string }
  | FinishedEvent

export type Ledger = {
  restricted_contracts: string[]
  operations: { blocked: number; permitted: number; pending: number }
  rows: Array<{
    contract_id: string
    restriction: string
    notice_id: string
    rule_id: string
    rule_version: string
    applied_at: string
  }>
}

export type SeedSnapshot = {
  contracts: Record<string, {
    status: string
    value_eur: number
    advance_eur: number
    allocation: Record<string, number>
    restrictions: Record<string, string>
  }>
  requests: Record<string, string>
}

export type RateMetrics = {
  scenarios: number
  runs: number
  passed: number
  pass_rate: number
  ci_low: number
  ci_high: number
  pass_hat_k: number
  pass_at_k: number
}

export type KindMetrics = RateMetrics & { kind: string }
export type Percentiles = { p50: number | null; p95: number | null }
export type DomainMetrics = {
  runs: number
  runs_without_state: number
  under_blocking: number
  over_blocking: number
  wrong_contract_changes: number
  lineage_completeness: number | null
  previews_on_expected_contract: number | null
}
export type SetExtra = {
  name: string
  model: string | null
  cost_per_success: number | null
  latency_s: Percentiles
  total_cost_usd: number
  domain: DomainMetrics | null
}
export type Summary = SetExtra & {
  runs: number
  scenarios: number
  overall: RateMetrics
  by_kind: KindMetrics[]
  cost_usd: Percentiles
  scenario_rows: Array<{
    id: string
    kind: string
    passed: number
    runs: number
    stop_reasons: Array<string | null>
  }>
  failed: Array<{
    id: string
    repeat: number
    kind: string
    stop_reason: string | null
    reason: string | null
  }>
}
export type Comparison = {
  shared: number
  only_a: number
  only_b: number
  both: number
  neither: number
  sign_test_p: number
  a: { overall: RateMetrics; by_kind: KindMetrics[] }
  b: { overall: RateMetrics; by_kind: KindMetrics[] }
  a_extra: SetExtra
  b_extra: SetExtra
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Could not reach the API.')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body
      ? String(body.detail)
      : `Request failed (${response.status})`
    throw new ApiError(response.status, detail)
  }
  return body as T
}

export const getSeeds = () => request<string[]>('/api/seeds')
export const resetSeed = (seed: string) => request<SeedSnapshot>('/api/reset', {
  method: 'POST', body: JSON.stringify({ seed }),
})
export const startRun = (body: { task: string; operator_id?: string; max_steps?: number }) =>
  request<{ run_id: string }>('/api/runs', { method: 'POST', body: JSON.stringify(body) })
export const decide = (runId: string, body: { approve: boolean; reason?: string }) =>
  request<{ ok: boolean }>(`/api/runs/${encodeURIComponent(runId)}/decision`, {
    method: 'POST', body: JSON.stringify(body),
  })
export const getLedger = () => request<Ledger>('/api/ledger')
export const getResults = (name?: string) => request<Record<string, unknown>[]>(
  `/api/results${name ? `?name=${encodeURIComponent(name)}` : ''}`,
)
export const getSummary = (name: string) => request<Summary>(
  `/api/summary?name=${encodeURIComponent(name)}`,
)
export const getComparison = (a: string, b: string) => request<Comparison>(
  `/api/comparison?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`,
)

export function openRunEvents(
  runId: string,
  onEvent: (event: RunEvent) => void,
  onError: (message: string) => void,
): () => void {
  const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`)
  source.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data) as RunEvent
      onEvent(event)
      if (event.type === 'finished') source.close()
    } catch {
      source.close()
      onError('The run stream returned an unreadable event.')
    }
  }
  source.onerror = () => {
    source.close()
    onError('The run stream disconnected. The run may still be active on the server.')
  }
  return () => source.close()
}
