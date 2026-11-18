export const MAIN_PAGES = 10
export type WorldName = 'field' | 'target' | 'grid' | 'compare' | 'before-after'
export const pages = [
  { name: 'The freeze', speaker: 'Khadidja', world: 'target' },
  { name: 'Two dangerous buttons', speaker: 'Khadidja', world: 'field' },
  { name: 'The backend', speaker: 'Ewan', world: 'field' },
  { name: 'The graph', speaker: 'Ewan', world: 'field' },
  { name: 'Live demo: success', speaker: 'Ewan', world: 'field' },
  { name: 'Live demo: failure', speaker: 'Ewan', world: 'field' },
  { name: 'Memory', speaker: 'Khadidja', world: 'field' },
  { name: 'Results', speaker: 'Khadidja', world: 'grid' },
  { name: 'Error analysis', speaker: 'Khadidja', world: 'field' },
  { name: 'The close', speaker: 'Ewan', world: 'field' },
] as const
export function pageInfo(page: number) { return pages[Math.max(0, Math.min(MAIN_PAGES - 1, page - 1))] }
export function worldFor(page: number, click: number): { name: WorldName, satellites: number, delay: number } {
  if (page === 9 && click >= 3) return { name: 'before-after', satellites: 0, delay: 0.45 }
  if (page === 10 && click >= 2) return { name: 'field', satellites: 0, delay: 0.45 }
  if (page === 10 && click >= 1) return { name: 'compare', satellites: 0, delay: 0.45 }
  const info = pageInfo(page)
  return { name: info.world as WorldName, satellites: page === 1 ? Math.max(0, click - 1) : 5, delay: 0.45 }
}
