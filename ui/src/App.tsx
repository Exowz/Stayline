import { useEffect, useRef, useState } from 'react'
import { Activity, BookOpen, ChartNoAxesCombined, Play, Sparkles } from 'lucide-react'
import { openRunEvents, startRun } from '@/lib/api'
import type { RunEvent } from '@/lib/api'
import { initialRun, reduceRun } from '@/lib/runState'
import type { RunView } from '@/lib/runState'
import Run from '@/pages/Run'
import Ledger from '@/pages/Ledger'
import Evaluation from '@/pages/Evaluation'
import Models from '@/pages/Models'

type Screen = 'Run' | 'Ledger' | 'Evaluation' | 'Models'
const screens: Array<{ name: Screen; icon: typeof Play }> = [
  { name: 'Run', icon: Play },
  { name: 'Ledger', icon: BookOpen },
  { name: 'Evaluation', icon: ChartNoAxesCombined },
  { name: 'Models', icon: Sparkles },
]
const descriptions: Record<Screen, string> = {
  Run: 'Watch the agent check the facts, then decide before a guarded write.',
  Ledger: 'Restriction lineage and operation outcomes.',
  Evaluation: 'Scenario results by kind.',
  Models: 'Compare the two model runs.',
}

function Dock({ run }: { run: RunView }) {
  const lastModel = run.models.at(-1)?.model ?? 'Not started'
  const tokensIn = run.finished?.tokens_in ?? run.models.reduce((sum, item) => sum + item.tokens_in, 0)
  const tokensOut = run.finished?.tokens_out ?? run.models.reduce((sum, item) => sum + item.tokens_out, 0)
  const cost = run.finished?.cost_usd ?? run.models.reduce((sum, item) => sum + item.cost_usd, 0)
  return <div className="island-dark dock" aria-label="Run metrics">
    <div><span>Steps</span><strong>{run.finished?.steps ?? run.tools.length} of 14</strong></div>
    <div><span>Tokens</span><strong>{tokensIn.toLocaleString()} in · {tokensOut.toLocaleString()} out</strong></div>
    <div><span>Cost</span><strong>${cost.toFixed(4)}</strong></div>
    <div><span>Elapsed</span><strong>{run.elapsed === null ? '0.0 s' : `${run.elapsed.toFixed(1)} s`}</strong></div>
    <div><span>Model</span><strong>{lastModel}</strong></div>
  </div>
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('Run')
  const [run, setRun] = useState<RunView>(initialRun)
  const [runId, setRunId] = useState<string | null>(null)
  const [streamError, setStreamError] = useState('')
  const [clock, setClock] = useState(0)
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const closeEvents = useRef<(() => void) | null>(null)
  useEffect(() => () => closeEvents.current?.(), [])
  useEffect(() => {
    if (run.status !== 'running' && run.status !== 'waiting') return
    const timer = window.setInterval(() => setClock(Date.now()), 250)
    return () => window.clearInterval(timer)
  }, [run.status])

  async function beginRun(body: { task: string; operator_id?: string; max_steps?: number }) {
    const started = await startRun(body)
    closeEvents.current?.()
    const now = Date.now()
    setStartedAt(now)
    setClock(now)
    setRun({ ...initialRun, status: 'running' })
    setRunId(started.run_id)
    setStreamError('')
    closeEvents.current = openRunEvents(started.run_id, (event: RunEvent) => {
      setRun((current) => reduceRun(current, event))
    }, setStreamError)
  }

  const statusText = run.status === 'waiting' ? 'Waiting for your approval'
    : run.status === 'done' ? 'Done'
      : run.status === 'failed' ? 'Run failed'
        : run.status === 'running' ? 'Agent running' : 'Ready to run'

  return <div className="app-shell">
    <aside className="island-dark sidebar">
      <div className="brand"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>Stayline</div>
      <nav className="nav" aria-label="Screens">
        {screens.map(({ name, icon: Icon }) => <button key={name} type="button"
          className={screen === name ? 'nav-item selected' : 'nav-item'}
          aria-current={screen === name ? 'page' : undefined} onClick={() => setScreen(name)}>
          <Icon size={18} strokeWidth={1.8} />{name}
          {name === 'Run' && run.status === 'failed' && <span className="failure-dot" aria-label="Run failed">!</span>}
        </button>)}
      </nav>
      <div className="sidebar-note"><Activity size={16} /> Guarded writes need your approval.</div>
    </aside>
    <main className="main-area">
      <header className="island title-island">
        <div><h1>{screen}</h1><p>{descriptions[screen]}</p></div>
        {screen === 'Run' && <span className={`status-pill ${run.status}`}><span className="status-dot" />{statusText}</span>}
      </header>
      {screen === 'Run' && <Run run={run} runId={runId} beginRun={beginRun}
        streamError={streamError} viewLedger={() => setScreen('Ledger')} />}
      {screen === 'Ledger' && <Ledger />}
      {screen === 'Evaluation' && <Evaluation />}
      {screen === 'Models' && <Models />}
    </main>
    {screen === 'Run' && <Dock run={{ ...run, elapsed: run.elapsed ?? (startedAt === null ? null : Math.max(0, (clock - startedAt) / 1000)) }} />}
  </div>
}
