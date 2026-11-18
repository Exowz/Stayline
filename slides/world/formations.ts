import deck from '../generated/deck.json'
import type { Formation, Link, Mark, Pt, Tone } from './engine'

export const N = 1500
export const SEIZED = 0
export const SATS = [1, 2, 3, 4, 5]
export const INNOCENT = 6
export const ORION_A = 7
export const ORION_B = 8
export const QUERY = 9
export const MONEY = Array.from({ length: 18 }, (_, k) => 20 + k)
export const RUN0 = 100
export const SPAN0 = 300

const hash = (i: number, s: number) => {
  const n = Math.sin(i * 127.1 + s * 311.7) * 43758.5453
  return n - Math.floor(n)
}
const gauss = (i: number, s: number) =>
  Math.sqrt(-2 * Math.log(Math.max(1e-6, hash(i, s)))) * Math.cos(2 * Math.PI * hash(i, s + 1))

const CLUSTERS: [number, number, number, number][] = [
  [1180, 560, 300, 210], [1480, 420, 220, 160], [1560, 720, 250, 180], [980, 760, 190, 130],
  [1300, 850, 230, 110], [900, 440, 150, 110], [1700, 560, 140, 190], [1280, 330, 200, 90],
]

export function cloudPt(i: number, dx = 0, dy = 0, spread = 1): Pt {
  if (hash(i, 3) < 0.8) {
    const c = CLUSTERS[Math.floor(hash(i, 4) * CLUSTERS.length)]
    const tone: Tone = hash(i, 8) < 0.05 ? 'blue' : hash(i, 9) < 0.28 ? 'soft' : 'ink'
    return {
      x: c[0] + dx + gauss(i, 5) * c[2] * 0.5 * spread, y: c[1] + dy + gauss(i, 7) * c[3] * 0.5 * spread,
      z: gauss(i, 11) * 260, r: 1.4 + hash(i, 13) * 1.7, a: 0.3 + hash(i, 14) * 0.5, tone,
    }
  }
  return dust(i, 0.2)
}

export function dust(i: number, a = 0.12): Pt {
  return { x: hash(i, 21) * 1920, y: hash(i, 22) * 1080, z: -300 - hash(i, 23) * 700, r: 1.1 + hash(i, 24) * 0.9, a: a * (0.6 + hash(i, 25) * 0.8), tone: 'soft' }
}

const dim = (p: Pt, k = 0.35): Pt => ({ ...p, a: p.a * k })

function base(dx = 0, dy = 0, k = 1): Pt[] {
  return Array.from({ length: N }, (_, i) => dim(cloudPt(i, dx, dy), k))
}
function quiet(): Pt[] {
  return Array.from({ length: N }, (_, i) => dust(i, i % 7 === 0 ? 0.3 : 0.16))
}
function put(pts: Pt[], overrides: Record<number, Partial<Pt>>) {
  for (const key of Object.keys(overrides)) {
    const i = Number(key)
    pts[i] = { ...pts[i], ...overrides[i] }
  }
  return pts
}

// ---------- scene 1 and 2: the seized contract ----------
export const SEIZED_AT = { x: 1160, y: 560 }
export const FAN = [-0.9, -0.45, 0, 0.45, 0.9]
export const FAN_R = 140
export const satAt = (k: number) => ({ x: SEIZED_AT.x + Math.cos(FAN[k]) * FAN_R, y: SEIZED_AT.y + Math.sin(FAN[k]) * FAN_R })

export function hero(step: number): Formation {
  const pts = base(0, 0, 1)
  const over: Record<number, Partial<Pt>> = { [SEIZED]: { ...SEIZED_AT, z: 0, r: 8, a: 1, tone: 'blue', glow: 1.4 } }
  const links: Link[] = []
  const marks: Mark[] = []
  const shown = Math.max(0, Math.min(5, step - 1))
  for (let k = 0; k < shown; k++) {
    over[SATS[k]] = { ...satAt(k), z: 0, r: 5, a: 1, tone: 'blue', glow: 0.9 }
    links.push({ a: SEIZED, b: SATS[k], tone: 'blue' })
  }
  if (step >= 1) marks.push({ i: SEIZED, r: 30, tone: 'blue' })
  if (step >= 6) marks.push({ i: SEIZED, r: FAN_R + 34, tone: 'blue', pulse: false })
  return { pts: put(pts, over), links, marks, pose: { yaw: 0.06 } }
}

