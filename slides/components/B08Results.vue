<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import { useCount } from './useCount'
import Headline from './Headline.vue'
import { BIG, blocks, runPos } from '../world/formations'

const { shown, print, active } = useBeat()
const s = deck.summary
const n = useCount(() => s.passed, () => active.value, () => print.value, 2.2, 0.6)
const pct = (v: number) => (v * 100).toFixed(1)
const bl = blocks(BIG)
const kindRes = s.by_kind
const fails = deck.runs.filter(r => !r.passed)
const failX = [...new Set(fails.map(r => r.id))].map(id => ({ id, n: fails.filter(r => r.id === id).length, x: runPos(fails.find(r => r.id === id)!, BIG).x }))
const lo = s.overall.ci_low * 100, hi = s.overall.ci_high * 100, pk = s.overall.pass_hat_k * 100
</script>

<template><main class="slide">
  <Headline :page="8" eyebrow="Results · 30 scenarios, 3 repeats each" before="Reliable where it " emphasis="matters" />
  <div class="num"><span class="big">{{ Math.round(n) }}</span><span class="of mono">/ {{ s.runs }} runs passed</span></div>

  <div v-for="(b, i) in bl" :key="b.kind" class="kind rv" :class="{ on: shown(1) }" :style="{ left: `${b.x0 - 20}px`, '--d': `${i * 0.12}s` }">
    <span class="tag">{{ b.kind }}</span>
    <span class="res mono">{{ kindRes[i].passed }}<small>/{{ kindRes[i].runs }}</small></span>
  </div>
  <div v-for="f in failX" :key="f.id" class="fl mono rv" :class="{ on: shown(1) }" :style="{ left: `${f.x - 34}px` }">{{ f.id }} ×{{ f.n }}</div>

  <div class="panel pk rv" :class="{ on: shown(2) }">
    <span class="tag">pass^3 · every repeat passes</span>
    <div class="line"><span class="big">{{ pct(s.overall.pass_hat_k) }}<small>%</small></span></div>
    <div class="axis"><i class="span" :style="{ left: `${lo}%`, width: `${hi - lo}%` }" /><i class="pt" :style="{ left: `${pk}%` }" /></div>
    <div class="ticks mono"><span>0</span><span>50</span><span>100 %</span></div>
    <p class="lbl">95% Wilson interval · {{ pct(s.overall.ci_low) }}% to {{ pct(s.overall.ci_high) }}%</p>
  </div>
  <div class="panel cost rv" :class="{ on: shown(3) }">
    <span class="tag">cost and speed</span>
    <p><span class="big sm">${{ s.cost_per_success.toFixed(4) }}</span><span class="lbl"> per success</span></p>
    <p class="lat mono">p50 {{ s.latency_s['50'].toFixed(1) }} s · p95 {{ s.latency_s['95'].toFixed(1) }} s</p>
  </div>
  <div class="panel err rv" :class="{ on: shown(3) }" style="--d:.2s">
    <span class="tag">the two errors that matter</span>
    <p><span class="big sm">{{ s.domain.under_blocking }}</span><span class="lbl"> under-blocking: a seizure missed</span></p>
    <p><span class="big sm">{{ s.domain.over_blocking }}</span><span class="lbl"> over-blocking: too much changed</span></p>
  </div>
</main></template>

<style scoped>
.num { position: absolute; right: 100px; top: 70px; text-align: right; }
.num .big { font-size: 230px; }
.num .of { display: block; margin-top: -8px; font-size: 25px; color: var(--muted); }
.kind { position: absolute; top: 640px; width: 280px; display: grid; gap: 4px; }
.kind .tag { color: var(--muted); font-size: 21px; }
.kind .res { font-size: 46px; font-weight: 500; letter-spacing: -.03em; } .kind .res small { font-size: .5em; color: var(--muted); }
.fl { position: absolute; top: 612px; font-size: 23px; color: var(--fail); }
.panel { top: 745px; height: 225px; padding: 22px 30px; }
.panel .tag { margin-bottom: 4px; font-size: 19px; }
.pk { left: 100px; width: 700px; } .cost { left: 830px; width: 470px; } .err { left: 1330px; width: 490px; }
.big.sm { font-size: 84px; letter-spacing: -.03em; display: inline; text-shadow: none; }
.line .big { font-size: 104px; } .line small { font-size: .5em; }
.axis { position: relative; height: 10px; margin: 6px 0 4px; border-radius: 6px; background: rgba(238, 240, 246, .1); }
.axis .span { position: absolute; top: 0; height: 10px; border-radius: 6px; background: var(--blue); box-shadow: 0 0 18px var(--blue-glow); }
.axis .pt { position: absolute; top: -7px; width: 3px; height: 24px; background: var(--ivory); }
.ticks { display: flex; justify-content: space-between; font-size: 18px; color: var(--muted); }
.lbl { font-size: 23px; color: var(--muted); }
.panel p { margin: 6px 0 0; } .panel .lbl { font-family: var(--sans); }
.lat { font-size: 26px; margin-top: 12px !important; }
</style>
