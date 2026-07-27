import { describe, expect, it } from 'vitest'

import { nextFieldOrder } from './reorder'

const IDS = ['f1', 'f2', 'f3']

describe('nextFieldOrder', () => {
  it('moves an item down', () => {
    expect(nextFieldOrder(IDS, 'f1', 'f3')).toEqual(['f2', 'f3', 'f1'])
  })

  it('moves an item up', () => {
    expect(nextFieldOrder(IDS, 'f3', 'f1')).toEqual(['f3', 'f1', 'f2'])
  })

  it('swaps neighbours', () => {
    expect(nextFieldOrder(IDS, 'f1', 'f2')).toEqual(['f2', 'f1', 'f3'])
  })

  it('returns null when the item is dropped on itself', () => {
    expect(nextFieldOrder(IDS, 'f2', 'f2')).toBeNull()
  })

  it('returns null when the active id is unknown', () => {
    expect(nextFieldOrder(IDS, 'ghost', 'f1')).toBeNull()
  })

  it('returns null when the over id is unknown', () => {
    expect(nextFieldOrder(IDS, 'f1', 'ghost')).toBeNull()
  })

  it('does not mutate the input array', () => {
    const input = [...IDS]

    nextFieldOrder(input, 'f1', 'f3')

    expect(input).toEqual(IDS)
  })

  it('returns null for a single-item list dropped on itself', () => {
    expect(nextFieldOrder(['f1'], 'f1', 'f1')).toBeNull()
  })
})
