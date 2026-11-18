<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import { useCount } from './useCount'
import Headline from './Headline.vue'
import { BIG, runPos } from '../world/formations'

const { shown, print, click, active } = useBeat()
const b = deck.baseline1_summary
const a = deck.summary
const n = useCount(() => (click.value >= 2 ? a.passed : b.passed), () => active.value, () => print.value, 1.4, 0.5)
const imp = (x: typeof a) => x.by_kind.find(k => k.kind === 'impossible')!
const failIds = [...new Set(deck.baseline1_runs.filter(r => !r.passed).map(r => r.id))]
const failX = failIds.map(id => ({ id, x: runPos(deck.baseline1_runs.find(r => r.id === id)!, BIG).x, kept: deck.runs.some(r => r.id === id && !r.passed) }))
const changes = ['The code checks the contract can take a seizure before any card is shown.', 'A larger reply budget.', 'An empty run ends as an error, not done.', 'Two generic sentences in the prompt.']
</script>

<template><main class="slide">
  <Headline :page="9" eyebrow="Error analysis" before="What " emphasis="failed" after=", and why" />
  <div class="num"><span class="big" :class="{ fail: click < 2 }">{{ Math.round(n) }}</span><span class="of mono">/ 90 · {{ click >= 2 ? 'after the fixes' : 'first full run' }}</span></div>

  <div v-for="f in failX" :key="f.id" class="fl mono" :class="{ gone: click >= 2 && !f.kept }" :style="{ left: `${f.x - 22}px` }">{{ f.id }}</div>
  <p class="every mono rv rv-l on" style="--d:1.4s">five scenarios failed on every repeat, so each had a cause</p>

  <div class="panel fail c1 rv" :class="{ on: shown(1) }">
    <span class="tag">What failed · s20</span>
    <p>A deceased subscriber. The agent showed a human an approval card for a seizure the server then had to refuse.</p>
    <p class="strong">The first wrong step is the card itself.</p>
  </div>
  <div class="panel c2 rv" :class="{ on: shown(2) }">
    <span class="tag">What we changed</span>
    <ul><li v-for="(c, i) in changes" :key="i">{{ c }}</li></ul>
  </div>
  <div class="panel c3 rv" :class="{ on: shown(3) }">
    <span class="tag">Measured again, same 30 scenarios</span>
    <p><span class="big sm">{{ imp(b).passed }}<small> → </small>{{ imp(a).passed }}</span><span class="lbl"> of 15 impossible</span></p>
    <p class="rem">What remains: s14 still fails 2 in 3. Two prompt sentences were written after seeing those failures, so it is not a fair test.</p>
  </div>
</main></template>

<style scoped>
.num { position: absolute; right: 100px; top: 70px; text-align: right; }
.num .big { font-size: 230px; }
.num .of { display: block; margin-top: -8px; font-size: 25px; color: var(--muted); }
.fl { position: absolute; top: 612px; font-size: 20px; color: var(--fail); transition: opacity .8s .6s; }
.fl.gone { opacity: 0; }
.every { position: absolute; left: 175px; top: 690px; font-size: 21px; color: var(--muted); }
.panel { top: 740px; height: 235px; padding: 20px 26px; }
.panel .tag { margin-bottom: 8px; font-size: 17px; }
.panel p { font-size: 23px; line-height: 1.28; color: var(--ivory); margin: 0; }
.strong { margin-top: 8px !important; font-weight: 650; }
.c1 { left: 100px; width: 560px; } .c2 { left: 690px; width: 560px; } .c3 { left: 1280px; width: 540px; }
ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 7px; } li { font-size: 22px; line-height: 1.25; padding-left: 20px; position: relative; }
li::before { content: ''; position: absolute; left: 0; top: .6em; width: 8px; height: 8px; border-radius: 50%; background: var(--blue); box-shadow: 0 0 10px var(--blue-glow); }
.big.sm { font-size: 70px; display: inline; text-shadow: none; letter-spacing: -.03em; } .big.sm small { font-size: .55em; color: var(--blue); }
.lbl { font-size: 22px; color: var(--muted); }
.rem { margin-top: 8px !important; font-size: 20px !important; color: var(--muted) !important; }
</style>
