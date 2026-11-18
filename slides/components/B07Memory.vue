<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import gsap from 'gsap'
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { phase } from '../world/pages'
import { ORION } from '../world/formations'

const { shown, print, click } = useBeat()
let call: gsap.core.Tween | undefined
watch(() => [click.value, print.value], () => {
  call?.kill()
  if (print.value) { phase.value = 'with'; return }
  if (click.value >= 1) {
    phase.value = 'without'
    call = gsap.delayedCall(3.6, () => { phase.value = 'with' })
  } else phase.value = 'none'
}, { immediate: true })
onBeforeUnmount(() => { call?.kill(); phase.value = 'none' })
</script>

<template><main class="slide">
  <Headline :page="7" eyebrow="Long-term memory" before="A memory that " emphasis="changes" after=" the next run" />

  <div class="panel one rv rv-l on" style="--d:1s">
    <span class="tag">Run 1 · the operator tells the agent</span>
    <p class="q">“Orion is instruction 2026/00417 at the Paris court.”</p>
    <p class="st mono">stored → alias <b>orion</b> = 2026/00417 <span>· per operator</span></p>
  </div>

  <div class="panel two rv rv-l" :class="{ on: shown(1) }">
    <span class="tag">Run 2 · a brand new run</span>
    <p class="q">“A request came in on the Orion contract, process it.”</p>
    <div class="out" :class="{ 'is-with': phase === 'with', 'is-without': phase === 'without' }">
      <p class="no"><b>Without memory</b> the request is ambiguous. The agent asks, and changes nothing.</p>
      <p class="yes"><b>With memory</b> the alias finds the seized contract, and the agent handles the request.</p>
    </div>
  </div>
  <p class="hint rv" :class="{ on: shown(1) }">The alias is only a hint. The current records still decide, and text from a tool can never write to memory.</p>

  <div class="lab la rv" :class="{ on: shown(1) }" :style="{ left: `${ORION.a.x + 20}px`, top: `${ORION.a.y - 74}px` }"><b>seized contract</b><span>instruction 2026/00417</span></div>
  <div class="lab lb rv" :class="{ on: shown(1) }" :style="{ left: `${ORION.b.x + 24}px`, top: `${ORION.b.y + 12}px` }"><b>another candidate</b></div>
  <div class="lab lq rv" :class="{ on: shown(1) }" :style="{ left: `${ORION.q.x - 120}px`, top: `${ORION.q.y + 28}px` }"><b>“the Orion contract”</b></div>
</main></template>

<style scoped>
.panel { left: 100px; width: 780px; }
.one { top: 290px; }
.two { top: 520px; }
.q { font: 400 40px/1.15 var(--serif); letter-spacing: -.01em; }
.st { margin-top: 14px; font-size: 22px; color: var(--muted); } .st b { color: var(--blue); font-weight: 500; }
.out { position: relative; margin-top: 18px; min-height: 120px; }
.out p { position: absolute; inset: 0 auto auto 0; width: 100%; font-size: 26px; line-height: 1.3; transition: opacity .7s, transform .7s; }
.out b { font-weight: 650; }
.out .no { color: var(--muted); } .out .yes { color: var(--ivory); }
.out .yes b { color: var(--blue); }
.out .no, .out .yes { opacity: 0; transform: translateY(10px); }
.out.is-without .no, .out.is-with .yes { opacity: 1; transform: none; }
.hint { position: absolute; left: 100px; top: 900px; width: 1700px; font-size: 23px; color: var(--muted); }
.lab { position: absolute; z-index: 2; display: grid; font-size: 22px; color: var(--muted); }
.lab b { font: 500 23px var(--mono); color: var(--blue); }
.lab.lb b, .lab.lq b { color: var(--ivory); }
</style>
