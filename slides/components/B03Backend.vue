<script setup lang="ts">
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { DB, DB_Y } from '../world/formations'

const { shown } = useBeat()
const refusals = ['stale version', 'duplicate notice', 'second seizure']
</script>

<template><main class="slide">
  <Headline :page="3" eyebrow="The backend" before="Two servers, one " emphasis="guarded" after=" database" />

  <div class="srv one rv rv-l" :class="{ on: shown(1) }">
    <span class="tag">MCP server</span>
    <h3 class="mono">justice_reference</h3>
    <b class="ro">read only</b>
    <ul><li>the notice</li><li>who may order a seizure</li><li>the rule in force on a date</li></ul>
  </div>
  <div class="srv two rv rv-r" :class="{ on: shown(1) }">
    <span class="tag">MCP server</span>
    <h3 class="mono">insurer_contracts</h3>
    <b class="ro">reads contracts, and two dangerous writes</b>
    <div class="chips"><span class="mono danger">apply_seizure</span><span class="mono danger">execute_operation</span></div>
  </div>

  <div class="rules rv" :class="{ on: shown(2) }">
    <span class="tag">Inside every write, in one transaction</span>
    <div class="row"><span v-for="(r, i) in refusals" :key="r" class="ref mono" :style="{ '--d': `${0.25 + i * 0.22}s` }">✕ {{ r }}</span></div>
    <p class="ok">The server refuses, and nothing changes.</p>
  </div>

  <svg class="beams" viewBox="0 0 1920 1080" aria-hidden="true">
    <path class="draw soft" :class="{ on: shown(1) }" pathLength="1" d="M 430 640 L 430 770 L 760 770" />
    <path class="draw" :class="{ on: shown(1) }" pathLength="1" d="M 1340 720 L 1340 770 L 1620 770" />
    <path class="draw soft" :class="{ on: shown(1) }" pathLength="1" d="M 330 770 L 1620 770" />
    <path v-for="d in DB" :key="d.name" class="draw soft" :class="{ on: shown(1) }" pathLength="1" :d="`M ${d.x} 770 L ${d.x} 826`" />
  </svg>

  <div v-for="d in DB" :key="d.name" class="dbl mono" :style="{ left: `${d.x - 120}px`, top: `${DB_Y + 66}px` }">{{ d.name }}</div>
  <p class="seed mono">SQLite<br>reset to a seed<br>before every test</p>
</main></template>

<style scoped>
.srv { position: absolute; top: 250px; padding: 24px 30px; border: 1px solid var(--line); border-top: 3px solid var(--blue); background: rgba(12, 14, 22, .62); }
.srv.one { left: 100px; width: 660px; border-top-color: var(--muted); }
.srv.two { left: 860px; width: 960px; }
.srv .tag { display: block; margin-bottom: 8px; font-size: 18px; } .srv.one .tag { color: var(--muted); }
.srv h3 { font-size: 44px; font-weight: 500; letter-spacing: -.02em; }
.ro { display: block; margin: 6px 0 14px; font-weight: 500; font-size: 25px; color: var(--muted); }
ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; justify-items: start; }
li { font-size: 24px; padding: 6px 16px; border: 1px solid var(--line); border-radius: 99px; }
.chips { display: flex; gap: 14px; }
.danger { font-size: 25px; padding: 8px 18px; border-radius: 6px; color: var(--fail); border: 1px solid rgba(255, 92, 98, .55); background: rgba(255, 92, 98, .08); }
.rules { position: absolute; left: 860px; top: 520px; width: 960px; }
.rules .tag { display: block; margin-bottom: 12px; }
.row { display: flex; gap: 14px; }
.ref { font-size: 24px; padding: 9px 20px; color: var(--fail); border: 1px solid rgba(255, 92, 98, .5); background: rgba(255, 92, 98, .08); opacity: 0; transform: translateX(-30px); transition: all .7s cubic-bezier(.2, .7, .2, 1); transition-delay: var(--d); }
.rules.on .ref { opacity: 1; transform: none; }
.ok { margin-top: 14px; font-size: 27px; }
.dbl { position: absolute; width: 240px; text-align: center; font-size: 23px; color: var(--muted); }
.seed { position: absolute; left: 100px; top: 730px; font-size: 20px; line-height: 1.35; color: var(--muted); letter-spacing: .04em; }
</style>
