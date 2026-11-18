<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNav } from '@slidev/client'
import { World } from './world/engine'
import { N } from './world/formations'
import { formationFor, phase } from './world/pages'

const nav = useNav()
const canvas = ref<HTMLCanvasElement | null>(null)
let world: World | undefined
let lastPage = 0

function print() { return nav.isPrintMode.value || location.search.includes('export') }
function update() {
  if (!world) return
  const turned = nav.currentPage.value !== lastPage
  lastPage = nav.currentPage.value
  world.go(formationFor(nav.currentPage.value, nav.clicks.value, phase.value), print(), turned)
}

onMounted(() => {
  if (!canvas.value) return
  world = new World(canvas.value, N)
  world.setStill(window.matchMedia('(prefers-reduced-motion: reduce)').matches || print())
  world.resize()
  update()
  world.start()
  window.addEventListener('resize', () => world?.resize())
})
onBeforeUnmount(() => world?.stop())
watch(() => [nav.currentPage.value, nav.clicks.value, phase.value], update)
</script>

<template>
  <div class="deck-bg" aria-hidden="true" />
  <canvas ref="canvas" class="world-canvas" aria-hidden="true" />
  <div class="deck-grain" aria-hidden="true" />
</template>
