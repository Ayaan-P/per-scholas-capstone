'use client'

import { useState, useRef, useEffect } from 'react'
import { api } from '../../utils/api'
import { useAuth } from '../../context/AuthContext'
import { useRouter } from 'next/navigation'

interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: Date
}

export default function ChatPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [hasProfile, setHasProfile] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/chat')
    }
  }, [isAuthenticated, authLoading, router])

  // Start session on mount
  useEffect(() => {
    if (isAuthenticated && !sessionId) {
      startSession()
    }
  }, [isAuthenticated])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`
    }
  }, [input])

  const startSession = async () => {
    try {
      const response = await api.startChatSession()
      if (response.ok) {
        const data = await response.json()
        setSessionId(data.session_id)
        setHasProfile(data.has_profile)
        
        // Add greeting message
        if (data.greeting) {
          setMessages([{
            id: 'greeting',
            role: 'agent',
            content: data.greeting,
            timestamp: new Date()
          }])
        }
      }
    } catch (error) {
      console.error('Failed to start session:', error)
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await api.sendChatMessage(sessionId, userMessage.content)
      
      if (response.ok) {
        const data = await response.json()
        
        const agentMessage: Message = {
          id: `agent-${Date.now()}`,
          role: 'agent',
          content: data.response || "I'm processing your request...",
          timestamp: new Date()
        }
        
        setMessages(prev => [...prev, agentMessage])
      } else {
        throw new Error('Failed to send message')
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'agent',
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date()
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-perscholas-primary"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null // Will redirect
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4 sm:px-6">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="bg-perscholas-primary p-2.5 rounded-xl shadow-md">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">FundFish Assistant</h1>
            <p className="text-sm text-gray-500">AI-powered grant discovery & proposal help</p>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-perscholas-primary text-white rounded-br-md'
                    : 'bg-white border border-gray-200 shadow-sm rounded-bl-md'
                }`}
              >
                {message.role === 'agent' && (
                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100">
                    <div className="w-6 h-6 rounded-full bg-perscholas-primary/10 flex items-center justify-center">
                      <svg className="w-4 h-4 text-perscholas-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <span className="text-xs font-semibold text-perscholas-primary">FundFish</span>
                  </div>
                )}
                <div className={`text-sm leading-relaxed whitespace-pre-wrap ${
                  message.role === 'user' ? 'text-white' : 'text-gray-700'
                }`}>
                  {message.content}
                </div>
                <div className={`text-xs mt-2 ${
                  message.role === 'user' ? 'text-white/70' : 'text-gray-400'
                }`}>
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 shadow-sm rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-perscholas-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-perscholas-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-perscholas-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about grants, get proposal help, or search opportunities..."
                className="w-full resize-none rounded-xl border border-gray-300 px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-perscholas-primary/20 focus:border-perscholas-primary transition-all text-sm"
                rows={1}
                disabled={isLoading}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 bg-perscholas-primary text-white p-3 rounded-xl hover:bg-perscholas-dark disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>

      {/* Suggested Prompts (show when no messages beyond greeting) */}
      {messages.length <= 1 && (
        <div className="bg-white border-t border-gray-100 px-4 py-4">
          <div className="max-w-4xl mx-auto">
            <p className="text-xs font-semibold text-gray-500 mb-3">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {[
                "Find grants for workforce development",
                "What grants match our tech training programs?",
                "Help me write a project narrative",
                "Show grants due in the next 30 days"
              ].map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInput(prompt)}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
