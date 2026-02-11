'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { api } from '../../utils/api'
import { useAuth } from '../../context/AuthContext'
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const SUGGESTED_PROMPTS = [
  { text: "Find federal grants for job training programs", icon: "search" },
  { text: "What grants are due in the next 30 days?", icon: "calendar" },
  { text: "Help me write a compelling project narrative", icon: "edit" },
  { text: "Analyze our organization's grant readiness", icon: "chart" },
]

export default function ChatPage() {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/chat')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (isAuthenticated && !sessionId) {
      // Try to restore session from localStorage
      const savedSessionId = localStorage.getItem('fundfish_session_id')
      if (savedSessionId) {
        setSessionId(savedSessionId)
        loadSessionHistory(savedSessionId)
      } else {
        startSession()
      }
    }
  }, [isAuthenticated, sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  const loadSessionHistory = async (sid: string) => {
    try {
      const response = await api.getChatHistory(sid)
      if (response.ok) {
        const data = await response.json()
        // Parse history if it exists
        if (data.history) {
          // Parse markdown format: **[HH:MM] USER:** text
          const historyText = data.history
          const messagePattern = /\*\*\[([\d:]+)\] (USER|AGENT):\*\* (.+?)(?=\n\*\*\[|$)/gs
          const matches = [...historyText.matchAll(messagePattern)]
          
          const parsedMessages: Message[] = matches.map((match, idx) => ({
            id: `${match[2].toLowerCase()}-${Date.now()}-${idx}`,
            role: match[2] === 'USER' ? 'user' : 'assistant',
            content: match[3].trim(),
            timestamp: new Date()
          }))
          
          setMessages(parsedMessages)
        }
      }
    } catch (error) {
      console.error('Failed to load session history:', error)
    }
  }

  const startSession = async () => {
    try {
      const response = await api.startChatSession()
      if (response.ok) {
        const data = await response.json()
        setSessionId(data.session_id)
        localStorage.setItem('fundfish_session_id', data.session_id)
      }
    } catch (error) {
      console.error('Failed to start session:', error)
    }
  }

  const sendMessage = useCallback(async (messageText?: string) => {
    const text = messageText || input
    if (!text.trim() || !sessionId || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }

    try {
      const response = await api.sendChatMessage(sessionId, userMessage.content)
      if (response.ok) {
        const data = await response.json()
        setMessages(prev => [...prev, {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.response || "I couldn't process that request.",
          timestamp: new Date()
        }])
      } else {
        throw new Error('Request failed')
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: "Something went wrong. Please try again.",
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }, [input, sessionId, isLoading])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getPromptIcon = (icon: string) => {
    switch (icon) {
      case 'search':
        return <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      case 'calendar':
        return <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      case 'edit':
        return <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      case 'chart':
        return <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      default:
        return null
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-gray-200 border-t-perscholas-primary rounded-full animate-spin" />
          <span className="text-sm text-gray-500">Loading...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) return null

  const hasMessages = messages.length > 0

  return (
    <div className="h-screen bg-white flex flex-col overflow-hidden">
      {/* Messages Area */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto pb-4">
        {!hasMessages ? (
          /* Empty State */
          <div className="h-full flex flex-col items-center justify-center px-4 py-12">
            <div className="w-16 h-16 rounded-2xl bg-perscholas-primary flex items-center justify-center mb-6 shadow-lg overflow-hidden">
              <img src="/logo.png" alt="FundFish" className="w-10 h-10 object-contain rounded-lg" />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">FundFish Agent</h1>
            <p className="text-gray-500 text-center max-w-md mb-10">
              Your AI assistant for grant discovery, proposal writing, and funding strategy.
            </p>
            
            <div className="w-full max-w-2xl grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(prompt.text)}
                  className="group flex items-start gap-3 p-4 rounded-xl border border-gray-200 hover:border-perscholas-primary/30 hover:bg-perscholas-primary/5 text-left transition-all duration-200"
                >
                  <div className="w-8 h-8 rounded-lg bg-gray-100 group-hover:bg-perscholas-primary/10 flex items-center justify-center flex-shrink-0 transition-colors">
                    <svg className="w-4 h-4 text-gray-500 group-hover:text-perscholas-primary transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      {getPromptIcon(prompt.icon)}
                    </svg>
                  </div>
                  <span className="text-sm text-gray-700 group-hover:text-gray-900 leading-relaxed">
                    {prompt.text}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Messages */
          <div className="max-w-3xl mx-auto px-4 py-6">
            <div className="space-y-6">
              {messages.map((message) => (
                <div key={message.id} className={`group ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                  {message.role === 'user' ? (
                    <div className="max-w-[85%] bg-perscholas-primary text-white rounded-2xl rounded-br-sm px-4 py-3">
                      <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    </div>
                  ) : (
                    <div className="flex gap-4">
                      <div className="w-8 h-8 rounded-lg bg-perscholas-primary flex items-center justify-center flex-shrink-0 shadow-sm overflow-hidden">
                        <img src="/logo.png" alt="FundFish" className="w-5 h-5 object-contain rounded" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="prose prose-sm max-w-none text-gray-700 prose-p:leading-relaxed prose-headings:text-gray-900 prose-a:text-perscholas-primary prose-strong:text-gray-900 prose-code:text-perscholas-primary prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                        <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => copyToClipboard(message.content, message.id)}
                            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            {copiedId === message.id ? (
                              <>
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Copied
                              </>
                            ) : (
                              <>
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-lg bg-perscholas-primary flex items-center justify-center flex-shrink-0 shadow-sm overflow-hidden">
                    <img src="/logo.png" alt="FundFish" className="w-5 h-5 object-contain rounded" />
                  </div>
                  <div className="flex items-center gap-1.5 py-3">
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-pulse" />
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-gray-300 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
            </div>
            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-gray-100 bg-white/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="relative flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 focus-within:border-perscholas-primary/50 focus-within:ring-2 focus-within:ring-perscholas-primary/10 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about grants, proposals, or funding..."
              className="flex-1 resize-none bg-transparent px-4 py-4 focus:outline-none text-[15px] text-gray-900 placeholder-gray-400 max-h-[200px] min-h-[56px]"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="m-2 p-2.5 bg-perscholas-primary text-white rounded-xl hover:bg-perscholas-dark disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 disabled:hover:bg-perscholas-primary"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-gray-400 text-center mt-3">
            FundFish may make mistakes. Verify important information.
          </p>
        </div>
      </div>
    </div>
  )
}
