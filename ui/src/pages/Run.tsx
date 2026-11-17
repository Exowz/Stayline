import { useEffect, useState } from 'react'
import { CircleAlert, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import ApprovalCard from '@/components/ApprovalCard'
import PlanList from '@/components/PlanList'
import { getSeeds, resetSeed } from '@/lib/api'
import type { RunView } from '@/lib/runState'

type Props = {
  run: RunView
  runId: string | null
  streamError: string
  beginRun: (body: { task: string; operator_id?: string; max_steps?: number }) => Promise<void>
  viewLedger: () => void
}

export default function Run({ run, runId, streamError, beginRun, viewLedger }: Props) {
  const [task, setTask] = useState('')
  const [operator, setOperator] = useState('op-default')
  const [seeds, setSeeds] = useState<string[]>([])
  const [seed, setSeed] = useState('base.json')
  const [resetMessage, setResetMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const active = run.status === 'running' || run.status === 'waiting'

  useEffect(() => {
    let live = true
    getSeeds().then((names) => {
      if (!live) return
      setSeeds(names)
      setSeed(names.includes('base.json') ? 'base.json' : names[0] ?? '')
    }).catch((cause: unknown) => {
      if (live) setError(cause instanceof Error ? cause.message : 'Could not load seeds.')
    })
    return () => { live = false }
  }, [])

  async function reset() {
    setBusy(true)
    setError('')
    setResetMessage('')
    try {
      const snapshot = await resetSeed(seed)
      setResetMessage(`Reset ${seed}: ${Object.keys(snapshot.contracts).length} contracts and ${Object.keys(snapshot.requests).length} requests ready.`)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Reset failed.') }
    finally { setBusy(false) }
  }

  async function start(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try { await beginRun({ task: task.trim(), operator_id: operator.trim() || 'op-default' }) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start the run.') }
    finally { setBusy(false) }
  }

  return <div className="run-grid">
    <section className="island panel setup-panel" aria-label="Run setup">
      <div className="panel-heading"><h2>New run</h2><span>Local demo</span></div>
      <p className="panel-intro">Give the agent a notice or adviser request. It will pause before a guarded write.</p>
      <form onSubmit={start} className="setup-form">
        <label htmlFor="task">Task</label>
        <textarea id="task" value={task} onChange={(event) => setTask(event.target.value)}
          placeholder="Apply seizure notice N-2026-0417 to the matching contract."
          rows={5} required disabled={active} />
        <label htmlFor="seed">Seed</label>
        <div className="seed-row"><select id="seed" value={seed} onChange={(event) => setSeed(event.target.value)} disabled={active || busy || !seeds.length}>
          {seeds.map((name) => <option key={name} value={name}>{name}</option>)}
        </select><Button type="button" variant="outline" onClick={reset} disabled={active || busy || !seed}><RotateCcw size={15} />Reset</Button></div>
        {resetMessage && <p className="reset-message" role="status">{resetMessage}</p>}
        <label htmlFor="operator">Operator</label>
        <Input id="operator" value={operator} onChange={(event) => setOperator(event.target.value)} disabled={active} />
        {(error || streamError) && <p className="inline-error" role="alert"><CircleAlert size={15} />{error || streamError}</p>}
        <div className="form-spacer" />
        <Button type="submit" variant={active ? 'outline' : 'default'} className="start-button" disabled={active || busy || !task.trim()}>Start run</Button>
      </form>
    </section>
    <PlanList run={run} />
    <ApprovalCard run={run} runId={runId} viewLedger={viewLedger} />
  </div>
}
