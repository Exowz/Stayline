import { useEffect, useState } from 'react'
import { CircleAlert, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getLedger } from '@/lib/api'
import type { Ledger as LedgerData } from '@/lib/api'
import { appliedLabel, groupByContract, ruleLabel } from '@/lib/ledger'
import './ledger.css'

type CounterProps = {
  label: string
  value: number
  note: string
  tone?: 'blocked'
}

function Counter({ label, value, note, tone }: CounterProps) {
  return <section className={`island counter ${tone ?? ''}`} aria-label={label}>
    <span className="counter-label">{label}</span>
    <strong className="counter-value">{value}</strong>
    <span className="counter-note">{note}</span>
  </section>
}

export default function Ledger() {
  const [ledger, setLedger] = useState<LedgerData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let live = true
    getLedger().then((data) => { if (live) setLedger(data) })
      .catch((cause: unknown) => {
        if (live) setError(cause instanceof Error ? cause.message : 'Could not load the ledger.')
      })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [])

  async function refresh() {
    setLoading(true)
    setError('')
    try { setLedger(await getLedger()) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load the ledger.') }
    finally { setLoading(false) }
  }

  const operations = ledger?.operations
  const rows = ledger?.rows ?? []
  const contracts = ledger?.restricted_contracts ?? []
  const groups = groupByContract(rows)

  return <div className="ledger-grid">
    <div className="ledger-counters">
      <Counter label="Blocked" value={operations?.blocked ?? 0} tone="blocked"
        note="Requests sent to manual review" />
      <Counter label="Permitted" value={operations?.permitted ?? 0}
        note="Requests executed" />
      <Counter label="Pending" value={operations?.pending ?? 0}
        note="Requests not processed yet" />
    </div>
    <section className="island ledger-panel" aria-label="Restriction lineage">
      <div className="ledger-head">
        <h2>Restriction lineage</h2>
        <Button type="button" variant="outline" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={15} />Refresh
        </Button>
      </div>
      <p className="ledger-sub">
        <strong>{rows.length}</strong> {rows.length === 1 ? 'restriction' : 'restrictions'} on{' '}
        <strong>{contracts.length}</strong> {contracts.length === 1 ? 'contract' : 'contracts'}.
        Each one names the notice and the rule version it came from.
      </p>
      {groups.length > 0 && <div className="chips ledger-groups" aria-label="Restricted contracts">
        {groups.map((group) => <span key={group.contract_id} className="chip confirmed">
          <code>{group.contract_id}</code> {group.restrictions.length} from <code>{group.notices.join(', ')}</code>
        </span>)}
      </div>}
      {error && <p className="inline-error" role="alert"><CircleAlert size={15} />{error}</p>}
      {!error && !loading && rows.length === 0 && <div className="ledger-empty">
        <strong>No restriction yet</strong>
        Approve a seizure notice on the Run screen and its five restrictions appear here.
      </div>}
      {rows.length > 0 && <Table className="ledger-table">
        <TableHeader>
          <TableRow>
            <TableHead>Contract</TableHead>
            <TableHead>Restriction</TableHead>
            <TableHead>Notice</TableHead>
            <TableHead>Rule version</TableHead>
            <TableHead>Applied</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => <TableRow key={`${row.contract_id}-${row.restriction}-${row.notice_id}`}>
            <TableCell><code>{row.contract_id}</code></TableCell>
            <TableCell><span className="chip">{row.restriction}</span></TableCell>
            <TableCell><code>{row.notice_id}</code></TableCell>
            <TableCell><code>{ruleLabel(row)}</code></TableCell>
            <TableCell className="num">{appliedLabel(row.applied_at)}</TableCell>
          </TableRow>)}
        </TableBody>
      </Table>}
    </section>
  </div>
}
