import { arrayMove } from '@dnd-kit/sortable'

/**
 * Work out the complete new field id order after a drop, or null if there is
 * nothing to apply.
 *
 * Returning the whole list rather than a move instruction is what the API
 * wants: PUT /fields/order takes every id in its new order and rejects
 * anything that is not an exact permutation, which makes the request
 * idempotent and impossible to half-apply.
 */
export function nextFieldOrder(
  fieldIds: readonly string[],
  activeId: string,
  overId: string,
): string[] | null {
  if (activeId === overId) {
    return null
  }
  const from = fieldIds.indexOf(activeId)
  const to = fieldIds.indexOf(overId)
  if (from === -1 || to === -1) {
    return null
  }
  // arrayMove returns a new array; the copy keeps it from touching the caller's.
  return arrayMove([...fieldIds], from, to)
}
