import type { DragEndEvent } from '@dnd-kit/core'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { ReactNode } from 'react'

import type { ReportField } from '../../api/types'
import { nextFieldOrder } from '../../lib/reorder'

type SortableRowProps = {
  id: string
  label: string
  children: ReactNode
}

function SortableRow({ id, label, children }: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id })

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`flex rounded-md border border-grey-light bg-white ${
        isDragging ? 'opacity-60' : ''
      }`.trim()}
    >
      {/*
        A real button, not a div, so the handle is reachable by keyboard and
        announced. dnd-kit's KeyboardSensor binds to these same listeners, so
        a keyboard drag works in a real browser even though jsdom cannot
        measure the layout it needs.
      */}
      <button
        type="button"
        aria-label={`Reorder ${label}`}
        className="shrink-0 cursor-grab px-3 py-4 text-sm font-semibold text-grey-mid hover:text-navy-deep"
        {...attributes}
        {...listeners}
      >
        Drag
      </button>
      {children}
    </li>
  )
}

type SortableFieldListProps = {
  fields: readonly ReportField[]
  onReorder: (fieldIds: string[]) => void
  renderField: (field: ReportField) => ReactNode
}

export function SortableFieldList({
  fields,
  onReorder,
  renderField,
}: SortableFieldListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const fieldIds = fields.map((field) => field.id)

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (over === null) {
      return
    }
    const reordered = nextFieldOrder(fieldIds, String(active.id), String(over.id))
    if (reordered !== null) {
      onReorder(reordered)
    }
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={fieldIds} strategy={verticalListSortingStrategy}>
        <ul className="flex flex-col gap-3">
          {fields.map((field) => (
            <SortableRow key={field.id} id={field.id} label={field.label}>
              {renderField(field)}
            </SortableRow>
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  )
}
