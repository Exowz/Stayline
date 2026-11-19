<script setup lang="ts">
// Our own line drawing of a balance: the law (a section sign) on one pan, the agent (a small graph) on the other.
// Drawn on slowly; shown on the opening and closing slides.
defineProps<{ on: boolean, faint?: boolean }>()
const lines = [
  'M210 296 L210 56',
  'M150 322 L270 322 M170 322 Q210 292 250 322',
  'M62 92 Q210 64 358 92',
  'M62 92 L18 224 M62 92 L106 224 M358 92 L314 224 M358 92 L402 224',
  'M6 224 Q62 276 118 224 Z M302 224 Q358 276 414 224 Z',
  'M196 296 Q210 270 224 296',
]
const nodes = [[336, 196], [358, 166], [382, 198], [358, 208]]
</script>

<template>
  <svg class="balance" :class="{ on, faint }" viewBox="0 0 420 340" aria-hidden="true">
    <path v-for="(d, i) in lines" :key="i" :d="d" pathLength="1" :style="{ transitionDelay: `${0.2 + i * 0.35}s` }" />
    <circle cx="210" cy="48" r="9" class="ring" pathLength="1" />
    <text class="sec" x="62" y="218" text-anchor="middle">§</text>
    <g transform="translate(358 192) scale(1.55) translate(-358 -192)">
      <path class="graph" d="M336 196 L358 166 L382 198 M358 166 L358 208 M336 196 L358 208 L382 198" pathLength="1" />
      <circle v-for="p in nodes" :key="p.join()" :cx="p[0]" :cy="p[1]" r="4.5" class="node" />
    </g>
  </svg>
</template>

<style scoped>
.balance { position: absolute; left: 1320px; top: 645px; width: 520px; height: 420px; pointer-events: none; opacity: .66; transition: opacity 1s; }
.balance.faint { opacity: .36; }
.balance path, .balance .ring { fill: none; stroke: rgba(200, 210, 255, .85); stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; stroke-dashoffset: 1; transition: stroke-dashoffset 2.2s cubic-bezier(.3, .6, .2, 1); }
.balance.on path, .balance.on .ring { stroke-dashoffset: 0; }
.balance .graph { transition-delay: 2.4s; stroke-width: 1.8; }
.sec { font: 400 92px 'Instrument Serif', serif; fill: rgba(200, 210, 255, .9); opacity: 0; transition: opacity 1.4s 2.2s; }
.node { fill: rgba(200, 210, 255, .95); opacity: 0; transition: opacity 1.4s 2.8s; }
.balance.on .sec, .balance.on .node { opacity: 1; }
</style>
