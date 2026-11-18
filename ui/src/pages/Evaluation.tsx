import { useEffect, useState } from 'react'
import { getSummary } from '@/lib/api'
import type { KindMetrics, Summary } from '@/lib/api'
import { interval, pct, seconds, usd } from '@/lib/format'
import './evaluation.css'

const sets = ['results.jsonl', 'mistral/results.jsonl'] as const

function KindRow({ row }: { row: KindMetrics }) {
  const span = Math.max(0, row.ci_high - row.ci_low) * 100
  return <tr>
    <td><span className="chip">{row.kind}</span></td>
    <td>{row.scenarios}</td>
    <td>{row.passed} of {row.runs}</td>
    <td>{pct(row.pass_rate)}</td>
    <td className="range-cell">
      <div className="range-track" role="img" aria-label={`Wilson interval ${interval(row.ci_low, row.ci_high)}`}>
        <span className="range-span" style={{ left: `${row.ci_low * 100}%`, width: `${span}%` }} />
        <span className="range-mark" style={{ left: `${row.pass_rate * 100}%` }} />
      </div>
      <small>{interval(row.ci_low, row.ci_high)}</small>
    </td>
    <td>{pct(row.pass_hat_k)}</td>
  </tr>
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return <section className="island eval-kpi" aria-label={label}>
    <span className="eval-label">{label}</span><strong>{value}</strong>
    {note && <small>{note}</small>}
  </section>
}

export default function Evaluation() {
  const [summaries, setSummaries] = useState<Record<string, Summary>>({})
  const [selected, setSelected] = useState<string>(sets[0])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    Promise.all(sets.map((name) => getSummary(name))).then(([first, second]) => {
      if (live) setSummaries({ [sets[0]]: first, [sets[1]]: second })
    }).catch((cause: unknown) => {
      if (live) setError(cause instanceof Error ? cause.message : 'Could not load evaluation.')
    }).finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [])

  const data = summaries[selected]
  return <div className="eval-layout">
    <section className="island eval-switch" aria-label="Result set">
      <span className="eval-label">Result set</span>
      <div className="eval-switch-buttons">{sets.map((name) => <button key={name} type="button"
        className={selected === name ? 'eval-set active' : 'eval-set'}
        aria-pressed={selected === name} onClick={() => setSelected(name)}>
        <strong>{summaries[name]?.model?.split('/').at(-1) ?? name}</strong>
        <small>{name}</small>
      </button>)}</div>
    </section>
    {loading && <section className="island eval-message" role="status">Loading evaluation...</section>}
    {error && <section className="island eval-message eval-error" role="alert">{error}</section>}
    {data && <>
      <div className="eval-kpis">
        <Metric label="Passed" value={`${data.overall.passed} of ${data.runs}`} note={pct(data.overall.pass_rate)} />
        <Metric label="pass^k" value={pct(data.overall.pass_hat_k)} note="Every repeat passed" />
        <Metric label="Cost per success" value={usd(data.cost_per_success)} />
        <Metric label="Latency p50" value={seconds(data.latency_s.p50)} />
        <Metric label="Latency p95" value={seconds(data.latency_s.p95)} />
      </div>
      <section className="island eval-panel">
        <h2>Results by kind</h2>
        <div className="eval-table-scroll"><table className="eval-table"><thead><tr>
          <th>Kind</th><th>Scenarios</th><th>Passed runs</th><th>Pass rate</th><th>Wilson interval</th><th>pass^k</th>
        </tr></thead><tbody>{data.by_kind.map((row) => <KindRow key={row.kind} row={row} />)}</tbody></table></div>
      </section>
      <div className="eval-panels">
        <section className="island eval-panel">
          <h2>Scenarios</h2>
          <div className="scenario-list">{data.scenario_rows.map((row) => <div className="scenario-row" key={row.id}>
            <code>{row.id}</code><span className="chip">{row.kind}</span>
            <span className="repeat-marks">{row.stop_reasons.map((stop, repeat) => {
              const failed = data.failed.find((item) => item.id === row.id && item.repeat === repeat)
              const label = failed ? `${row.id} repeat ${repeat}: fail. ${failed.reason ?? stop ?? 'Unknown reason'}` : `${row.id} repeat ${repeat}: passed`
              return <span key={repeat} tabIndex={0} title={label} aria-label={label}
                className={failed ? 'repeat-mark failure' : 'repeat-mark pass'}>
                {failed ? 'fail' : '✓'}
              </span>
            })}</span>
          </div>)}</div>
        </section>
        <section className="island eval-panel">
          <h2>Domain metrics</h2>
          {data.domain ? <div className="domain-list">
            {([
              ['Under-blocking', data.domain.under_blocking],
              ['Over-blocking', data.domain.over_blocking],
              ['Wrong-contract changes', data.domain.wrong_contract_changes],
            ] as const).map(([label, count]) => <div key={label}><span>{label}</span><strong className={count ? 'safety-fail' : ''}>{count ? `${count} (must be 0)` : '0'}</strong></div>)}
            <div><span>Lineage completeness</span><strong>{pct(data.domain.lineage_completeness)}</strong></div>
            <div><span>Approval previews on expected contract</span><strong>{pct(data.domain.previews_on_expected_contract)}</strong></div>
          </div> : <p>Domain metrics unavailable.</p>}
        </section>
      </div>
      <section className="island eval-panel">
        <h2>Failed runs</h2>
        {data.failed.length ? <div className="failed-list">{data.failed.map((row) => <div key={`${row.id}-${row.repeat}`}>
          <code>{row.id}#{row.repeat}</code><span className="chip">{row.kind}</span>
          <strong>{row.stop_reason ?? 'unknown stop'}</strong><span>{row.reason ?? 'No reason recorded'}</span>
        </div>)}</div> : <p>No failed run</p>}
      </section>
    </>}
  </div>
}
