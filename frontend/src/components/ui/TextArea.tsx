import type { TextareaHTMLAttributes } from 'react'

const DEFAULT_ROWS = 6

const FIELD_CLASSES =
  'mt-1 block w-full rounded-md border border-grey-light bg-white px-3 py-2 text-charcoal placeholder:text-grey-mid focus:border-blue-royal focus:outline-none'

type TextAreaProps = Omit<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  'id' | 'value' | 'onChange' | 'rows'
> & {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  rows?: number
}

export function TextArea({
  id,
  label,
  value,
  onChange,
  rows = DEFAULT_ROWS,
  className = '',
  ...rest
}: TextAreaProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-charcoal">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${FIELD_CLASSES} ${className}`.trim()}
        {...rest}
      />
    </div>
  )
}
