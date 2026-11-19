import { ref, watch } from 'vue'
import gsap from 'gsap'

/** A number that counts up when `on` turns true, and eases to a new target when the target changes. */
export function useCount(target: () => number, on: () => boolean, still: () => boolean, duration = 1.8, delay = 0) {
  const value = ref(0)
  const state = { x: 0 }
  let tween: gsap.core.Tween | undefined
  watch([on, target], ([active, to], [wasActive]) => {
    tween?.kill()
    if (!active) { state.x = 0; value.value = 0; return }
    if (still()) { state.x = to; value.value = to; return }
    if (!wasActive) state.x = 0
    tween = gsap.to(state, { x: to, duration: wasActive ? 1.1 : duration, delay: wasActive ? 0.25 : delay, ease: 'power3.out', onUpdate: () => { value.value = state.x } })
  }, { immediate: true })
  return value
}
