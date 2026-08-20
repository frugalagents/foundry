'use client'

import { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { Shapes } from 'lucide-react'
import dynamicIconImports from 'lucide-react/dynamicIconImports'

type DynamicIconName = keyof typeof dynamicIconImports

function toLucideKey(icon: string): DynamicIconName | null {
  const trimmed = icon.trim()
  if (!trimmed) return null

  const normalized = trimmed
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/[_\s]+/g, '-')
    .toLowerCase()

  return normalized in dynamicIconImports ? normalized as DynamicIconName : null
}

export default function IconGlyph({
  icon,
  color,
  size = 14,
  fallbackText = false,
}: {
  icon?: string
  color: string
  size?: number
  fallbackText?: boolean
}) {
  const iconKey = useMemo(() => (icon ? toLucideKey(icon) : null), [icon])
  const LucideIcon = useMemo(() => {
    if (!iconKey) return null
    return dynamic(dynamicIconImports[iconKey], { ssr: false })
  }, [iconKey])

  if (LucideIcon) {
    return <LucideIcon size={size} color={color} strokeWidth={2} />
  }

  if (fallbackText && icon?.trim()) {
    return <span>{icon}</span>
  }

  return <Shapes size={size} color={color} strokeWidth={2} />
}
