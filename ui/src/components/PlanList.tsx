import { Check, CircleAlert } from 'lucide-react'
import type { RunView } from '@/lib/runState'
import { deriveSteps } from '@/lib/runState'

export default function PlanList({ run }: { run: RunView }) {
  const steps = deriveSteps(run.tools)
  const previewKey = run.preview?.tool === 'apply_seizure' ? 'apply'
    : run.preview?.tool === 'execute_operation' ? 'operate' : null
  const lastFilled = steps.findLastIndex((step) => step.tools.length > 0)
  return <section className="island panel plan-panel" aria-label="Run plan">
    <div className="panel-heading"><h2>Plan</h2><span>Live tool calls</span></div>
    <ol className="plan-list">
      {steps.map((step, index) => {
        const current = run.status === 'waiting' ? step.key === previewKey
          : run.status === 'running' && index === lastFilled
        const done = step.tools.length > 0 && (run.status === 'done' || index < lastFilled || (run.status === 'waiting' && !current))
        return <li key={step.key} className={current ? 'plan-step current' : done ? 'plan-step completed' : 'plan-step pending'}>
          <span className="step-mark" aria-label={done ? 'Completed' : current ? 'Current' : 'Pending'}>
            {done ? <Check size={13} strokeWidth={3} /> : index + 1}
          </span>
          <h3>{step.label}</h3><p>{step.explanation}</p>
          {step.tools.length > 0 && <ul className="tool-list">{step.tools.map((event, toolIndex) =>
            <li key={`${step.key}-${toolIndex}`} className={event.ok ? 'tool-row' : 'tool-row failed'}>
              {event.ok ? null : <CircleAlert size={13} aria-label="Failed" />}
              <code>{event.tool}</code>
              {['get_contract', 'get_rule', 'get_restriction_ledger'].includes(event.tool) &&
                <span className="safety-tag">safety check</span>}
              <span className="tool-result">{event.ok ? 'Completed' : `Failed: ${event.error_code ?? 'tool error'}`}</span>
              <span className="tool-ms">{event.ms} ms</span>
            </li>,
          )}</ul>}
          {current && run.status === 'waiting' && <div className="tool-row on-hold"><code>{run.preview?.tool}</code><span className="tool-result">Paused before writing</span><span className="tool-ms">On hold</span></div>}
        </li>
      })}
    </ol>
  </section>
}
