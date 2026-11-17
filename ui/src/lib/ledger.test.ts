import { describe, expect, it } from 'vitest'
import type { Ledger } from './api'
import { appliedLabel, groupByContract, ruleLabel } from './ledger'

const row = (contract: string, restriction: string, notice = 'N-2026-0417') => ({
  contract_id: contract, restriction, notice_id: notice, rule_id: 'CPP-706-155',
  rule_version: '2026', applied_at: '2026-11-12T09:00:00+00:00',
})

describe('ledger helpers', () => {
  it('names the rule and its version together', () => {
    expect(ruleLabel(row('C-0001', 'rachat'))).toBe('CPP-706-155 v2026')
  })

  it('formats the application time in UTC and keeps unreadable values as they are', () => {
    expect(appliedLabel('2026-11-12T09:00:00+00:00')).toBe('12 Nov 2026, 09:00 UTC')
    expect(appliedLabel('2026-11-12T23:30:00-05:00')).toBe('13 Nov 2026, 04:30 UTC')
    expect(appliedLabel('not a date')).toBe('not a date')
  })

  it('groups restrictions by contract in first-seen order with their notice', () => {
    const rows: Ledger['rows'] = [
      row('C-0001', 'rachat'), row('C-0001', 'avance'),
      row('C-0003', 'rachat', 'N-2026-0500'),
    ]
    expect(groupByContract(rows)).toEqual([
      { contract_id: 'C-0001', notices: ['N-2026-0417'], restrictions: ['rachat', 'avance'] },
      { contract_id: 'C-0003', notices: ['N-2026-0500'], restrictions: ['rachat'] },
    ])
  })

  it('lists a notice once even when it wrote five restrictions', () => {
    const names = ['rachat', 'renonciation', 'nantissement', 'acceptation_benefice', 'avance']
    const groups = groupByContract(names.map((name) => row('C-0001', name)))
    expect(groups).toHaveLength(1)
    expect(groups[0].notices).toEqual(['N-2026-0417'])
    expect(groups[0].restrictions).toHaveLength(5)
  })

  it('returns nothing for an empty ledger', () => {
    expect(groupByContract([])).toEqual([])
  })
})
