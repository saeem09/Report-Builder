/**
 * TypeScript mirrors of the backend's Pydantic response models.
 *
 * Property names are snake_case because that is exactly what the API sends.
 * Renaming them to camelCase would mean a mapping layer on both sides of every
 * call for no gain, and would make a mismatch with the server silent rather
 * than a compile error.
 *
 * Source of truth: backend/app/reports/schemas.py
 */

/** FieldResponse. is_user_edited arrives as a JSON boolean, not 0 or 1. */
export type ReportField = {
  id: string
  report_id: string
  label: string
  content: string
  sort_order: number
  is_user_edited: boolean
}

/** ReportSummaryResponse, as returned by the list endpoint. */
export type ReportSummary = {
  id: string
  name: string
  logo_file_id: string | null
  created_at: string
  updated_at: string
}

/** ReportDetailResponse. Returned by create, get, rename, reorder, generate, logo. */
export type ReportDetail = ReportSummary & {
  fields: ReportField[]
}

/** ReportListResponse. */
export type ReportListResponse = {
  reports: ReportSummary[]
}

/** SourceDocumentResponse. cleaned_text is deliberately not exposed by the API. */
export type SourceDocument = {
  id: string
  report_id: string
  file_id: string
  original_name: string
  sort_order: number
  created_at: string
}
