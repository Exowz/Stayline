<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ text: string, on: boolean, tag?: string }>(), { tag: 'h1' })
const words = computed(() => props.text.split(' ').map((raw, index) => ({
  text: raw.replace(/\*/g, ''), accent: raw.startsWith('*'), delay: `${0.12 + index * 0.045}s`,
})))
const underlineDelay = computed(() => `${0.45 + words.value.length * 0.045}s`)
</script>

<template>
  <component :is="tag" class="kin" :class="{ on }">
    <template v-for="(word, index) in words" :key="index">
      <em v-if="word.accent" class="w" :style="{ '--d': word.delay, '--ud': underlineDelay }">{{ word.text }}<svg class="uline" viewBox="0 0 200 20" preserveAspectRatio="none" aria-hidden="true"><path d="M2 13 C40 6 90 16 130 9 S185 8 198 11" /></svg></em>
      <span v-else class="w" :style="{ '--d': word.delay }">{{ word.text }}</span>{{ ' ' }}
    </template>
  </component>
</template>
