import { describe, expect, it } from 'vitest'

import { formatTimestamp } from './formatTimestamp'

describe('formatTimestamp', () => {
  it('formats a valid ISO timestamp using the reader locale', () => {
    const isoTimestamp = '2026-07-27T10:05:00.000000Z'

    expect(formatTimestamp(isoTimestamp)).toBe(new Date(isoTimestamp).toLocaleString())
  })

  it('falls back to the raw string when the timestamp cannot be parsed', () => {
    expect(formatTimestamp('not-a-timestamp')).toBe('not-a-timestamp')
  })
})
