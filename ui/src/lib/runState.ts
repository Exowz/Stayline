import type { ApprovalPreview, FinishedEvent, ModelEvent, RunEvent, ToolEvent } from './api'

export type RunStatus = 'idle' | 'running' | 'waiting' | 'done' | 'failed'

export type RunView = {
  status: RunStatus
  tools: ToolEvent[]
  models: ModelEvent[]
  preview: ApprovalPreview | null
  finished: FinishedEvent | null
  elapsed: number | null
}

export const initialRun: RunView = {
  status: 'idle', tools: [], models: [], preview: null, finished: null, elapsed: null,
}

export function reduceRun(state: RunView, event: RunEvent): RunView {
  switch (event.type) {
    case 'tool':
      return { ...state, status: state.status === 'idle' ? 'running' : state.status, tools: [...state.tools, event] }
    case 'model':
      return { ...state, status: state.status === 'idle' ? 'running' : state.status, models: [...state.models, event] }
    case 'approval_needed':
      return { ...state, status: 'waiting', preview: event.preview }
    case 'approval_decided':
      return { ...state, status: 'running', preview: null }
    case 'finished':
      return {
        ...state,
        status: ['done', 'asked_operator', 'refused'].includes(event.stop_reason) ? 'done' : 'failed',
        preview: null,
        finished: event,
        elapsed: event.latency_s,
      }
  }
}

export type PlanStep = {
  key: string
  label: string
  explanation: string
  tools: ToolEvent[]
}

const seizurePlan = [
  ['notice', 'Read the notice', 'Who issued it, and which contract it names.'],
  ['authority', 'Check the issuing authority', 'Confirm the court and judge can issue this order.'],
  ['contract', 'Find the contract', 'Match the policy and subscriber details.'],
  ['apply', 'Apply the five restrictions', 'Re-read backend facts before asking you.'],
  ['readback', 'Read the contract back', 'Confirm the exact restrictions after writing.'],
] as const

const operationPlan = [
  ['request', 'Read the request', 'Check the adviser request and its contract.'],
  ['ledger', 'Check the ledger', 'Read the active restrictions before acting.'],
  ['operate', 'Execute or refuse the request', 'Apply the rule to this operation.'],
] as const

export function deriveSteps(toolEvents: ToolEvent[]): PlanStep[] {
  const isOperation = toolEvents.some((event) => [
    'get_operation_request', 'find_operation_requests', 'execute_operation', 'set_request_status',
  ].includes(event.tool))
  const templates = isOperation ? operationPlan : seizurePlan
  const steps: PlanStep[] = templates.map(([key, label, explanation]) => ({
    key, label, explanation, tools: [],
  }))
  let wrote = false
  for (const event of toolEvents) {
    let key: string | undefined
    if (isOperation) {
      if (['find_operation_requests', 'get_operation_request'].includes(event.tool)) {
        key = wrote ? 'operate' : 'request'
      } else if (['get_restriction_ledger', 'get_contract'].includes(event.tool)) {
        key = wrote ? 'operate' : 'ledger'
      } else if (['execute_operation', 'set_request_status'].includes(event.tool)) {
        key = 'operate'
        wrote = true
      }
    } else {
      if (['find_notices', 'get_notice'].includes(event.tool)) key = wrote ? 'apply' : 'notice'
      else if (event.tool === 'resolve_issuing_authority') key = 'authority'
      else if (event.tool === 'find_contracts') key = wrote ? 'apply' : 'contract'
      else if (['get_contract', 'get_rule'].includes(event.tool)) key = 'apply'
      else if (event.tool === 'apply_seizure') {
        key = 'apply'
        wrote = true
      } else if (event.tool === 'get_restriction_ledger') key = wrote ? 'readback' : 'apply'
    }
    let step = steps.find((item) => item.key === key)
    if (!step) {
      step = { key: `unknown:${event.tool}`, label: event.tool, explanation: 'Backend tool call.', tools: [] }
      steps.push(step)
    }
    step.tools.push(event)
  }
  return steps
}
