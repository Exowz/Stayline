export const pct = (value: number | null): string => value === null ? 'n/a' : `${(value * 100).toFixed(1)}%`
export const usd = (value: number | null): string => value === null ? 'n/a' : `$${value.toFixed(4)}`
export const seconds = (value: number | null): string => value === null ? 'n/a' : `${value.toFixed(1)} s`
export const interval = (low: number | null, high: number | null): string =>
  low === null || high === null ? 'n/a' : `${pct(low)} to ${pct(high)}`
