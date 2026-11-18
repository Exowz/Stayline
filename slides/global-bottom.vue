<script setup lang="ts">
import { watch } from 'vue'
import { useNav } from '@slidev/client'
import DotWorld from './components/DotWorld.vue'

const nav = useNav()
let timer = 0
watch(() => nav.currentPage.value, () => {
  document.documentElement.style.setProperty('--base', '.45s')
  clearTimeout(timer)
  timer = window.setTimeout(() => document.documentElement.style.setProperty('--base', '0s'), 1700)
})
</script>

<template>
  <div class="deck-backdrop" aria-hidden="true" />
  <div class="slide-pane" aria-hidden="true" />
  <DotWorld />
</template>
