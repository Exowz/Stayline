<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { LEFT, RIGHT } from '../world/formations'

const { shown } = useBeat()
const a = deck.summary, m = deck.mistral_summary
const bonus = [
  ['01', 'A second model', 'Mistral Small is about twice as fast and cheaper, but passes 67% against 98%. It obeyed an injected instruction, and our server refused it.'],
  ['02', 'A failure injected into a tool', 'The server commits, then answers with a timeout. The agent reads back instead of retrying blindly.'],
  ['03', 'The interface you saw', 'The plan, the tool calls and the approval step.'],
]
</script>

<template><main class="slide">
  <div class="stage1" :class="{ gone: shown(2) }">
    <Headline :page="10" eyebrow="Bonuses" before="Three " emphasis="bonuses" />

    <div v-for="(b, i) in bonus" :key="b[0]" class="bn" :style="{ top: `${250 + i * 78}px` }">
      <span class="mono n">{{ b[0] }}</span><b class="serif">{{ b[1] }}</b>
      <span class="d rv" :class="{ on: shown(1) }" :style="{ '--d': `${i * 0.15}s` }">{{ b[2] }}</span>
    </div>

    <div class="cmp rv" :class="{ on: shown(1) }">
      <div class="side" :style="{ left: `${LEFT.x0}px` }"><span class="tag">deepseek-v4.1-flash · main</span><span class="num">{{ a.overall.passed }}<small>/90</small></span></div>
      <div class="side" :style="{ left: `${RIGHT.x0}px` }"><span class="tag mute">mistral-small</span><span class="num mu">{{ m.overall.passed }}<small>/90</small></span></div>
      <div class="st mono" :style="{ left: `${LEFT.x0}px` }">pass^3 {{ (a.overall.pass_hat_k * 100).toFixed(1) }}% · ${{ a.cost_per_success.toFixed(4) }} per success · p50 {{ a.latency_s['50'].toFixed(1) }} s</div>
      <div class="st mono" :style="{ left: `${RIGHT.x0}px` }">pass^3 {{ (m.overall.pass_hat_k * 100).toFixed(1) }}% · ${{ m.cost_per_success.toFixed(4) }} per success · p50 {{ m.latency_s['50'].toFixed(1) }} s</div>
    </div>
    <p class="lim rv" :class="{ on: shown(1) }" style="--d:.5s">Limits: a mock feed, one operator at a time, an always-yes approver.</p>
  </div>

  <div class="fin" :class="{ on: shown(2) }">
    <h2 class="serif">Stay<em>line</em></h2>
    <p>An AI agent that applies a court-ordered freeze to the right life-insurance contract, and nothing more.</p>
    <span class="tag">Thank you</span>
  </div>
</main></template>

<style scoped>
.stage1 { position: absolute; inset: 0; transition: opacity .6s; }
.stage1.gone { opacity: 0 !important; pointer-events: none; }
.bn { position: absolute; left: 100px; right: 100px; display: grid; grid-template-columns: 70px 520px 1fr; gap: 20px; align-items: baseline; }
.bn .n { color: var(--blue); font-size: 22px; } .bn b { font-size: 46px; font-weight: 400; letter-spacing: -.02em; }
.bn .d { font-size: 22px; line-height: 1.3; color: var(--muted); }
.cmp { position: absolute; inset: 0; }
.side { position: absolute; top: 490px; display: grid; gap: 4px; } .side .tag.mute { color: var(--muted); }
.num { font: 400 72px/1 var(--serif); letter-spacing: -.03em; } .num small { font-size: .45em; color: var(--muted); } .num.mu { color: var(--muted); }
.st { position: absolute; top: 712px; font-size: 20px; color: var(--muted); }
.lim { position: absolute; left: 100px; top: 920px; font-size: 23px; color: var(--muted); }
.fin { position: absolute; inset: 0; display: grid; align-content: center; justify-items: center; gap: 24px; text-align: center; opacity: 0; transform: scale(.96); transition: opacity 1s .5s, transform 1.4s cubic-bezier(.2, .7, .2, 1) .4s; }
.fin.on { opacity: 1; transform: none; }
.fin h2 { font-size: 300px; line-height: .85; letter-spacing: -.05em; text-shadow: 0 0 120px rgba(122, 146, 255, .55); } .fin em { color: var(--blue); }
.fin p { max-width: 1100px; font-size: 38px; line-height: 1.25; } .fin .tag { margin-top: 12px; font-size: 20px; color: var(--muted); }
</style>
