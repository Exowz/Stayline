<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { CONTRACT, INNOCENT_AT } from '../world/formations'

const { shown, print } = useBeat()

// The grader as a balance. Left pan: the five effects the law lists. Right pan: what the agent changed.
// Three states play once after the third click, then the scale holds level: exactly the same five.
const PIVOT = { x: 1410, y: 650 }
const HALF = 300
const HANG = 150
const theta = ref(0)
const stage = ref(0)
const state = { t: 0 }
let timeline: gsap.core.Timeline | undefined
const still = () => print.value || matchMedia('(prefers-reduced-motion: reduce)').matches

watch(() => shown(3), (on) => {
  timeline?.kill()
  if (!on) { stage.value = 0; theta.value = 0; state.t = 0; return }
  if (still()) { stage.value = 3; theta.value = 0; return }
  state.t = 0
  stage.value = 1
  const swing = (to: number, ease: string, d: number) => gsap.to(state, { t: to, duration: d, ease, onUpdate: () => { theta.value = state.t } })
  timeline = gsap.timeline({ delay: 0.9 })
  timeline.add(swing(-11, 'back.out(1.6)', 1.1))
    .add(() => { stage.value = 2 }, '+=1.5')
    .add(swing(11, 'back.out(1.6)', 1.2), '<')
    .add(() => { stage.value = 3 }, '+=1.5')
    .add(swing(0, 'elastic.out(1, 0.45)', 1.8), '<')
}, { immediate: true })
onBeforeUnmount(() => timeline?.kill())

const rad = computed(() => (theta.value * Math.PI) / 180)
const end = (sign: number) => ({ x: PIVOT.x + sign * HALF * Math.cos(rad.value), y: PIVOT.y + sign * HALF * Math.sin(rad.value) })
const left = computed(() => end(-1))
const right = computed(() => end(1))
const pan = (e: { x: number, y: number }) => ({ x: e.x, y: e.y + HANG })
const panPath = (c: { x: number, y: number }) => `M ${c.x - 140} ${c.y} Q ${c.x} ${c.y + 58} ${c.x + 140} ${c.y} Z`
const slots = (c: { x: number, y: number }) => [1, 2, 3, 4, 5].map(k => ({ k, x: c.x + (k - 3) * 54, y: c.y - 28 }))
const extras = (c: { x: number, y: number }) => [0, 1].map(j => ({ x: c.x + (j - 0.5) * 54, y: c.y - 82 }))
const have = (k: number) => stage.value === 0 ? false : stage.value === 1 ? k <= 3 : true
const caption = computed(() => [
  { head: '', sub: '', cls: '' },
  { head: 'Blocks too little', sub: 'two required restrictions are missing', cls: 'bad' },
  { head: 'Blocks too much', sub: 'two changes the law does not list', cls: 'bad' },
  { head: 'Exactly the five the law lists', sub: 'the same effects, no more, no fewer', cls: 'good' },
][stage.value])
</script>

<template><main class="slide">
  <Headline :page="2" eyebrow="The risk" before="Two " emphasis="dangerous" after=" buttons" />

  <div class="blk blk-a rv rv-l" :class="{ on: shown(1) }">
    <span class="tag">01 / Block a contract</span>
    <p class="stmt">Pick the wrong one and an <em>innocent</em> client is frozen.</p>
  </div>
  <div class="blk blk-b rv rv-l" :class="{ on: shown(2) }">
    <span class="tag">02 / Pay out a rachat or an advance</span>
    <p class="stmt">On a seized contract, that money must <em>not leave</em>.</p>
  </div>

  <div class="lab seized rv" :class="{ on: !shown(3) }" :style="{ left: `${CONTRACT.x - 130}px`, top: `${CONTRACT.y - 100}px` }">
    <b>seized contract</b>
  </div>
  <div class="lab bad rv" :class="{ on: shown(1) && !shown(3) }" :style="{ left: `${INNOCENT_AT.x - 120}px`, top: `${INNOCENT_AT.y + 52}px` }">
    <b>frozen by mistake</b><span>an innocent client</span>
  </div>
  <svg class="beams" viewBox="0 0 1920 1080" aria-hidden="true">
    <path class="draw red" :class="{ on: shown(1) && !shown(3) }" pathLength="1" :d="`M ${INNOCENT_AT.x} ${INNOCENT_AT.y + 38} L ${INNOCENT_AT.x} ${INNOCENT_AT.y + 62}`" />
    <path class="wall" :class="{ on: shown(2) && !shown(3) }" d="M 1790 400 L 1790 700" />
  </svg>
  <div class="lab out rv" :class="{ on: shown(2) && !shown(3) }" style="left: 1500px; top: 350px"><b>money that must not leave</b></div>

  <div class="note rv" :class="{ on: shown(3) }">
    <p>The grader reads the final state of the database, in both directions: the same five effects, no more, no fewer.</p>
    <p class="mono cite">Crim. 30 Oct 2012, n° 12-84.961</p>
  </div>

  <div class="scale rv" :class="{ on: shown(3), win: stage === 3, fail: stage === 1 || stage === 2 }">
    <div class="cap" :class="caption.cls"><b class="serif">{{ caption.head }}</b><span>{{ caption.sub }}</span></div>
    <svg viewBox="0 0 1920 1080" aria-hidden="true">
      <line :x1="PIVOT.x" :y1="PIVOT.y" :x2="PIVOT.x" y2="930" class="post" />
      <path d="M 1330 934 L 1490 934 M 1352 934 Q 1410 900 1468 934" class="post" />
      <line :x1="left.x" :y1="left.y" :x2="right.x" :y2="right.y" class="beam" />
      <circle :cx="PIVOT.x" :cy="PIVOT.y" r="13" class="pivot" />
      <g v-for="(e, side) in [left, right]" :key="side">
        <path :d="`M ${e.x} ${e.y} L ${pan(e).x - 130} ${pan(e).y} M ${e.x} ${e.y} L ${pan(e).x + 130} ${pan(e).y}`" class="hang" />
        <path :d="panPath(pan(e))" class="pan" />
        <template v-if="side === 0">
          <g v-for="d in slots(pan(e))" :key="d.k"><circle :cx="d.x" :cy="d.y" r="23" class="w law" /><text :x="d.x" :y="d.y + 9" text-anchor="middle" class="n">{{ d.k }}</text></g>
        </template>
        <template v-else>
          <g v-for="d in slots(pan(e))" :key="d.k"><circle :cx="d.x" :cy="d.y" r="23" class="w mine" :class="{ empty: !have(d.k) }" /><text v-if="have(d.k)" :x="d.x" :y="d.y + 9" text-anchor="middle" class="n">{{ d.k }}</text></g>
          <g v-for="(d, j) in extras(pan(e))" :key="`x${j}`" :class="{ off: stage !== 2 }"><circle :cx="d.x" :cy="d.y" r="23" class="w extra" /><text :x="d.x" :y="d.y + 9" text-anchor="middle" class="n">+</text></g>
        </template>
      </g>
      <text :x="pan(left).x" y="905" text-anchor="middle" class="lbl">what the law lists</text>
      <text :x="pan(right).x" y="905" text-anchor="middle" class="lbl">what the agent changed</text>
    </svg>
  </div>
