import { ref } from 'vue'
import * as F from './formations'
import type { Formation } from './engine'

export const MAIN_PAGES = 10
export const pages = [
  { name: 'The freeze', speaker: 'Khadidja' },
  { name: 'Two dangerous buttons', speaker: 'Khadidja' },
  { name: 'The backend', speaker: 'Ewan' },
  { name: 'The graph', speaker: 'Ewan' },
  { name: 'Live demo: success', speaker: 'Ewan' },
  { name: 'Live demo: failure', speaker: 'Ewan' },
  { name: 'Memory', speaker: 'Khadidja' },
  { name: 'Results', speaker: 'Khadidja' },
  { name: 'Error analysis', speaker: 'Khadidja' },
  { name: 'The close', speaker: 'Ewan' },
] as const

export const pageInfo = (page: number) => pages[Math.max(0, Math.min(MAIN_PAGES - 1, page - 1))]

/** Sub-state a slide can set itself (memory story, before/after timing). */
export const phase = ref<'none' | 'without' | 'with'>('none')

export function formationFor(page: number, click: number, memoryPhase: 'none' | 'without' | 'with'): Formation {
  switch (page) {
    case 1: return F.hero(click)
    case 2: return F.twoButtons(click)
    case 3: return F.backend(click)
    case 4: return F.graph(click)
    case 5: return F.trace(click, 's01')
    case 6: return F.trace(click, 's14')
    case 7: return F.memory(memoryPhase)
    case 8: return F.results(click)
    case 9: return F.errors(click)
    case 10: return click >= 2 ? F.finale() : click >= 1 ? F.compare() : F.calm()
    default: return F.hero(0)
  }
}
