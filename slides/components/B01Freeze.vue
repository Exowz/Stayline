<script setup lang="ts">
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { SEIZED_AT, satAt } from '../world/formations'

const { shown } = useBeat()
const items = [
  ['rachat', 'withdrawals stop'], ['renonciation', 'cancelling stops'], ['nantissement', 'pledging stops'],
  ['acceptation_benefice', 'no new beneficiary acceptance'], ['avance', 'no advance from the insurer'],
]
const slot = (k: number) => 370 + k * 92
const leader = (k: number) => {
  const a = satAt(k)
  return `M ${a.x + 8} ${a.y} C ${a.x + 140} ${a.y}, 1330 ${slot(k) + 20}, 1412 ${slot(k) + 20}`
}
</script>

<template><main class="slide s1">
  <Headline :page="1" eyebrow="Court-ordered freeze · life insurance" before="Stay" emphasis="line" hero />
  <p class="sub rv rv-l on" style="--d:.9s">An AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more.</p>
  <p class="who rv rv-l on" style="--d:1.1s"><b>Khadidja</b> and <b>Ewan</b><i /> Agentic Workflows</p>

  <svg class="beams" viewBox="0 0 1920 1080" aria-hidden="true">
    <path class="beam" :class="{ on: shown(1) }" pathLength="1" :d="`M 880 700 C 1000 700, 1040 600, ${SEIZED_AT.x - 14} ${SEIZED_AT.y + 8}`" />
    <path v-for="(item, k) in items" :key="item[0]" class="beam thin" :class="{ on: shown(k + 2) }" pathLength="1" :d="leader(k)" />
  </svg>

  <div class="notice rv rv-l" :class="{ on: shown(1) }">
    <div class="tag">01 / The input</div>
    <p><b>Notice N-2026-0417</b> orders the seizure of this life-insurance claim until the trial.</p>
    <div class="meta mono">CPP 706-155 · Tribunal judiciaire de Paris</div>
  </div>

  <div v-for="(item, k) in items" :key="item[0]" class="restr rv rv-r" :class="{ on: shown(k + 2) }" :style="{ top: `${slot(k)}px` }">
    <span class="n mono">{{ String(k + 1).padStart(2, '0') }}</span>
    <div><b class="mono">{{ item[0] }}</b><span>{{ item[1] }}</span></div>
  </div>

  <p class="ledger rv" :class="{ on: shown(6) }">Five lines in a ledger, each traced to its notice and its rule version.</p>
</main></template>

<style scoped>
.sub { position: absolute; left: 104px; top: 372px; width: 820px; font-size: 38px; line-height: 1.28; color: var(--ivory); }
.who { position: absolute; left: 104px; top: 560px; font-size: 26px; color: var(--muted); display: flex; align-items: center; gap: 12px; }
.who b { color: var(--ivory); font-weight: 600; }
.who i { width: 5px; height: 5px; border-radius: 50%; background: var(--muted); margin: 0 6px; }
.beams { position: absolute; inset: 0; width: 1920px; height: 1080px; pointer-events: none; z-index: 1; overflow: visible; }
.beam { fill: none; stroke: var(--blue); stroke-width: 2.4; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1; filter: drop-shadow(0 0 8px var(--blue-glow)); transition: stroke-dashoffset 1.1s cubic-bezier(.3, .6, .2, 1) .15s; }
.beam.thin { stroke-width: 1.6; opacity: .8; }
.beam.on { stroke-dashoffset: 0; }
.notice { position: absolute; left: 100px; top: 640px; width: 780px; padding: 26px 32px; border: 1px solid var(--line); border-left: 3px solid var(--blue); background: rgba(12, 14, 22, .62); }
.tag { font: 600 19px var(--sans); letter-spacing: .16em; text-transform: uppercase; color: var(--blue); margin-bottom: 12px; }
.notice p { font-size: 32px; line-height: 1.28; }
.notice b { font-weight: 650; }
.meta { margin-top: 14px; font-size: 22px; color: var(--muted); }
.restr { position: absolute; left: 1420px; display: flex; gap: 18px; align-items: flex-start; width: 450px; }
.restr .n { font-size: 20px; color: var(--blue); padding-top: 7px; }
.restr b { display: block; font-size: 30px; font-weight: 500; color: var(--ivory); }
.restr span:not(.n) { font-size: 23px; color: var(--muted); }
.ledger { position: absolute; left: 104px; top: 890px; width: 900px; font-size: 27px; color: var(--muted); }
</style>
