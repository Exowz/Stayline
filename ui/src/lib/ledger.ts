import type { Ledger } from './api'

export type LedgerRow = Ledger['rows'][number]

export type ContractGroup = {
  contract_id: string
  notices: string[]
  restrictions: string[]
}

const applied = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC',
})

export function ruleLabel(row: Pick<LedgerRow, 'rule_id' | 'rule_version'>): string {
  return `${row.rule_id} v${row.rule_version}`
}

export function appliedLabel(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return `${applied.format(date)} UTC`
}

export function groupByContract(rows: LedgerRow[]): ContractGroup[] {
  const groups = new Map<string, ContractGroup>()
  for (const row of rows) {
    const group = groups.get(row.contract_id)
      ?? { contract_id: row.contract_id, notices: [], restrictions: [] }
    if (!group.notices.includes(row.notice_id)) group.notices.push(row.notice_id)
    group.restrictions.push(row.restriction)
    groups.set(row.contract_id, group)
  }
  return [...groups.values()]
}
