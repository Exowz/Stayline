<script setup lang="ts">
import deck from '../generated/deck.json'
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const before = deck.baseline1_summary
const after = deck.summary
const kindBefore = before.by_kind.find(kind => kind.kind === 'impossible')!
const kindAfter = after.by_kind.find(kind => kind.kind === 'impossible')!
const chain = ['Deceased subscriber', 'Approval card shown', 'Server refuses', 'Run fails']
const fixes = ['Check before the card', 'Reply budget is a setting', 'Empty run is error, not done', 'Two generic prompt sentences']
</script>

<template><main class="slide beat-nine">
  <div class="eyebrow">09 / Error analysis</div>
  <Kin text="Fix the *first* wrong step" :on="active" />
  <div class="chain reveal" :class="{ on: shown(1) && !shown(3) }"><Island v-for="(step, index) in chain" :key="step" :class="{ firstwrong: index === 1 }"><span class="mono">0{{ index + 1 }}</span><strong>{{ step }}</strong></Island></div>
  <div class="fixes reveal" :class="{ on: shown(2) && !shown(3) }"><span v-for="fix in fixes" :key="fix" class="chip">✓ {{ fix }}</span></div>
  <div class="before-after reveal" :class="{ on: shown(3) }">
    <Island><span>First full run</span><strong class="big mono">{{ before.passed }} / {{ before.runs }}</strong><p>Impossible: {{ kindBefore.passed }} / {{ kindBefore.runs }}</p></Island>
    <div class="arrow">→</div>
    <Island><span>Final run</span><strong class="big mono">{{ after.passed }} / {{ after.runs }}</strong><p>Impossible: {{ kindAfter.passed }} / {{ kindAfter.runs }}</p></Island>
  </div>
  <Island class="honest reveal" :class="{ on: shown(3) }"><p>s14 still fails {{ deck.runs.filter(run => run.id === 's14' && !run.passed).length }} of {{ deck.runs.filter(run => run.id === 's14').length }}. Two prompt sentences were written after the failures, so they are not a fair test.</p></Island>
</main></template>
<style scoped>
.chain { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 65px; }
.chain .island { min-height: 180px; display: flex; flex-direction: column; gap: 15px; font-size: 29px; }
.chain .firstwrong { box-shadow: inset 0 0 0 4px var(--second); }
.fixes { display: flex; flex-wrap: wrap; gap: 15px; margin-top: 45px; }
.fixes .chip { font-size: 27px; }
.before-after { position: absolute; top: 640px; left: 176px; right: 176px; display: flex; gap: 22px; align-items: center; }
.before-after .island { flex: 1; display: grid; gap: 6px; padding: 16px 28px; }
.before-after .arrow { font-size: 60px; }
.before-after span { font-size: 28px; }
.before-after p { font-size: 29px; }
.score-bar { height: 12px; border-radius: 10px; background: color-mix(in oklab, var(--second) 9%, transparent); }
.score-bar i { display: block; height: 100%; border-radius: inherit; background: var(--second); }
.honest { position: absolute; left: 176px; right: 176px; top: 862px; padding: 14px 25px; }
.honest p { font-size: 28px; }
</style>