export const CONTRACT = { x: 1300, y: 540 }
export const INNOCENT_AT = { x: 1590, y: 640 }
export function twoButtons(step: number): Formation {
  const pts = base(0, 0, step >= 3 ? 0.4 : 0.8)
  const over: Record<number, Partial<Pt>> = {
    [SEIZED]: { ...CONTRACT, z: 0, r: 8, a: 1, tone: 'blue', glow: 1.4 },
    [INNOCENT]: { ...INNOCENT_AT, z: 0, r: 6, a: 1, tone: step >= 1 ? 'fail' : 'ink', glow: 1 },
  }
  const marks: Mark[] = [{ i: SEIZED, r: 30, tone: 'blue' }]
  if (step >= 1) marks.push({ i: INNOCENT, r: 28, tone: 'fail' })
  MONEY.forEach((id, k) => {
    over[id] = step >= 2 && step < 3
      ? { x: CONTRACT.x + 30, y: CONTRACT.y, z: 0, r: 3, a: 1, tone: 'blue', glow: 0.8, motion: t => [((t * 150 + k * 24) % 440), Math.sin(t * 2 + k) * 8 + (k % 3) * 6 - 6] }
      : {}
  })
  return { pts: put(pts, over), marks }
}

// ---------- scene 3: the backend ----------
export const DB = [
  { name: 'subscribers', x: 330 }, { name: 'contracts', x: 760 }, { name: 'requests', x: 1190 }, { name: 'ledger', x: 1620 },
]
export const DB_Y = 880
export function backend(step: number): Formation {
  const pts = quiet()
  const over: Record<number, Partial<Pt>> = {}
  DB.forEach((d, c) => {
    for (let k = 0; k < 70; k++) {
      const i = 200 + c * 70 + k
      const ang = hash(i, 31) * Math.PI * 2
      const rad = Math.sqrt(hash(i, 32)) * 62
      over[i] = { x: d.x + Math.cos(ang) * rad, y: DB_Y + Math.sin(ang) * rad * 0.62, z: 0, r: 1.8 + hash(i, 33) * 1.3, a: 0.85, tone: c === 3 ? 'blue' : 'ink', glow: c === 3 ? 0.4 : 0 }
    }
  })
  const marks: Mark[] = step >= 2 ? [{ i: 200 + 70 + 5, r: 80, tone: 'blue' }] : []
  return { pts: put(pts, over), marks, stagger: 'y' }
}

// ---------- scene 4: the graph ----------
export const LOOP = { x: 520, y: 690, rx: 330, ry: 175 }
export const STAGES = [
  { name: 'prepare', x: 1010 }, { name: 'approve', x: 1250 }, { name: 'write', x: 1490 }, { name: 'verify', x: 1730 },
]
export function graph(step: number): Formation {
  const pts = quiet()
  const over: Record<number, Partial<Pt>> = {}
  for (let k = 0; k < 140; k++) {
    const i = 200 + k
    const phase = (k / 140) * Math.PI * 2
    const jr = 1 + gauss(i, 41) * 0.045
    over[i] = {
      x: LOOP.x + Math.cos(phase) * LOOP.rx * jr, y: LOOP.y + Math.sin(phase) * LOOP.ry * jr, z: gauss(i, 42) * 60,
      r: 2 + hash(i, 43) * 1.6, a: 0.9, tone: k % 9 === 0 ? 'blue' : 'ink', glow: k % 9 === 0 ? 0.6 : 0,
      motion: t => {
        const a = phase + t * 0.42
        return [LOOP.x + Math.cos(a) * LOOP.rx * jr - (LOOP.x + Math.cos(phase) * LOOP.rx * jr), LOOP.y + Math.sin(a) * LOOP.ry * jr - (LOOP.y + Math.sin(phase) * LOOP.ry * jr)]
      },
    }
  }
  if (step >= 2) {
    STAGES.forEach((s, c) => {
      for (let k = 0; k < 28; k++) {
        const i = 400 + c * 28 + k
        const ang = hash(i, 51) * Math.PI * 2
        const rad = Math.sqrt(hash(i, 52)) * 44
        over[i] = { x: s.x + Math.cos(ang) * rad, y: 690 + Math.sin(ang) * rad, z: 0, r: 2 + hash(i, 53) * 1.3, a: 0.9, tone: c === 1 ? 'blue' : 'ink', glow: c === 1 ? 0.7 : 0 }
      }
    })
  }
  const marks: Mark[] = step >= 2 ? [{ i: 400 + 28 + 3, r: 68, tone: 'blue' }] : []
  return { pts: put(pts, over), marks }
}

