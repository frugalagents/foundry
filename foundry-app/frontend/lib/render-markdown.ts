export function renderMarkdown(text: string): string {
  const html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```[\s\S]*?```/g, (m) => {
      const inner = m.slice(3, -3).replace(/^[^\n]*\n/, '')
      return `<pre><code>${inner}</code></pre>`
    })
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^---+$/gm, '<hr />')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^(?!<[huplo]|<li|<pre|<blockquote|<hr)(.+)$/gm, '<p>$1</p>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')

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
