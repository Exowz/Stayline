<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNav } from '@slidev/client'
import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin'

gsap.registerPlugin(SplitText, DrawSVGPlugin)

const props = defineProps<{ page: number, eyebrow: string, before: string, emphasis?: string, after?: string, hero?: boolean, fail?: boolean }>()
const nav = useNav()
const heading = ref<HTMLElement | null>(null)
const eyebrowEl = ref<HTMLElement | null>(null)
const underline = ref<SVGPathElement | null>(null)
let split: SplitText | undefined
let timeline: gsap.core.Timeline | undefined

const still = () => matchMedia('(prefers-reduced-motion: reduce)').matches || nav.isPrintMode.value || location.search.includes('export')

function showFinal() {
  if (!heading.value) return
  gsap.set(split?.words ?? heading.value, { y: 0, opacity: 1, filter: 'blur(0px)' })
  gsap.set(eyebrowEl.value, { opacity: 1, letterSpacing: '0.16em' })
  if (underline.value) gsap.set(underline.value, { drawSVG: '100%' })
}

function animate() {
  if (!heading.value || nav.currentPage.value !== props.page) return
  timeline?.kill()
  if (still()) return showFinal()
  const words = split?.words ?? [heading.value]
  gsap.set(words, { y: 46, opacity: 0, filter: 'blur(10px)' })
  gsap.set(eyebrowEl.value, { opacity: 0, letterSpacing: '0.34em' })
  if (underline.value) gsap.set(underline.value, { drawSVG: '0%' })
  timeline = gsap.timeline({ delay: 0.3 })
  timeline.to(eyebrowEl.value, { opacity: 1, letterSpacing: '0.16em', duration: 0.9, ease: 'power2.out' }, 0)
  timeline.to(words, { y: 0, opacity: 1, filter: 'blur(0px)', duration: 0.9, stagger: 0.07, ease: 'power3.out' }, 0.1)
  if (underline.value) timeline.to(underline.value, { drawSVG: '100%', duration: 0.7, ease: 'power2.inOut' }, '>-0.1')
}

onMounted(async () => {
  await nextTick()
  if (heading.value) split = new SplitText(heading.value, { type: 'words', mask: 'words' })
  animate()
})
watch(nav.currentPage, animate)
onBeforeUnmount(() => { timeline?.kill(); split?.revert() })
</script>

<template>
  <header class="headline" :class="{ 'headline-hero': hero }">
    <div ref="eyebrowEl" class="eyebrow">{{ eyebrow }}</div>
    <h1 ref="heading">{{ before }}<em v-if="emphasis" :class="{ fail }">{{ emphasis }}<svg viewBox="0 0 260 20" preserveAspectRatio="none" aria-hidden="true"><path ref="underline" d="M3 15 C65 4 145 22 257 7" /></svg></em>{{ after }}</h1>
  </header>
</template>
