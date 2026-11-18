<script setup lang="ts">
import { useBeat } from './useBeat'
import Kin from './Kin.vue'
import Island from './Island.vue'
const { active, shown } = useBeat()
const justice = ['get_notice', 'find_notices', 'resolve_issuing_authority', 'get_rule']
const insurer = ['find_contracts', 'get_contract', 'get_restriction_ledger', 'find_operation_requests']
</script>

<template><main class="slide beat-three">
  <div class="eyebrow">03 / Backend and servers</div>
  <Kin text="The server *checks* again" :on="active" />
  <div class="servers section reveal" :class="{ on: shown(1) }">
    <Island><h2 class="mono">justice_reference</h2><p>Read only</p><div class="tools"><code v-for="tool in justice" :key="tool">{{ tool }}</code></div></Island>
    <Island><h2 class="mono">insurer_contracts</h2><p>Reads, and two dangerous writes</p><div class="tools"><code v-for="tool in insurer" :key="tool">{{ tool }}</code><code class="danger">apply_seizure</code><code class="danger">execute_operation</code></div></Island>
  </div>
  <div class="lower">
    <Island class="database"><h2>SQLite backend</h2><p>Reset to a seed before every test</p></Island>
    <Island class="guard reveal" :class="{ on: shown(2) }"><strong>Every rule is checked again inside the write, in one transaction.</strong><div><span class="chip">stale version</span><span class="chip">duplicate notice</span><span class="chip">second seizure</span></div><p>Each one is refused. Nothing changes.</p></Island>
  </div>
</main></template>
<style scoped>
.servers { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.servers .island { padding: 26px 30px; }
.servers h2 { font-size: 36px; margin-bottom: 4px; }
.servers p { font-size: 30px; color: var(--ink-muted); }
.tools { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 10px; }
.tools code { font-size: 27px; border-radius: 10px; padding: 8px 13px; background: color-mix(in oklab, var(--second) 7%, var(--white)); }
.tools code.danger { background: var(--loud-tint); color: var(--loud-dark); font-weight: 650; box-shadow: inset 0 0 0 1.5px color-mix(in oklab, var(--loud) 50%, var(--white)); }
.lower { display: grid; grid-template-columns: 0.75fr 1.5fr; gap: 24px; margin-top: 24px; }
.database { display: flex; flex-direction: column; justify-content: center; }
.database h2 { font-size: 36px; margin-bottom: 6px; }
.database p { font-size: 30px; color: var(--ink-muted); }
.guard { padding: 24px 30px; font-size: 32px; }
.guard > div { display: flex; flex-wrap: wrap; gap: 12px; margin: 14px 0 10px; }
.guard .chip { font-size: 28px; padding: 8px 18px; }
.guard p { font-size: 30px; color: var(--ink-muted); }
</style>
