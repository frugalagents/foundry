function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderInline(text: string): string {
  const codeTokens: string[] = []
  let html = escapeHtml(text)

  html = html.replace(/`([^`]+)`/g, (_, code: string) => {
    const token = `@@CODETOK${codeTokens.length}@@`
    codeTokens.push(`<code>${code}</code>`)
    return token
  })

  html = html
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')

  return codeTokens.reduce((current, _token, index) => (
    current.split(`@@CODETOK${index}@@`).join(codeTokens[index])
  ), html)
}

function renderList(lines: string[], ordered: boolean): string {
  const items: string[] = []
  let current: string[] = []

  function flushCurrent() {
    if (current.length === 0) return
    const [head, ...rest] = current
    const content = [head.trim(), ...rest.map((line) => line.trim())]
      .filter(Boolean)
      .map(renderInline)
      .join('<br />')
    items.push(`<li>${content}</li>`)
    current = []
  }

  for (const line of lines) {
    if (/^\s{2,}\S/.test(line) && current.length > 0) {
      current.push(line)
      continue
    }

    flushCurrent()
    current.push(line.replace(ordered ? /^\d+\.\s+/ : /^[-*]\s+/, ''))
  }

  flushCurrent()
  return ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`
}

function isTableSeparator(line: string): boolean {
  return /^\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?$/.test(line.trim())
}

function parseTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function renderTable(lines: string[]): string {
  if (lines.length < 2) return `<p>${renderInline(lines.join(' '))}</p>`

  const [headerLine, , ...bodyLines] = lines
  const headers = parseTableRow(headerLine)
  const rows = bodyLines
    .filter((line) => line.trim())
    .map(parseTableRow)

  const head = headers.map((cell) => `<th>${renderInline(cell)}</th>`).join('')
  const body = rows.map((row) => (
    `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join('')}</tr>`
  )).join('')

  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`
}

function finalizeH2Sections(html: string): string {
  const parts = html.split(/(<h2>.*?<\/h2>)/g)
  if (parts.length < 5) return html

  let result = parts[0]
  for (let i = 1; i < parts.length; i += 2) {
    const title = parts[i].replace(/<\/?h2>/g, '')
    const content = parts[i + 1] ?? ''
    const open = i === 1 ? ' open' : ''
    result += `<details${open}><summary>${title}</summary><div class="details-body">${content}</div></details>`
  }
  return result
}

type RenderMarkdownOptions = {
  collapsibleH2Sections?: boolean
}

export function renderMarkdown(
  text: string,
  options: RenderMarkdownOptions = {},
): string {
  const { collapsibleH2Sections = true } = options
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const blocks: string[] = []

  for (let index = 0; index < lines.length;) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('```')) {
      const codeLines: string[] = []
      index += 1
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
      continue
    }

    if (/^###\s+/.test(trimmed)) {
      blocks.push(`<h3>${renderInline(trimmed.replace(/^###\s+/, ''))}</h3>`)
      index += 1
      continue
    }

    if (/^##\s+/.test(trimmed)) {
      blocks.push(`<h2>${renderInline(trimmed.replace(/^##\s+/, ''))}</h2>`)
      index += 1
      continue
    }

    if (/^#\s+/.test(trimmed)) {
      blocks.push(`<h1>${renderInline(trimmed.replace(/^#\s+/, ''))}</h1>`)
      index += 1
      continue
    }

    if (/^---+$/.test(trimmed)) {
      blocks.push('<hr />')
      index += 1
      continue
    }

    if (
      index + 1 < lines.length &&
      trimmed.includes('|') &&
      isTableSeparator(lines[index + 1])
    ) {
      const tableLines: string[] = [lines[index], lines[index + 1]]
      index += 2
      while (index < lines.length && lines[index].trim().includes('|')) {
        tableLines.push(lines[index])
        index += 1
      }
      blocks.push(renderTable(tableLines))
      continue
    }

    if (/^>\s?/.test(trimmed)) {
      const quoteLines: string[] = []
      while (index < lines.length && /^>\s?/.test(lines[index].trim())) {
        quoteLines.push(lines[index].trim().replace(/^>\s?/, ''))
        index += 1
      }
      blocks.push(`<blockquote>${quoteLines.map(renderInline).join('<br />')}</blockquote>`)
      continue
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const listLines: string[] = []
      while (
        index < lines.length && (
          /^[-*]\s+/.test(lines[index].trim()) ||
          /^\s{2,}\S/.test(lines[index])
        )
      ) {
        listLines.push(lines[index])
        index += 1
      }
      blocks.push(renderList(listLines, false))
      continue
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const listLines: string[] = []
      while (
        index < lines.length && (
          /^\d+\.\s+/.test(lines[index].trim()) ||
          /^\s{2,}\S/.test(lines[index])
        )
      ) {
        listLines.push(lines[index])
        index += 1
      }
      blocks.push(renderList(listLines, true))
      continue
    }

    const paragraphLines: string[] = []
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(```|###\s+|##\s+|#\s+|---+$|>\s?|[-*]\s+|\d+\.\s+)/.test(lines[index].trim())
    ) {
      paragraphLines.push(lines[index].trim())
      index += 1
    }
    blocks.push(`<p>${renderInline(paragraphLines.join(' '))}</p>`)
  }

  const html = blocks.join('')
  return collapsibleH2Sections ? finalizeH2Sections(html) : html
}
