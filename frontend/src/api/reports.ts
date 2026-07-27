/**
 * One function per backend endpoint. Nothing outside this module builds a URL
 * or calls fetch, which is what lets a component test stub a single named
 * export instead of reasoning about request shapes.
 *
 * Path segments are always encodeURIComponent'd. Report and field ids are
 * server-generated UUIDs today, but encoding is what stops a future id format
 * from silently changing which resource a request reaches.
 */

import { jsonBody, requestBlob, requestJson, requestVoid } from './client'
import type {
  ReportDetail,
  ReportField,
  ReportListResponse,
  ReportSummary,
  SourceDocument,
} from './types'

function reportPath(reportId: string): string {
  return `/api/reports/${encodeURIComponent(reportId)}`
}

function fieldPath(reportId: string, fieldId: string): string {
  return `${reportPath(reportId)}/fields/${encodeURIComponent(fieldId)}`
}

/**
 * Multipart bodies must not carry an explicit Content-Type header: the browser
 * has to set it itself so it can append the multipart boundary. Passing
 * headers here would produce a request the server cannot parse.
 */
function fileBody(file: File): RequestInit {
  const form = new FormData()
  form.append('file', file)
  return { body: form }
}

export async function listReports(): Promise<ReportSummary[]> {
  const response = await requestJson<ReportListResponse>('/api/reports')
  return response.reports
}

export function createReport(
  name: string,
  fieldLabels: readonly string[],
): Promise<ReportDetail> {
  return requestJson<ReportDetail>('/api/reports', {
    method: 'POST',
    ...jsonBody({ name, field_labels: fieldLabels }),
  })
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return requestJson<ReportDetail>(reportPath(reportId))
}

export function renameReport(reportId: string, name: string): Promise<ReportDetail> {
  return requestJson<ReportDetail>(reportPath(reportId), {
    method: 'PATCH',
    ...jsonBody({ name }),
  })
}

export function deleteReport(reportId: string): Promise<void> {
  return requestVoid(reportPath(reportId), { method: 'DELETE' })
}

export function addField(reportId: string, label: string): Promise<ReportField> {
  return requestJson<ReportField>(`${reportPath(reportId)}/fields`, {
    method: 'POST',
    ...jsonBody({ label }),
  })
}

/**
 * The server requires the complete field id list in its new order and rejects
 * anything else with 400, which is what makes the reorder idempotent.
 */
export function reorderFields(
  reportId: string,
  fieldIds: readonly string[],
): Promise<ReportDetail> {
  return requestJson<ReportDetail>(`${reportPath(reportId)}/fields/order`, {
    method: 'PUT',
    ...jsonBody({ field_ids: fieldIds }),
  })
}

/**
 * This is the only call that sets is_user_edited on the server, permanently
 * excluding the field from future AI generation. Callers must only invoke it
 * on a deliberate user save, never on a keystroke.
 */
export function updateFieldContent(
  reportId: string,
  fieldId: string,
  content: string,
): Promise<ReportField> {
  return requestJson<ReportField>(fieldPath(reportId, fieldId), {
    method: 'PATCH',
    ...jsonBody({ content }),
  })
}

export function deleteField(reportId: string, fieldId: string): Promise<void> {
  return requestVoid(fieldPath(reportId, fieldId), { method: 'DELETE' })
}

export function uploadSourceDocument(
  reportId: string,
  file: File,
): Promise<SourceDocument> {
  return requestJson<SourceDocument>(`${reportPath(reportId)}/documents`, {
    method: 'POST',
    ...fileBody(file),
  })
}

export function generateReport(reportId: string): Promise<ReportDetail> {
  return requestJson<ReportDetail>(`${reportPath(reportId)}/generate`, {
    method: 'POST',
  })
}

export function uploadReportLogo(reportId: string, file: File): Promise<ReportDetail> {
  return requestJson<ReportDetail>(`${reportPath(reportId)}/logo`, {
    method: 'PUT',
    ...fileBody(file),
  })
}

export function exportReportPdf(
  reportId: string,
): Promise<{ blob: Blob; contentDisposition: string | null }> {
  return requestBlob(`${reportPath(reportId)}/export.pdf`)
}
