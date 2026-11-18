import { describe, expect, it } from 'vitest'
import { interval, pct, seconds, usd } from './format'

describe('evaluation formatting', () => {
  it('formats rates, costs, seconds and intervals', () => {
    expect(pct(0.978)).toBe('97.8%')
    expect(usd(0.00153)).toBe('$0.0015')
    expect(seconds(8.84)).toBe('8.8 s')
    expect(interval(0.833, 0.994)).toBe('83.3% to 99.4%')
  })

  it('uses n/a for missing values', () => {
    expect(pct(null)).toBe('n/a')
    expect(usd(null)).toBe('n/a')
    expect(seconds(null)).toBe('n/a')
    expect(interval(null, 0.5)).toBe('n/a')
  })
})
