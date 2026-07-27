import type { DragEndEvent } from '@dnd-kit/core'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { makeField } from '../../test/fixtures'

/**
 * dnd-kit's sensors cannot complete a drag under jsdom: every
 * getBoundingClientRect is all-zero, so closestCenter never resolves an "over"
 * and onDragEnd never fires. DndContext is therefore replaced with a shim that
 * captures onDragEnd, letting the test drive the handler directly with the
 * exact event dnd-kit would have produced. Everything else - SortableContext,
 * useSortable, the drag handle - is the real implementation.
 */
const dragEndHandlers: Array<(event: DragEndEvent) => void> = []

vi.mock('@dnd-kit/core', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@dnd-kit/core')>()
  return {
    ...actual,
    DndContext: ({
      children,
      onDragEnd,
    }: {
      children: ReactNode
      onDragEnd: (event: DragEndEvent) => void
    }) => {
      dragEndHandlers.push(onDragEnd)
      return <div data-testid="dnd-context">{children}</div>
    },
  }
})

const { SortableFieldList } = await import('./SortableFieldList')

function fireDragEnd(activeId: string, overId: string | null) {
  const handler = dragEndHandlers[dragEndHandlers.length - 1]
  handler({
    active: { id: activeId },
    over: overId === null ? null : { id: overId },
  } as unknown as DragEndEvent)
}

const FIELDS = [
  makeField('f1', 'Summary', { sort_order: 0 }),
  makeField('f2', 'Blockers', { sort_order: 1 }),
]

function renderList(onReorder = vi.fn()) {
  render(
    <SortableFieldList
      fields={FIELDS}
      onReorder={onReorder}
      renderField={(field) => <span>{field.label} body</span>}
    />,
  )
  return onReorder
}

describe('SortableFieldList', () => {
  beforeEach(() => {
    dragEndHandlers.length = 0
  })

  it('renders one labelled drag handle per field', () => {
    renderList()

    expect(screen.getByRole('button', { name: 'Reorder Summary' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reorder Blockers' })).toBeInTheDocument()
  })

  it('renders the supplied field body', () => {
    renderList()

    expect(screen.getByText('Summary body')).toBeInTheDocument()
    expect(screen.getByText('Blockers body')).toBeInTheDocument()
  })

  it('reports the complete new order when a field is dropped on another', () => {
    const onReorder = renderList()

    fireDragEnd('f1', 'f2')

    expect(onReorder).toHaveBeenCalledWith(['f2', 'f1'])
  })

  it('does nothing when the field is dropped outside the list', () => {
    const onReorder = renderList()

    fireDragEnd('f1', null)

    expect(onReorder).not.toHaveBeenCalled()
  })

  it('does nothing when the field is dropped on itself', () => {
    const onReorder = renderList()

    fireDragEnd('f1', 'f1')

    expect(onReorder).not.toHaveBeenCalled()
  })

  it('does nothing for an id that is not in the list', () => {
    const onReorder = renderList()

    fireDragEnd('ghost', 'f1')

    expect(onReorder).not.toHaveBeenCalled()
  })
})
