"use client"

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const components: Components = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '')
      const codeString = String(children).replace(/\n$/, '')

      if (match) {
        return (
          <SyntaxHighlighter
            style={oneLight}
            language={match[1]}
            PreTag="div"
            customStyle={{
              borderRadius: '12px',
              padding: '1.25rem',
              fontSize: '14px',
              lineHeight: '1.7',
              border: '1px solid #e5e7eb',
              margin: '1.5rem 0',
            }}
          >
            {codeString}
          </SyntaxHighlighter>
        )
      }

      return (
        <code className={className} {...props}>
          {children}
        </code>
      )
    },
    h2({ children, ...props }) {
      const text = String(children)
      const id = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
      return (
        <h2 id={id} {...props}>
          {children}
        </h2>
      )
    },
    h3({ children, ...props }) {
      const text = String(children)
      const id = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
      return (
        <h3 id={id} {...props}>
          {children}
        </h3>
      )
    },
  }

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  )
}
