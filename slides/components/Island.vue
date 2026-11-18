<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'light' | 'dark' | 'loud' | 'fail' }>(), { tone: 'light' })
</script>

<template><div class="island" :class="`island-${tone}`"><slot /></div></template>
