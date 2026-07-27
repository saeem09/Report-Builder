import { describe, expect, it } from 'vitest'

import type { ReportDetail, ReportField } from '../api/types'
import { appendField, removeField, replaceField } from './reportState'

function field(id: string, sortOrder: number, content = ''): ReportField {
  return {
    id,
    report_id: 'r1',
    label: id.toUpperCase(),
    content,
    sort_order: sortOrder,
    is_user_edited: false,
  }
}

function report(fields: ReportField[]): ReportDetail {
  return {
    id: 'r1',
    name: 'Kickoff',
    logo_file_id: null,
    created_at: '2026-07-27T10:00:00.000000Z',
    updated_at: '2026-07-27T10:05:00.000000Z',
    fields,
  }
}

describe('replaceField', () => {
  it('swaps the matching field and keeps the order', () => {
    const original = report([field('f1', 0), field('f2', 1)])
    const updated: ReportField = { ...field('f2', 1, 'Edited.'), is_user_edited: true }

    const result = replaceField(original, updated)

    expect(result.fields.map((item) => item.id)).toEqual(['f1', 'f2'])
    expect(result.fields[1].content).toBe('Edited.')
    expect(result.fields[1].is_user_edited).toBe(true)
  })

  it('does not mutate the original report or its field array', () => {
    const original = report([field('f1', 0)])
    const originalFields = original.fields

    const result = replaceField(original, field('f1', 0, 'Edited.'))

    expect(original.fields).toBe(originalFields)
    expect(original.fields[0].content).toBe('')
    expect(result).not.toBe(original)
    expect(result.fields).not.toBe(originalFields)
  })

  it('leaves the report unchanged when the id is unknown', () => {
    const original = report([field('f1', 0)])

    const result = replaceField(original, field('ghost', 0, 'x'))

    expect(result.fields.map((item) => item.id)).toEqual(['f1'])
    expect(result.fields[0].content).toBe('')
  })
})

describe('appendField', () => {
  it('adds the field at the end', () => {
    const result = appendField(report([field('f1', 0)]), field('f2', 1))

    expect(result.fields.map((item) => item.id)).toEqual(['f1', 'f2'])
  })

  it('does not mutate the original', () => {
    const original = report([field('f1', 0)])

    appendField(original, field('f2', 1))

    expect(original.fields).toHaveLength(1)
  })

  it('works on a report with no fields', () => {
    const result = appendField(report([]), field('f1', 0))

    expect(result.fields).toHaveLength(1)
  })
})

describe('removeField', () => {
  it('drops the matching field', () => {
    const result = removeField(report([field('f1', 0), field('f2', 1)]), 'f1')

    expect(result.fields.map((item) => item.id)).toEqual(['f2'])
  })

  it('does not mutate the original', () => {
    const original = report([field('f1', 0), field('f2', 1)])

    removeField(original, 'f1')

    expect(original.fields).toHaveLength(2)
  })

  it('leaves the report unchanged when the id is unknown', () => {
    const result = removeField(report([field('f1', 0)]), 'ghost')

    expect(result.fields.map((item) => item.id)).toEqual(['f1'])
  })
})
