/**
 * Immutable transitions on a ReportDetail's field list.
 *
 * These exist because three of the API's mutations return a single Field or
 * nothing at all rather than the whole report, so the page has to fold the
 * result into the report it already holds. Keeping that arithmetic here, as
 * pure functions, is what makes it testable without React and what guarantees
 * nothing is mutated in place.
 */

import type { ReportDetail, ReportField } from '../api/types'

/** Swap the field with the same id. Order and every other field are untouched. */
export function replaceField(report: ReportDetail, field: ReportField): ReportDetail {
  return {
    ...report,
    fields: report.fields.map((existing) =>
      existing.id === field.id ? field : existing,
    ),
  }
}

/** Add a newly created field. The server always appends, so this does too. */
export function appendField(report: ReportDetail, field: ReportField): ReportDetail {
  return { ...report, fields: [...report.fields, field] }
}

/** Drop a deleted field. Remaining sort_order values are left as the server has them. */
export function removeField(report: ReportDetail, fieldId: string): ReportDetail {
  return {
    ...report,
    fields: report.fields.filter((existing) => existing.id !== fieldId),
  }
}

/**
 * Apply a new field id order optimistically, before the server confirms it.
 *
 * sort_order is rewritten to each field's new index so the local object is
 * internally consistent; the server's response then replaces this value
 * entirely, so a divergence lasts only as long as one request.
 */
export function withFieldOrder(
  report: ReportDetail,
  fieldIds: readonly string[],
): ReportDetail {
  const byId = new Map(report.fields.map((field) => [field.id, field]))
  const ordered = fieldIds
    .map((fieldId) => byId.get(fieldId))
    .filter((field): field is ReportField => field !== undefined)
    .map((field, index) => ({ ...field, sort_order: index }))
  return { ...report, fields: ordered }
}
