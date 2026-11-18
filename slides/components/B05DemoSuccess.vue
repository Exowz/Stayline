<script setup lang="ts">
import { computed } from 'vue'
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import { useCount } from './useCount'
import Headline from './Headline.vue'

const { shown, print, click } = useBeat()
const moments = ['The run starts and only reads', 'An approval card asks a human', 'Approve, write, read back', 'The proof, from trace and database']
const shot = computed(() => Math.max(1, Math.min(4, click.value)))
const trace = deck.traces.s01
const tokens = useCount(() => trace.total_tokens_in + trace.total_tokens_out, () => shown(4), () => print.value, 1.8)
const cost = useCount(() => trace.total_cost_usd, () => shown(4), () => print.value, 1.8)
const secs = useCount(() => trace.total_ms / 1000, () => shown(4), () => print.value, 1.8)
</script>

<template><main class="slide">
  <Headline :page="5" eyebrow="Live demo · success" before="A freeze with " emphasis="proof" />
  <div class="scn mono rv rv-r on" style="--d:.9s"><b>s01</b> · a clean seizure notice, on the base seed</div>

  <div class="frame rv rv-s on" style="--d:.8s">
    <div class="chrome"><i /><i /><i /><span class="mono">localhost:8000 · Run</span></div>
    <div class="shots"><img v-for="n in 4" :key="n" :class="{ cur: shot === n }" :src="`/media/demo-${n}.png`" :alt="`Live demo, moment ${n}`" /></div>
  </div>

  <ol class="steps">
    <li v-for="(m, i) in moments" :key="m" class="rv rv-r" :class="{ on: shown(i + 1), cur: click === i + 1 }" :style="{ '--d': '.1s' }">
      <span class="dot" /><span class="t">{{ m }}</span>
    </li>
  </ol>

  <div class="proof rv" :class="{ on: shown(4) }">
    <div><span class="big">{{ trace.model_calls }}</span><span class="lbl">model calls</span></div>
    <div><span class="big">{{ trace.tool_calls }}</span><span class="lbl">tool calls</span></div>
    <div><span class="big">{{ Math.round(tokens).toLocaleString('en-US') }}</span><span class="lbl">tokens</span></div>
    <div><span class="big">${{ cost.toFixed(4) }}</span><span class="lbl">cost</span></div>
    <div><span class="big">{{ secs.toFixed(1) }}<small> s</small></span><span class="lbl">latency</span></div>
  </div>
  <p class="trace-cap mono rv" :class="{ on: shown(4) }">the 17 spans of this run, read from the trace</p>
</main></template>

<style scoped>
.scn { position: absolute; right: 100px; top: 112px; font-size: 24px; color: var(--muted); }
.scn b { color: var(--blue); font-weight: 500; }
.frame { position: absolute; left: 100px; top: 250px; width: 980px; border: 1px solid rgba(238, 240, 246, .2); border-radius: 12px; overflow: hidden; background: #0d0f16;
  box-shadow: 0 0 0 1px rgba(122, 146, 255, .12), 0 40px 120px -30px rgba(70, 92, 255, .45); }
.chrome { height: 40px; display: flex; align-items: center; gap: 8px; padding: 0 16px; border-bottom: 1px solid var(--line); background: rgba(238, 240, 246, .04); }
.chrome i { width: 11px; height: 11px; border-radius: 50%; background: rgba(238, 240, 246, .22); }
.chrome span { margin-left: 18px; font-size: 18px; color: var(--muted); }
.shots { position: relative; aspect-ratio: 1024 / 640; }
.shots img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transform: scale(1.025); transition: opacity .7s ease, transform 1.1s cubic-bezier(.2, .7, .2, 1); }
.shots img.cur { opacity: 1; transform: none; }
.steps { position: absolute; left: 1290px; top: 262px; width: 540px; margin: 0; padding: 0; list-style: none; display: grid; gap: 30px; }
.steps li { display: flex; gap: 20px; align-items: center; font-size: 30px; line-height: 1.2; color: var(--muted); }
.steps li.cur { color: var(--ivory); }
.dot { width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--blue); flex: none; position: relative; }
.steps li.on .dot { background: var(--blue); box-shadow: 0 0 18px var(--blue-glow); }
.steps li.cur .dot::after { content: ''; position: absolute; inset: -9px; border-radius: 50%; border: 1.5px solid var(--blue); animation: ping 1.6s ease-out infinite; }
@keyframes ping { from { transform: scale(.6); opacity: 1; } to { transform: scale(1.5); opacity: 0; } }
.proof { position: absolute; left: 1290px; top: 560px; width: 540px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px 24px; }
.proof .big { display: block; font-size: 78px; letter-spacing: -.03em; }
.proof .lbl { display: block; margin-top: 4px; font-size: 20px; }
.trace-cap { position: absolute; left: 104px; top: 912px; font-size: 19px; color: var(--muted); }
</style>
