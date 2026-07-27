/**
 * Test fixtures shared by every component and page test.
 *
 * These live in a plain module rather than in a *.test.tsx file on purpose:
 * importing a test file from another test file re-registers its describe
 * blocks in the importing file, so the same suite would run more than once.
 *
 * src/test/** is excluded from coverage in vite.config.ts.
 */

import type { ReportDetail, ReportField } from '../api/types'

export function makeField(
  id: string,
  label: string,
  overrides: Partial<ReportField> = {},
): ReportField {
  return {
    id,
    report_id: 'r1',
    label,
    content: '',
    sort_order: 0,
    is_user_edited: false,
    ...overrides,
  }
}

export function makeReport(overrides: Partial<ReportDetail> = {}): ReportDetail {
  return {
    id: 'r1',
    name: 'Kickoff',
    logo_file_id: null,
    created_at: '2026-07-27T10:00:00.000000Z',
    updated_at: '2026-07-27T10:05:00.000000Z',
    fields: [],
    ...overrides,
  }
}
