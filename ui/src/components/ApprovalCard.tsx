import { Check, CircleAlert } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { decide } from '@/lib/api'
import type { ApprovalPreview } from '@/lib/api'
import type { RunView } from '@/lib/runState'

const names: Record<string, string> = { acceptation_benefice: 'Acceptation du bénéfice' }
const readable = (value: string) => names[value] ?? value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function ApprovalDetails({ preview }: { preview: ApprovalPreview }) {
  const isSeizure = preview.tool === 'apply_seizure'
  return <>
    <div className="approval-head">
      <span className="kicker">Approval needed</span>
      <h2>{isSeizure ? 'Apply this seizure?' : 'Execute this request?'}</h2>
      <p>Nothing has been written yet. Check the backend facts before you decide.</p>
    </div>
    <div className="approval-section">
      <h3>Contract</h3>
      <div className="contract-line">
        <span className="contract-avatar">{preview.contract.contract_id.slice(-2)}</span>
        <div><strong>Contract <code>{preview.contract.contract_id}</code></strong>
          <span>Policy <code>{preview.contract.policy_number}</code> · {preview.contract.status}</span></div>
        <span className="version">Version {preview.contract.version}</span>
      </div>
    </div>
    <div className="approval-section">
      <h3>Why this contract</h3>
      <div className="chips">{isSeizure
        ? preview.match.evidence.map((item) => <span className="chip confirmed" key={item}><Check size={12} />{readable(item)}</span>)
        : <span className="chip confirmed"><Check size={12} />Linked to request {preview.source.request_id}</span>}
      </div>
      {isSeizure && <p className="section-note">Match outcome: {readable(preview.match.outcome)}</p>}
    </div>
    <div className="approval-section">
      <h3>What will change</h3>
      {isSeizure ? <div className="change-grid">
        <span>Blocked</span><div className="chips">{preview.effect.restrictions.map((item) =>
          <span className="chip change-chip" key={item}>{readable(item)}</span>)}</div>
        {!preview.effect.restrictions.includes('arbitrage') && <><span>Still allowed</span><div className="chips"><span className="chip confirmed"><Check size={12} />Arbitrage</span></div></>}
        <span>Untouched</span><div>Other contracts are outside this write.</div>
      </div> : <div className="change-grid">
        <span>Operation</span><div className="chips"><span className="chip change-chip">{readable(preview.effect.type)}</span>
          {'amount_eur' in preview.effect && preview.effect.amount_eur !== undefined &&
            <span className="chip change-chip">€{preview.effect.amount_eur.toLocaleString()}</span>}</div>
        {preview.effect.target_allocation && <><span>Allocation</span><div>{JSON.stringify(preview.effect.target_allocation)}</div></>}
        <span>Active restrictions</span><div className="chips">{preview.active_restrictions.length
          ? preview.active_restrictions.map((item) => <span className="chip" key={item}>{readable(item)}</span>)
          : <span>None</span>}</div>
      </div>}
      <p className="source-line">{isSeizure
        ? <>Source: notice <code>{preview.source.notice_id}</code>, {preview.source.court_id}, case <code>{preview.source.case_reference}</code>, rule <code>{preview.effect.rule}</code></>
        : <>Source: request <code>{preview.source.request_id}</code>, {preview.source.origin}</>}</p>
    </div>
  </>
}

export default function ApprovalCard({ run, runId, viewLedger }: {
  run: RunView
  runId: string | null
  viewLedger: () => void
}) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  async function submit(approve: boolean) {
    if (!runId) return
    setSubmitting(true)
    setError('')
    try { await decide(runId, { approve }) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Decision failed.') }
    finally { setSubmitting(false) }
  }
  return <section className="island panel approval-panel" aria-label="Approval and result">
    {run.status === 'waiting' && run.preview ? <>
      <ApprovalDetails preview={run.preview} />
      {error && <p className="inline-error"><CircleAlert size={14} />{error}</p>}
      <div className="approval-actions"><small>The agent waits for your decision.</small>
        <Button type="button" variant="outline" disabled={submitting} onClick={() => submit(false)}>Reject</Button>
        <Button type="button" disabled={submitting} onClick={() => submit(true)}>Approve</Button>
      </div>
    </> : <>
      <div className="approval-head"><span className="kicker">Run result</span>
        <h2>{run.status === 'idle' ? 'Ready when you are' : run.status === 'running' ? 'Agent working' : run.status === 'failed' ? 'Run stopped with a failure' : 'Run complete'}</h2>
        <p>{run.status === 'idle' ? 'Start a run to see its result and any approval request here.' : run.status === 'running' ? 'The agent is reading backend state and preparing its next action.' : 'The final stop reason and answer are shown below.'}</p>
      </div>
      <div className="approval-section"><h3>Stop reason</h3><p className={run.status === 'failed' ? 'stop-reason failed' : 'stop-reason'}>
        {run.status === 'failed' && <CircleAlert size={15} />}{run.finished ? readable(run.finished.stop_reason) : 'Pending'}</p></div>
      <div className="approval-section"><h3>Final answer</h3><p className="answer-text">{run.finished?.answer ?? 'No final answer yet.'}</p></div>
      <div className="approval-actions"><small>Read the restriction ledger after a run.</small>
        <Button type="button" variant="outline" onClick={viewLedger}>View ledger</Button></div>
    </>}
  </section>
}
