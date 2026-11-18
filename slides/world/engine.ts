// A small particle world drawn on one canvas. Formations describe where every particle
// should be; the engine flows the particles there with a staggered, curved tween, adds a
// slow depth drift, additive glow, links and rings, and eases the camera pose.

export type Tone = 'ink' | 'blue' | 'fail' | 'soft'
export const TONES: Record<Tone, [number, number, number]> = {
  ink: [236, 240, 250], blue: [122, 146, 255], fail: [255, 92, 98], soft: [140, 150, 178],
}

export interface Pt {
  x: number, y: number, z: number, r: number, a: number, tone: Tone
  glow?: number
  motion?: (t: number) => [number, number]
}
export interface Link { a: number, b: number, tone: Tone, width?: number }
export interface Mark { i: number, r: number, tone: Tone, pulse?: boolean }
export interface Pose { yaw: number, zoom: number, x: number, y: number }
export interface Formation {
  pts: Pt[]
  links?: Link[]
  marks?: Mark[]
  pose?: Partial<Pose>
  stagger?: 'random' | 'x' | 'y' | 'none'
  drift?: number
}

export const W = 1920
export const H = 1080
const DURATION = 1.5
const clamp = (v: number, a = 0, b = 1) => Math.min(b, Math.max(a, v))
const ease = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2)
const rand = (i: number, s: number) => {
  const n = Math.sin(i * 127.1 + s * 311.7) * 43758.5453
  return n - Math.floor(n)
}

function sprite(tone: Tone): HTMLCanvasElement {
  const size = 96
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')!
  const [r, gg, b] = TONES[tone]
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  grad.addColorStop(0, `rgba(${r},${gg},${b},1)`)
  grad.addColorStop(0.12, `rgba(${r},${gg},${b},.92)`)
  grad.addColorStop(0.32, `rgba(${r},${gg},${b},.28)`)
  grad.addColorStop(0.62, `rgba(${r},${gg},${b},.07)`)
  grad.addColorStop(1, `rgba(${r},${gg},${b},0)`)
  g.fillStyle = grad
  g.fillRect(0, 0, size, size)
  return c
}

export class World {
  private ctx: CanvasRenderingContext2D
  private sprites: Record<Tone, HTMLCanvasElement>
  private n: number
  private cur: Float32Array // x y z r a glow cr cg cb  (9 per particle)
  private from: Float32Array
  private to: Float32Array
  private delay: Float32Array
  private swirl: Float32Array
  private tones: Tone[]
  private tonesFrom: Tone[]
  private motions: (((t: number) => [number, number]) | undefined)[]
  private formation: Formation
  private pose: Pose = { yaw: 0, zoom: 1, x: 0, y: 0 }
  private poseTo: Pose = { yaw: 0, zoom: 1, x: 0, y: 0 }
  private started = 0
  private overlay = 0
  private last = 0
  private frame = 0
  private scale = 1
  private still = false
  private drift = 1
  private seed = 0
  private pos: Float32Array

  constructor(private canvas: HTMLCanvasElement, count: number) {
    this.n = count
    this.pos = new Float32Array(count * 3)
    this.ctx = canvas.getContext('2d')!
    this.sprites = { ink: sprite('ink'), blue: sprite('blue'), fail: sprite('fail'), soft: sprite('soft') }
    this.cur = new Float32Array(count * 9)
    this.from = new Float32Array(count * 9)
    this.to = new Float32Array(count * 9)
    this.delay = new Float32Array(count)
    this.swirl = new Float32Array(count)
    this.tones = new Array(count).fill('ink')
    this.tonesFrom = new Array(count).fill('ink')
    this.motions = new Array(count).fill(undefined)
    this.formation = { pts: [] }
  }

  resize() {
    const width = this.canvas.getBoundingClientRect().width || W
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    const backing = Math.min(Math.round(width * dpr), 2560)
    this.canvas.width = backing
    this.canvas.height = Math.round(backing * H / W)
    this.scale = this.canvas.width / W
  }

