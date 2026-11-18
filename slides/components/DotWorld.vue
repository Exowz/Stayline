<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNav } from '@slidev/client'
import { worldFor } from '../world/pages'
import { N, targets, afterTargets, type Target } from '../world/states'

const nav = useNav()
const canvas = ref<HTMLCanvasElement | null>(null)
const current: Target[] = targets('field')
let from = targets('field')
let to = targets('field')
let start = 0
let frame = 0
let ctx: CanvasRenderingContext2D | null = null
let scale = 1
let state = worldFor(1, 0)
let reduced = false
let afterTimer = 0
const mix = (a: number, b: number, p: number) => a + (b - a) * p

function resize() {
  if (!canvas.value) return
  const width = canvas.value.getBoundingClientRect().width || 1920
  const backing = Math.round(width * (window.devicePixelRatio || 1))
  canvas.value.width = backing
  canvas.value.height = Math.round(backing * 1080 / 1920)
  scale = backing / 1920
  ctx = canvas.value.getContext('2d')
}

function apply(next: Target[], instant = false) {
  for (let i = 0; i < N; i++) from[i] = { ...current[i] }
  to = next
  start = instant || reduced || nav.isPrintMode.value ? -10000 : performance.now()
  if (start < 0) step(1)
}

function step(p: number) {
  const ease = 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3)
  for (let i = 0; i < N; i++) {
    const a = from[i], b = to[i], dot = current[i]
    dot.x = mix(a.x, b.x, ease)
    dot.y = mix(a.y, b.y, ease)
    dot.radius = mix(a.radius, b.radius, ease)
    dot.alpha = mix(a.alpha, b.alpha, ease)
    dot.tone = ease > .5 ? b.tone : a.tone
    dot.fail = ease > .5 ? b.fail : a.fail
  }
}

function draw(now: number) {
  frame = requestAnimationFrame(draw)
  if (!ctx) return
  step((now - start) / 1200)
  ctx.setTransform(scale, 0, 0, scale, 0, 0)
  ctx.clearRect(0, 0, 1920, 1080)
  const drifting = state.name === 'field' || state.name === 'target'
  for (let i = 0; i < N; i++) {
    const dot = current[i]
    if (dot.alpha < .01) continue
    const wave = drifting && !reduced ? Math.sin(now * .00038 + i * 2.4) * 6 : 0
    const x = dot.x + wave, y = dot.y + wave * .6
    ctx.beginPath()
    ctx.arc(x, y, dot.radius, 0, Math.PI * 2)
    ctx.globalAlpha = dot.alpha
    ctx.fillStyle = dot.tone === 'blue' ? '#3548e1' : dot.tone === 'fail' ? '#c23445' : '#232328'
    ctx.fill()
    if (dot.fail) {
      ctx.fillStyle = 'rgb(130,30,42)'
      ctx.globalAlpha = 1
      ctx.font = '600 26px "Onest Variable"'
      ctx.textAlign = 'center'
      ctx.fillText('fail', x, y + 34)
    }
    if (state.name === 'target' && i === 0) {
      ctx.beginPath(); ctx.arc(x, y, dot.radius + 16, 0, Math.PI * 2)
      ctx.globalAlpha = .8; ctx.strokeStyle = '#3548e1'; ctx.lineWidth = 3; ctx.stroke()
      for (let j = 0; j < state.satellites; j++) {
        const angle = -2 + j * .76
        ctx.beginPath(); ctx.arc(x + Math.cos(angle) * 67, y + Math.sin(angle) * 67, 5, 0, Math.PI * 2)
        ctx.globalAlpha = 1; ctx.fillStyle = '#3548e1'; ctx.fill()
      }
    }
  }
  ctx.globalAlpha = 1
}

function update() {
  window.clearTimeout(afterTimer)
  state = worldFor(nav.currentPage.value, nav.clicks.value)
  apply(targets(state.name))
  if (state.name === 'before-after' && !reduced && !nav.isPrintMode.value)
    afterTimer = window.setTimeout(() => apply(afterTargets()), 1000)
  else if (state.name === 'before-after') apply(afterTargets(), true)
}

onMounted(() => {
  reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resize(); update(); frame = requestAnimationFrame(draw)
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame); window.clearTimeout(afterTimer)
  window.removeEventListener('resize', resize)
})
watch(() => [nav.currentPage.value, nav.clicks.value], update)
</script>

<template><canvas ref="canvas" class="world-canvas" aria-hidden="true" /></template>
