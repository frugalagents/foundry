function canonicalize(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\u2013\u2014]/g, '-')
    .replace(/[^a-z0-9?\-\s]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function tokenize(value: string) {
  return canonicalize(value)
    .replace(/[?]/g, '')
    .split(' ')
    .filter(Boolean)
}

function isNearDuplicate(a: string, b: string) {
  const left = canonicalize(a)
  const right = canonicalize(b)
  if (!left || !right) return false
  if (left === right) return true

  const shorter = left.length <= right.length ? left : right
  const longer = left.length <= right.length ? right : left
  if ((longer.startsWith(shorter) || shorter.startsWith(longer)) && shorter.length / longer.length >= 0.82) {
    return true
  }

  const shortTokens = tokenize(shorter)
  const longTokens = tokenize(longer)
  if (shortTokens.length === 0 || longTokens.length === 0) return false

  const sharedPrefix = shortTokens.findIndex((token, index) => longTokens[index] !== token)
  const prefixLength = sharedPrefix === -1 ? shortTokens.length : sharedPrefix
  if (prefixLength / shortTokens.length >= 0.8) {
    return true
  }

  return false
}

export function dedupeTextList(values: string[]) {
  const deduped: string[] = []

  values
    .map((value) => value.trim())
    .filter(Boolean)
    .forEach((value) => {
      const existingIndex = deduped.findIndex((current) => isNearDuplicate(current, value))
      if (existingIndex === -1) {
        deduped.push(value)
        return
      }

      if (value.length > deduped[existingIndex].length) {
        deduped[existingIndex] = value
      }
    })

  return deduped
}

export function hasPendingItems(values: string[]) {
  return dedupeTextList(values).length > 0
}
