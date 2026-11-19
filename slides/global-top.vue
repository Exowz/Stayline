<script setup lang="ts">
import { computed } from 'vue'
import { useNav } from '@slidev/client'
import { MAIN_PAGES, pageInfo } from './world/pages'

const nav = useNav()
const info = computed(() => pageInfo(nav.currentPage.value))
const segments = Array.from({ length: MAIN_PAGES }, (_, i) => i + 1)
const blue = (n: number) => pageInfo(n).speaker === 'Khadidja'
</script>

<template>
  <footer class="deck-footer">
    <span class="footer-brand">STAYLINE<i />CPP 706-155</span>
    <span class="speaker-pill" :class="info.speaker.toLowerCase()"><b />{{ info.speaker }}</span>
    <span class="footer-number">{{ String(nav.currentPage.value).padStart(2, '0') }}<small> / {{ MAIN_PAGES }}</small></span>
    <div class="progress-track" aria-hidden="true">
      <span v-for="n in segments" :key="n" :class="{ done: n <= nav.currentPage.value, blue: blue(n) }" />
    </div>
  </footer>
</template>