  /** Move to a new formation. `instant` snaps (print, export, reduced motion). */
  go(f: Formation, instant = false, big = false) {
    const prev = this.formation
    this.formation = f
    this.seed += 1
    const first = prev.pts.length === 0
    for (let i = 0; i < this.n; i++) {
      const p = f.pts[i]
      const o = i * 9
      // snapshot the rendered state as the new starting point
      for (let k = 0; k < 9; k++) this.from[o + k] = this.cur[o + k]
      this.to.set([p.x, p.y, p.z, p.r, p.a, p.glow ?? 0, 0, 0, 0], o)
      this.tonesFrom[i] = this.tones[i]
      this.tones[i] = p.tone
      this.motions[i] = p.motion
      const mode = f.stagger ?? 'random'
      const spread = mode === 'none' ? 0 : 0.55
      const key = mode === 'x' ? p.x / W : mode === 'y' ? p.y / H : rand(i, this.seed)
      this.delay[i] = key * spread
      this.swirl[i] = (rand(i, this.seed + 9) - 0.5) * (big ? 520 : 200)
      if (first) this.from.set(this.to.subarray(o, o + 9), o)
    }
    this.poseTo = { yaw: f.pose?.yaw ?? 0, zoom: f.pose?.zoom ?? 1, x: f.pose?.x ?? 0, y: f.pose?.y ?? 0 }
    this.drift = f.drift ?? 1
    this.started = performance.now()
    this.overlay = 0
    if (instant || this.still) {
      this.pose = { ...this.poseTo }
      this.started = -1e9
      this.overlay = 1
      this.step(performance.now())
      this.draw(performance.now())
    }
  }

  setStill(v: boolean) { this.still = v }

  start() {
    const loop = (now: number) => {
      this.frame = requestAnimationFrame(loop)
      this.step(now)
      this.draw(now)
    }
    this.frame = requestAnimationFrame(loop)
  }

  stop() { cancelAnimationFrame(this.frame) }

  private step(now: number) {
    const dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0.016
    this.last = now
    const t = (now - this.started) / 1000
    const k = 1 - Math.exp(-dt * 3.2)
    const pose = this.pose
    pose.yaw += (this.poseTo.yaw - pose.yaw) * k
    pose.zoom += (this.poseTo.zoom - pose.zoom) * k
    pose.x += (this.poseTo.x - pose.x) * k
    pose.y += (this.poseTo.y - pose.y) * k
    this.overlay = clamp((t - 0.7) / 0.7)
    for (let i = 0; i < this.n; i++) {
      const o = i * 9
      const p = clamp((t - this.delay[i]) / DURATION)
      const e = ease(p)
      const bow = Math.sin(Math.PI * p) * this.swirl[i]
      const dx = this.to[o] - this.from[o]
      const dy = this.to[o + 1] - this.from[o + 1]
      const len = Math.hypot(dx, dy) || 1
      this.cur[o] = this.from[o] + dx * e + (-dy / len) * bow * 0.5
      this.cur[o + 1] = this.from[o + 1] + dy * e + (dx / len) * bow * 0.5
      for (let c = 2; c < 6; c++) this.cur[o + c] = this.from[o + c] + (this.to[o + c] - this.from[o + c]) * e
      this.cur[o + 6] = clamp((t - this.delay[i] - 0.25) / 0.9)
    }
  }

  /** Where particle i is on the 1920x1080 canvas right now. */
  at(i: number, now = performance.now()): [number, number, number] {
    const o = i * 9
    return this.project(this.cur[o] + this.motion(i, now)[0], this.cur[o + 1] + this.motion(i, now)[1], this.cur[o + 2], now)
  }

  private motion(i: number, now: number): [number, number] {
    const m = this.motions[i]
    if (!m) return [0, 0]
    const w = clamp(((now - this.started) / 1000 - this.delay[i] - DURATION * 0.6) / 0.9)
    const [mx, my] = m(now / 1000)
    return [mx * w, my * w]
  }

