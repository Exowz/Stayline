<script setup lang="ts">
import { computed } from 'vue'
import { useNav } from '@slidev/client'
import { MAIN_PAGES, pageInfo } from './world/pages'

const nav = useNav()
const info = computed(() => pageInfo(nav.currentPage.value))
</script>

<template>
  <footer class="deck-dock">
    <strong>Stayline</strong><i class="dock-rule" />
    <span class="dock-beat">{{ info.name }}</span>
    <span class="speaker-chip"><i :class="info.speaker.toLowerCase()" />{{ info.speaker }}</span>
    <span class="dock-page">{{ String(nav.currentPage.value).padStart(2, '0') }}</span>
    <span class="dock-progress"><i v-for="page in MAIN_PAGES" :key="page" :class="{ done: page < nav.currentPage.value, now: page === nav.currentPage.value }" /></span>
  </footer>
</template>
