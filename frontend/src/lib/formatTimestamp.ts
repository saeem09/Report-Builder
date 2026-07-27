/**
 * Timestamps arrive as microsecond-precision UTC ISO strings. They are shown
 * in the reader's own locale because "when did I last touch this" is the only
 * question this answers. If the string cannot be parsed, the raw value is
 * shown rather than something misleading like "Invalid Date".
 */
export function formatTimestamp(isoTimestamp: string): string {
  const parsed = new Date(isoTimestamp)
  return Number.isNaN(parsed.getTime()) ? isoTimestamp : parsed.toLocaleString()
}