</main></template>

<style scoped>
.blk { position: absolute; left: 100px; width: 780px; }
.blk .tag { display: block; margin-bottom: 14px; }
.blk-a { top: 300px; }
.blk-b { top: 500px; }
.lab { position: absolute; z-index: 2; font-size: 24px; color: var(--muted); display: grid; gap: 2px; }
.lab b { font: 500 24px var(--mono); color: var(--blue); }
.lab.bad b { color: var(--fail); }
.lab.out b { color: var(--fail); font-size: 23px; }
.wall { stroke: var(--fail); stroke-width: 3; stroke-dasharray: 8 10; opacity: 0; filter: drop-shadow(0 0 8px rgba(255, 92, 98, .5)); transition: opacity .6s .5s; }
.wall.on { opacity: .9; }
.note { position: absolute; left: 100px; top: 740px; width: 780px; }
.note p { font-size: 28px; line-height: 1.3; color: var(--ivory); }
.note .cite { margin-top: 14px; font-size: 22px; color: var(--muted); }
.scale { position: absolute; inset: 0; pointer-events: none; }
.scale svg { position: absolute; inset: 0; width: 1920px; height: 1080px; overflow: visible; }
.cap { position: absolute; right: 100px; top: 372px; width: 800px; text-align: right; }
.cap b { display: block; font-size: 58px; font-weight: 400; letter-spacing: -.02em; line-height: 1.05; transition: color .4s; }
.cap span { display: block; margin-top: 8px; font-size: 26px; color: var(--muted); }
.cap.bad b { color: var(--fail); } .cap.good b { color: var(--ivory); text-shadow: 0 0 40px rgba(122, 146, 255, .6); }
.post, .beam, .hang { stroke: rgba(200, 210, 255, .8); fill: none; stroke-linecap: round; }
.post { stroke-width: 3; } .beam { stroke-width: 7; } .hang { stroke-width: 2; }
.pivot { fill: #0a0d2c; stroke: rgba(200, 210, 255, .9); stroke-width: 3; }
.pan { fill: rgba(200, 210, 255, .08); stroke: rgba(200, 210, 255, .85); stroke-width: 3; stroke-linejoin: round; }
.scale.win .pan, .scale.win .beam { stroke: var(--blue); filter: drop-shadow(0 0 12px var(--blue-glow)); }
.scale.fail .beam { stroke: var(--fail); }
.w { fill: rgba(236, 240, 250, .16); stroke: rgba(236, 240, 250, .9); stroke-width: 3; transition: opacity .5s, fill .4s; }
.w.mine { fill: rgba(122, 146, 255, .3); stroke: var(--blue); }
.w.mine.empty { fill: none; stroke-dasharray: 5 7; stroke: rgba(200, 210, 255, .5); }
.w.extra { fill: rgba(255, 92, 98, .32); stroke: var(--fail); }
.off { opacity: 0; } g { transition: opacity .5s; }
.n { font: 600 24px var(--mono); fill: var(--ivory); }
.lbl { font: 500 24px var(--mono); fill: var(--muted); }
</style>
