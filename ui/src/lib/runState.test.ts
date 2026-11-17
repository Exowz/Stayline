import { describe, expect, it } from 'vitest'
import type { RunEvent, ToolEvent } from './api'
import { deriveSteps, initialRun, reduceRun } from './runState'

const tool = (name: string): ToolEvent => ({
  type: 'tool', tool: name, args: {}, ok: true, error_code: null, ms: 84,
})

describe('run state', () => {
  it('accumulates tool events in arrival order', () => {
    const first = reduceRun(initialRun, tool('get_notice'))
    const second = reduceRun(first, tool('find_contracts'))
    expect(second.tools.map((event) => event.tool)).toEqual(['get_notice', 'find_contracts'])
  })

  it('waits with the trusted preview', () => {
    const preview = {
      tool: 'apply_seizure' as const,
      args: { notice_id: 'N-1', contract_id: 'C-1', expected_version: 3 },
      contract: { contract_id: 'C-1', policy_number: 'AV-1', version: 3, status: 'active' },
      source: { notice_id: 'N-1', court_id: 'TJ Paris', judge_role: 'judge', procedure_type: 'investigation', case_reference: '2026/1' },
      match: { outcome: 'match', evidence: ['policy_number'] },
      effect: { restrictions: ['rachat'], rule: 'CPP-706-155@2026' },
    }
    const waiting = reduceRun(initialRun, { type: 'approval_needed', preview })
    expect(waiting.status).toBe('waiting')
    expect(waiting.preview).toEqual(preview)
    expect(reduceRun(waiting, { type: 'approval_decided', approve: true, reason: '' }).status).toBe('running')
  })

  it('marks a completed run done with its totals', () => {
    const finished: RunEvent = {
      type: 'finished', stop_reason: 'done', steps: 4, model_calls: 2,
      tokens_in: 120, tokens_out: 30, cost_usd: 0.004, latency_s: 2.5,
      answer: 'Applied.',
    }
    const state = reduceRun(initialRun, finished)
    expect(state.status).toBe('done')
    expect(state.finished).toEqual(finished)
    expect(state.elapsed).toBe(2.5)
  })

  it('marks a step budget stop as failed', () => {
    const state = reduceRun(initialRun, {
      type: 'finished', stop_reason: 'max_steps', steps: 14, model_calls: 3,
      tokens_in: 10, tokens_out: 5, cost_usd: 0.01, latency_s: 8, answer: null,
    })
    expect(state.status).toBe('failed')
  })

  it('keeps unknown tools visible as steps', () => {
    expect(deriveSteps([tool('new_backend_tool')]).some((step) =>
      step.label === 'new_backend_tool' && step.tools[0].tool === 'new_backend_tool',
    )).toBe(true)
  })

  it('does not mutate the prior state', () => {
    const first = reduceRun(initialRun, tool('get_notice'))
    const prior = structuredClone(first)
    reduceRun(first, tool('get_rule'))
    expect(first).toEqual(prior)
    expect(initialRun.tools).toEqual([])
  })
})
