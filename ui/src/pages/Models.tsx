import { useEffect, useState } from 'react'
import { getComparison } from '@/lib/api'
import type { Comparison, KindMetrics, RateMetrics, SetExtra } from '@/lib/api'
import { interval, pct, seconds, usd } from '@/lib/format'
import './evaluation.css'

type Side = { extra: SetExtra; overall: RateMetrics; byKind: KindMetrics[] }

function Measure({ label, value, better, safetyFail }: {
  label: string; value: string; better?: boolean; safetyFail?: boolean
}) {
  return <div className="model-measure"><span>{label}</span><strong className={safetyFail ? 'safety-fail' : ''}>
    {better && <span className="better-mark" aria-label="Better value">✓ </span>}{value}{safetyFail && ' (must be 0)'}
  </strong></div>
}

function ModelCard({ side, other }: { side: Side; other: Side }) {
  const { extra, overall, byKind } = side
  const lowCost = extra.cost_per_success !== null && other.extra.cost_per_success !== null
    && extra.cost_per_success < other.extra.cost_per_success
  const lowLatency = extra.latency_s.p50 !== null && other.extra.latency_s.p50 !== null
    && extra.latency_s.p50 < other.extra.latency_s.p50
  return <section className="island eval-panel model-card">
    <h2>{extra.model?.split('/').at(-1) ?? extra.name}</h2>
    <p className="model-name">{extra.model ?? 'Model unavailable'}</p>
    <div className="model-measures">
      <Measure label="Passed" value={`${overall.passed} of ${overall.runs} (${pct(overall.pass_rate)})`}
        better={overall.pass_rate > other.overall.pass_rate} />
      <Measure label="Wilson interval" value={interval(overall.ci_low, overall.ci_high)} />
      <Measure label="pass^k" value={pct(overall.pass_hat_k)}
        better={overall.pass_hat_k > other.overall.pass_hat_k} />
      <Measure label="Cost per success" value={usd(extra.cost_per_success)} better={lowCost} />
      <Measure label="Latency p50" value={seconds(extra.latency_s.p50)} better={lowLatency} />
      <Measure label="Latency p95" value={seconds(extra.latency_s.p95)}
        better={extra.latency_s.p95 !== null && other.extra.latency_s.p95 !== null && extra.latency_s.p95 < other.extra.latency_s.p95} />
      <Measure label="Under-blocking" value={String(extra.domain?.under_blocking ?? 'n/a')}
        safetyFail={Boolean(extra.domain?.under_blocking)} />
      <Measure label="Over-blocking" value={String(extra.domain?.over_blocking ?? 'n/a')}
        safetyFail={Boolean(extra.domain?.over_blocking)} />
    </div>
    <h3>Pass rate by kind</h3>
    <div className="model-measures">{byKind.map((row) => <Measure key={row.kind} label={row.kind}
      value={pct(row.pass_rate)} better={row.pass_rate > (other.byKind.find((item) => item.kind === row.kind)?.pass_rate ?? row.pass_rate)} />)}</div>
  </section>
}

export default function Models() {
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let live = true
    getComparison('results.jsonl', 'mistral/results.jsonl')
      .then((data) => { if (live) setComparison(data) })
      .catch((cause: unknown) => {
        if (live) setError(cause instanceof Error ? cause.message : 'Could not load comparison.')
      }).finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [])

  if (loading) return <section className="island eval-message" role="status">Loading models...</section>
  if (error) return <section className="island eval-message eval-error" role="alert">{error}</section>
  if (!comparison) return null
  const first = { extra: comparison.a_extra, overall: comparison.a.overall, byKind: comparison.a.by_kind }
  const second = { extra: comparison.b_extra, overall: comparison.b.overall, byKind: comparison.b.by_kind }
  return <div className="eval-layout">
    <div className="model-grid"><ModelCard side={first} other={second} /><ModelCard side={second} other={first} /></div>
    <section className="island eval-panel paired-panel">
      <h2>Paired comparison</h2>
      <p>{comparison.shared} shared scenarios. Scenarios passed on every repeat: only the first model {comparison.only_a},
        {' '}only the second {comparison.only_b}, both {comparison.both}, neither {comparison.neither}.
        {' '}Sign test p = {comparison.sign_test_p.toFixed(4)}.</p>
    </section>
  </div>
}
