import { computed, ref, watch } from 'vue'
import { useNav, useSlideContext } from '@slidev/client'

export function useBeat() {
  const nav = useNav()
  const { $page, $clicks } = useSlideContext()
  const print = computed(() => nav.isPrintMode.value || (typeof location !== 'undefined' && location.search.includes('export')))
  const current = computed(() => print.value || nav.currentPage.value === $page.value)
  const active = ref(false)
  watch(current, (on) => {
    if (!on) { active.value = false; return }
    if (print.value || typeof requestAnimationFrame === 'undefined') { active.value = true; return }
    requestAnimationFrame(() => requestAnimationFrame(() => { active.value = current.value }))
  }, { immediate: true })
  const click = computed(() => $clicks.value)
  const shown = (at: number) => print.value || click.value >= at
  return { active, click, print, shown }
}