  private project(x: number, y: number, z: number, now: number): [number, number, number] {
    const { yaw, zoom, x: px, y: py } = this.pose
    const drift = this.drift
    const sway = Math.sin(now * 0.00021) * 0.035 * drift
    const a = yaw + sway
    const dx = x - W / 2
    const x1 = dx * Math.cos(a) + z * Math.sin(a)
    const z1 = -dx * Math.sin(a) + z * Math.cos(a)
    const s = 1 / (1 - z1 / 2400)
    return [W / 2 + (x1 * zoom + px) * s, H / 2 + ((y - H / 2) * zoom + py) * s, s]
  }

  private draw(now: number) {
    const c = this.ctx
    c.setTransform(this.scale, 0, 0, this.scale, 0, 0)
    c.clearRect(0, 0, W, H)
    c.globalCompositeOperation = 'lighter'
    const tt = now / 1000
    const pos = this.pos
    for (let i = 0; i < this.n; i++) {
      const o = i * 9
      const [mx, my] = this.motion(i, now)
      const [X, Y, s] = this.project(this.cur[o] + mx, this.cur[o + 1] + my, this.cur[o + 2], now)
      pos[i * 3] = X; pos[i * 3 + 1] = Y; pos[i * 3 + 2] = s
      const a = this.cur[o + 4]
      if (a < 0.01) continue
      const tw = 0.82 + 0.18 * Math.sin(tt * 0.7 + i * 1.7)
      const glow = this.cur[o + 5]
      const size = (this.cur[o + 3] * (5 + glow * 5)) * s
      const tone = this.tones[i]
      const from = this.tonesFrom[i]
      const mix = this.cur[o + 6]
      const base = clamp(a * tw * (0.75 + 0.25 * s))
      if (from !== tone && mix < 1) {
        c.globalAlpha = base * (1 - mix)
        c.drawImage(this.sprites[from], X - size, Y - size, size * 2, size * 2)
      }
      c.globalAlpha = base * (from !== tone ? mix : 1)
      c.drawImage(this.sprites[tone], X - size, Y - size, size * 2, size * 2)
    }
    // links
    const f = this.formation
    if (f.links && this.overlay > 0.01) {
      for (const l of f.links) {
        const [x1, y1] = [pos[l.a * 3], pos[l.a * 3 + 1]]
        const [x2, y2] = [pos[l.b * 3], pos[l.b * 3 + 1]]
        const [r, g, b] = TONES[l.tone]
        c.lineCap = 'round'
        c.strokeStyle = `rgba(${r},${g},${b},${0.16 * this.overlay})`
        c.lineWidth = (l.width ?? 1) * 7
        c.beginPath(); c.moveTo(x1, y1); c.lineTo(x1 + (x2 - x1) * this.overlay, y1 + (y2 - y1) * this.overlay); c.stroke()
        c.strokeStyle = `rgba(${r},${g},${b},${0.85 * this.overlay})`
        c.lineWidth = (l.width ?? 1) * 1.6
        c.beginPath(); c.moveTo(x1, y1); c.lineTo(x1 + (x2 - x1) * this.overlay, y1 + (y2 - y1) * this.overlay); c.stroke()
      }
    }
    // rings
    c.globalCompositeOperation = 'source-over'
    if (f.marks && this.overlay > 0.01) {
      for (const m of f.marks) {
        const [r, g, b] = TONES[m.tone]
        const pulse = m.pulse === false ? 0 : Math.sin(tt * 2.4) * 5
        c.strokeStyle = `rgba(${r},${g},${b},${0.85 * this.overlay})`
        c.lineWidth = 2.5
        c.beginPath(); c.arc(pos[m.i * 3], pos[m.i * 3 + 1], (m.r + pulse) * pos[m.i * 3 + 2] * this.overlay, 0, Math.PI * 2); c.stroke()
      }
    }
    c.globalAlpha = 1
  }
}
