import deck from '../generated/deck.json'
import type { WorldName } from './pages'

export const N = 240
export interface Target { x: number, y: number, radius: number, alpha: number, tone: 'ink' | 'blue' | 'fail', fail: boolean }
const random = (i: number, seed: number) => {
  const n = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453
  return n - Math.floor(n)
}
const field = Array.from({ length: N }, (_, i): Target => ({
  x: 118 + random(i, 1) * 1684, y: 170 + random(i, 2) * 700,
  radius: 2.4 + random(i, 3) * 2.2, alpha: 0.35,
  tone: i % 19 === 0 ? 'blue' : 'ink', fail: false,
}))
const grid = (runs: typeof deck.runs, x0: number, width: number, y0: number, gapY: number, radius: number, label: boolean): Target[] =>
  runs.map(run => ({
    x: x0 + (Number(run.id.slice(1)) - 1) * width / 29,
    y: y0 + run.repeat * gapY,
    radius, alpha: 0.95, tone: run.passed ? 'ink' : 'fail', fail: label && !run.passed,
  }))

export function targets(name: WorldName): Target[] {
  if (name === 'field' || name === 'target') {
    const result = field.map(dot => ({ ...dot }))
    if (name === 'target') result[0] = { x: 1525, y: 420, radius: 13, alpha: 1, tone: 'blue', fail: false }
    return result
  }
  const compare = name === 'compare'
  const primary = compare ? grid(deck.runs, 176, 725, 560, 46, 8, false)
    : grid(name === 'before-after' ? deck.baseline1_runs : deck.runs, 230, 1460, 380, 84, 12, name === 'grid')
  const secondary = compare ? grid(deck.mistral_runs, 1020, 725, 560, 46, 8, false) : []
  return Array.from({ length: N }, (_, i) => primary[i] || secondary[i - 90] || { ...field[i], alpha: 0 })
}

export function afterTargets(): Target[] {
  const primary = grid(deck.runs, 230, 1460, 380, 84, 12, false)
  return Array.from({ length: N }, (_, i) => primary[i] || { ...field[i], alpha: 0 })
}
