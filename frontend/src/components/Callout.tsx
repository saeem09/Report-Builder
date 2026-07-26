import type { ReactNode } from 'react'

type CalloutProps = {
  children: ReactNode
}

export function Callout({ children }: CalloutProps) {
  return (
    <div className="bg-tint-sky text-charcoal border border-blue-steel rounded-md p-4">
      <p>{children}</p>
    </div>
  )
}
