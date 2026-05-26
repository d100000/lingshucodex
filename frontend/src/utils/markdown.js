function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInline(value = '') {
  const codes = []
  let text = String(value).replace(/`([^`\n]+)`/g, (_, code) => {
    const key = `@@CODE_${codes.length}@@`
    codes.push(code)
    return key
  })

  text = escapeHtml(text)
    .replace(/\*\*([^*\n][\s\S]*?[^*\n])\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_\n][\s\S]*?[^_\n])__/g, '<strong>$1</strong>')
    .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
    .replace(/~~([^~\n]+)~~/g, '<del>$1</del>')

  codes.forEach((code, index) => {
    text = text.replace(`@@CODE_${index}@@`, `<code>${escapeHtml(code)}</code>`)
  })

  return text
}

export function renderMarkdown(markdown = '') {
  const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n')
  const html = []
  let paragraph = []
  let listType = ''
  let inCode = false
  let codeLines = []

  const closeParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${renderInline(paragraph.join('\n')).replace(/\n/g, '<br />')}</p>`)
    paragraph = []
  }

  const closeList = () => {
    if (!listType) return
    html.push(`</${listType}>`)
    listType = ''
  }

  const openList = (type) => {
    closeParagraph()
    if (listType === type) return
    closeList()
    listType = type
    html.push(`<${type}>`)
  }

  lines.forEach((rawLine) => {
    const line = rawLine.trimEnd()

    if (/^```/.test(line.trim())) {
      if (inCode) {
        html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
        codeLines = []
        inCode = false
      } else {
        closeParagraph()
        closeList()
        inCode = true
      }
      return
    }

    if (inCode) {
      codeLines.push(rawLine)
      return
    }

    if (!line.trim()) {
      closeParagraph()
      closeList()
      return
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(line)
    if (heading) {
      closeParagraph()
      closeList()
      const level = heading[1].length
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`)
      return
    }

    if (/^([-*_])(?:\s*\1){2,}\s*$/.test(line)) {
      closeParagraph()
      closeList()
      html.push('<hr />')
      return
    }

    const unordered = /^\s*[-*+]\s+(.+)$/.exec(line)
    if (unordered) {
      openList('ul')
      html.push(`<li>${renderInline(unordered[1])}</li>`)
      return
    }

    const ordered = /^\s*\d+\.\s+(.+)$/.exec(line)
    if (ordered) {
      openList('ol')
      html.push(`<li>${renderInline(ordered[1])}</li>`)
      return
    }

    const quote = /^\s*>\s?(.+)$/.exec(line)
    if (quote) {
      closeParagraph()
      closeList()
      html.push(`<blockquote>${renderInline(quote[1])}</blockquote>`)
      return
    }

    closeList()
    paragraph.push(line)
  })

  if (inCode) {
    html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
  }
  closeParagraph()
  closeList()

  return html.join('\n')
}

export function stripMarkdown(markdown = '') {
  return String(markdown || '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/~~([^~]+)~~/g, '$1')
    .trim()
}