// ---------- scenes 5 and 6: the trace ----------
export const TRACE = { x0: 104, x1: 1140, y: 964 }
export function trace(step: number, key: 's01' | 's14' = 's01'): Formation {
  const pts = quiet()
  const t = deck.traces[key]
  const over: Record<number, Partial<Pt>> = {}
  if (step >= 4 && key === 's01') {
    t.spans.forEach((span, k) => {
      const x = TRACE.x0 + (span.t0_ms / t.total_ms) * (TRACE.x1 - TRACE.x0)
      const bad = key === 's14' && span.kind === 'LLM' && span.tokens_out === 4000
      over[SPAN0 + k] = { x, y: TRACE.y, z: 0, r: 1.8 + Math.min(2.5, Math.sqrt(span.ms) / 12), a: 1, tone: bad ? 'fail' : span.kind === 'LLM' ? 'blue' : 'ink', glow: bad ? 1.4 : 0.3 }
    })
  }
  return { pts: put(pts, over), stagger: 'x' }
}

// ---------- scene 7: memory ----------
export const ORION = { a: { x: 1250, y: 470 }, b: { x: 1440, y: 650 }, q: { x: 1010, y: 560 } }
export function memory(phase: 'none' | 'without' | 'with'): Formation {
  const pts = base(0, 0, 0.7)
  const over: Record<number, Partial<Pt>> = {
    [ORION_A]: { ...ORION.a, z: 0, r: 8, a: 1, tone: 'blue', glow: 1.3 },
    [ORION_B]: { ...ORION.b, z: 0, r: 8, a: 1, tone: 'blue', glow: 1.3 },
  }
  const links: Link[] = []
  const marks: Mark[] = []
  if (phase !== 'none') over[QUERY] = { ...ORION.q, z: 0, r: 6, a: 1, tone: 'ink', glow: 1.4 }
  if (phase === 'without') {
    marks.push({ i: ORION_A, r: 30, tone: 'soft' }, { i: ORION_B, r: 30, tone: 'soft' })
    links.push({ a: QUERY, b: ORION_A, tone: 'soft' }, { a: QUERY, b: ORION_B, tone: 'soft' })
  }
  if (phase === 'with') {
    marks.push({ i: ORION_A, r: 32, tone: 'blue' })
    links.push({ a: QUERY, b: ORION_A, tone: 'blue', width: 1.4 })
  }
  return { pts: put(pts, over), links, marks }
}

// ---------- scenes 8, 9, 10: the 90 runs ----------
type Run = (typeof deck.runs)[number]
const KINDS = ['normal', 'ambiguous', 'impossible', 'adversarial']
export interface GridSpec { x0: number, y0: number, col: number, row: number, gap: number, r: number }
export const BIG: GridSpec = { x0: 175, y0: 470, col: 52, row: 62, gap: 38, r: 9 }
export const LEFT: GridSpec = { x0: 120, y0: 560, col: 25.5, row: 40, gap: 14, r: 6.5 }
export const RIGHT: GridSpec = { x0: 1010, y0: 560, col: 25.5, row: 40, gap: 14, r: 6.5 }

