<script setup lang="ts">
import { useBeat } from './useBeat'
import Headline from './Headline.vue'
import { CONTRACT, INNOCENT_AT } from '../world/formations'

const { shown } = useBeat()
</script>

<template><main class="slide">
  <Headline :page="2" eyebrow="The risk" before="Two " emphasis="dangerous" after=" buttons" />

  <div class="blk blk-a rv rv-l" :class="{ on: shown(1) }">
    <span class="tag">01 / Block a contract</span>
    <p class="stmt">Pick the wrong one and an <em>innocent</em> client is frozen.</p>
  </div>
  <div class="blk blk-b rv rv-l" :class="{ on: shown(2) }">
    <span class="tag">02 / Pay out a rachat or an advance</span>
    <p class="stmt">On a seized contract, that money must <em>not leave</em>.</p>
  </div>

  <div class="lab seized rv" :class="{ on: true }" :style="{ left: `${CONTRACT.x - 130}px`, top: `${CONTRACT.y - 100}px` }">
    <b>seized contract</b>
  </div>
  <div class="lab bad rv" :class="{ on: shown(1) }" :style="{ left: `${INNOCENT_AT.x - 120}px`, top: `${INNOCENT_AT.y + 52}px` }">
    <b>frozen by mistake</b><span>an innocent client</span>
  </div>
  <svg class="beams" viewBox="0 0 1920 1080" aria-hidden="true">
    <path class="draw red" :class="{ on: shown(1) }" pathLength="1" :d="`M ${INNOCENT_AT.x} ${INNOCENT_AT.y + 38} L ${INNOCENT_AT.x} ${INNOCENT_AT.y + 62}`" />
    <path class="wall" :class="{ on: shown(2) && !shown(3) }" d="M 1790 400 L 1790 700" />
  </svg>
  <div class="lab out rv" :class="{ on: shown(2) && !shown(3) }" style="left: 1500px; top: 350px"><b>money that must not leave</b></div>

  <div class="gauge rv" :class="{ on: shown(3) }">
    <div class="track">
      <div class="zone bad"><b>Blocks too little</b><span>fails</span></div>
      <div class="zone good"><b>Exactly the effects the law lists</b><span>passes</span></div>
      <div class="zone bad"><b>Blocks too much</b><span>fails</span></div>
    </div>
    <p class="cap">The grader reads the final state of the database, in both directions. <span class="mono">Crim. 30 Oct 2012, n° 12-84.961</span></p>
  </div>
</main></template>

<style scoped>
.blk { position: absolute; left: 100px; width: 780px; }
.blk .tag { display: block; margin-bottom: 14px; }
.blk-a { top: 300px; }
.blk-b { top: 500px; }
.lab { position: absolute; z-index: 2; font-size: 24px; color: var(--muted); display: grid; gap: 2px; }
.lab b { font: 500 24px var(--mono); color: var(--blue); }
.lab.bad b { color: var(--fail); }
.lab.out b { color: var(--fail); font-size: 23px; }
.wall { stroke: var(--fail); stroke-width: 3; stroke-dasharray: 8 10; opacity: 0; filter: drop-shadow(0 0 8px rgba(255, 92, 98, .5)); transition: opacity .6s .5s; }
.wall.on { opacity: .9; }
.gauge { position: absolute; left: 100px; right: 100px; top: 765px; }
.track { display: grid; grid-template-columns: 1fr 1.7fr 1fr; gap: 6px; }
.zone { height: 108px; display: flex; flex-direction: column; justify-content: center; padding: 0 26px; border: 1px solid var(--line); background: rgba(12, 14, 22, .55); }
.zone b { font: 500 27px var(--sans); } .zone span { font: 500 21px var(--mono); letter-spacing: .08em; text-transform: uppercase; }
.zone.bad { border-color: rgba(255, 92, 98, .55); } .zone.bad span { color: var(--fail); }
.zone.good { border-color: rgba(122, 146, 255, .7); background: rgba(70, 92, 255, .16); box-shadow: 0 0 60px rgba(122, 146, 255, .2) inset; } .zone.good span { color: var(--blue); }
.cap { margin-top: 18px; font-size: 25px; color: var(--muted); }
.cap .mono { color: var(--ivory); margin-left: 10px; font-size: 22px; }
</style>
