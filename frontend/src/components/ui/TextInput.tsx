import type { InputHTMLAttributes } from 'react'

const FIELD_CLASSES =
  'mt-1 block w-full rounded-md border border-grey-light bg-white px-3 py-2 text-charcoal placeholder:text-grey-mid focus:border-blue-royal focus:outline-none'

type TextInputProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'id' | 'value' | 'onChange'
> & {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
}

/**
 * onChange receives the string value rather than the event: every caller wants
 * the value, so unwrapping it once here keeps event.target.value out of a
 * dozen components.
 */
export function TextInput({
  id,
  label,
  value,
  onChange,
  className = '',
  ...rest
}: TextInputProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-charcoal">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${FIELD_CLASSES} ${className}`.trim()}
        {...rest}
      />
    </div>
  )
}