const order = (() => {
  const seen = new Map<string, string>()
  for (const r of deck.runs) seen.set(r.id, r.kind)
  return [...seen.entries()].sort((a, b) => KINDS.indexOf(a[1]) - KINDS.indexOf(b[1]) || Number(a[0].slice(1)) - Number(b[0].slice(1))).map(e => e[0])
})()
export const kindOf = (id: string) => KINDS[KINDS.findIndex(k => deck.runs.find(r => r.id === id)?.kind === k)]
export function colX(id: string, g: GridSpec) {
  const c = order.indexOf(id)
  const block = KINDS.indexOf(deck.runs.find(r => r.id === id)!.kind)
  return g.x0 + c * g.col + block * g.gap
}
export const runPos = (run: Run, g: GridSpec) => ({ x: colX(run.id, g), y: g.y0 + run.repeat * g.row })
export function blocks(g: GridSpec) {
  return KINDS.map((kind, b) => {
    const ids = order.filter(id => deck.runs.find(r => r.id === id)!.kind === kind)
    const x0 = colX(ids[0], g), x1 = colX(ids[ids.length - 1], g)
    return { kind, x0, x1, ids }
  })
}

function runPts(runs: Run[], g: GridSpec, offset: number, flat: Pt[], failTone: Tone = 'fail') {
  runs.forEach((run, k) => {
    const p = runPos(run, g)
    flat[offset + k] = { x: p.x, y: p.y, z: 0, r: g.r * (run.passed ? 0.4 : 0.5), a: run.passed ? 0.9 : 1, tone: run.passed ? 'ink' : failTone, glow: run.passed ? 0.2 : 0.7 }
  })
}

export function results(step: number): Formation {
  const pts = quiet()
  runPts(deck.runs as Run[], BIG, RUN0, pts)
  const marks: Mark[] = step >= 1 ? [] : []
  return { pts, marks, stagger: 'x' }
}

export function errors(step: number): Formation {
  const pts = quiet()
  runPts((step >= 2 ? deck.runs : deck.baseline1_runs) as Run[], BIG, RUN0, pts)
  return { pts, stagger: 'x' }
}

export function compare(): Formation {
  const pts = quiet()
  runPts(deck.runs as Run[], LEFT, RUN0, pts)
  runPts(deck.mistral_runs as Run[], RIGHT, RUN0 + 90, pts)
  return { pts, stagger: 'x' }
}

export const FINAL_AT = { x: 960, y: 150 }
export function finale(): Formation {
  const pts = Array.from({ length: N }, (_, i) => dust(i, i % 5 === 0 ? 0.28 : 0.14))
  const over: Record<number, Partial<Pt>> = {}
  const links: Link[] = []
  // a halo of contracts closing round the wordmark, slowly turning
  const halo = 360
  for (let k = 0; k < halo; k++) {
    const i = 600 + k
    const phase = (k / halo) * Math.PI * 2
    const jr = 1 + gauss(i, 61) * 0.035
    const x0 = 960 + Math.cos(phase) * 820 * jr, y0 = 600 + Math.sin(phase) * 330 * jr
    over[i] = {
      x: x0, y: y0, z: gauss(i, 62) * 70, r: 1.5 + hash(i, 63) * 1.6, a: 0.75, tone: k % 12 === 0 ? 'blue' : 'ink',
      motion: t => [960 + Math.cos(phase + t * 0.06) * 820 * jr - x0, 600 + Math.sin(phase + t * 0.06) * 330 * jr - y0],
    }
  }
  over[SEIZED] = { ...FINAL_AT, z: 0, r: 8, a: 1, tone: 'blue', glow: 1.8 }
  SATS.forEach((id, k) => {
    const ang = -Math.PI / 2 + (k - 2) * 0.62
    over[id] = { x: FINAL_AT.x + Math.cos(ang) * 58, y: FINAL_AT.y + Math.sin(ang) * 58 + 40, z: 0, r: 3.6, a: 1, tone: 'blue', glow: 0.9 }
    links.push({ a: SEIZED, b: id, tone: 'blue' })
  })
  return { pts: put(pts, over), links, marks: [{ i: SEIZED, r: 34, tone: 'blue' }], stagger: 'random' }
}

export function calm(): Formation {
  return { pts: base(0, 0, 0.4), stagger: 'random' }
}
