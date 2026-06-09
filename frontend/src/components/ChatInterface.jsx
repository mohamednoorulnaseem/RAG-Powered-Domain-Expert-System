/**
 * ChatInterface.jsx — Central Chat Panel
 *
 * Features:
 *  - Auto-scrolling message list
 *  - Text input with send button
 *  - Loading indicator while streaming
 *  - Clear chat button
 *  - Empty state when no documents uploaded
 *  - Keyboard shortcuts (Enter to send, Shift+Enter for newline)
 */

import { useState, useRef, useEffect } from 'react'
import {
  HiPaperAirplane,
  HiOutlineTrash,
  HiOutlineSparkles,
  HiOutlineDocumentArrowUp,
} from 'react-icons/hi2'
import MessageBubble from './MessageBubble.jsx'

function ChatInterface({
  messages,
  onSendMessage,
  onClearChat,
  isLoading,
  hasDocuments,
}) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !isLoading && hasDocuments) {
      onSendMessage(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // ── Empty State (no documents) ────────────────────────

  if (!hasDocuments && messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 animate-fade-in">
        <div className="relative mb-6">
          <div className="w-20 h-20 rounded-3xl bg-bg-tertiary flex items-center justify-center">
            <HiOutlineDocumentArrowUp size={36} className="text-text-muted" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-xl bg-accent/20 flex items-center justify-center">
            <HiOutlineSparkles size={16} className="text-accent" />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-text-primary mb-2">
          Upload a document to get started
        </h2>
        <p className="text-sm text-text-muted text-center max-w-md leading-relaxed">
          Drag and drop a PDF, TXT, or DOCX file into the sidebar.
          Then ask any question — the AI will find answers directly from your documents.
        </p>

        {/* Feature highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8 max-w-2xl w-full">
          {[
            {
              icon: '📄',
              title: 'Upload Documents',
              desc: 'Support for PDF, TXT, and DOCX files up to 50MB',
            },
            {
              icon: '🔍',
              title: 'Smart Search',
              desc: 'Vector similarity search finds the most relevant content',
            },
            {
              icon: '✨',
              title: 'Grounded Answers',
              desc: 'AI answers only from your documents — no hallucinations',
            },
          ].map((feature, i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-bg-secondary border border-border hover:border-border-light transition-colors"
            >
              <div className="text-2xl mb-2">{feature.icon}</div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                {feature.title}
              </h3>
              <p className="text-xs text-text-muted leading-relaxed">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Chat View ─────────────────────────────────────────

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-4">
        {messages.length === 0 && hasDocuments && (
          <div className="flex flex-col items-center justify-center h-full animate-fade-in">
            <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
              <HiOutlineSparkles size={24} className="text-accent" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-1">
              Ask a question
            </h3>
            <p className="text-sm text-text-muted text-center max-w-sm">
              Your documents are ready. Ask anything about their content and get AI-powered, citation-backed answers.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-4 md:px-8 pb-4 pt-2">
        {/* Clear Chat Button */}
        {messages.length > 0 && (
          <div className="flex justify-center mb-2">
            <button
              onClick={onClearChat}
              className="flex items-center gap-1.5 px-3 py-1 text-xs text-text-muted hover:text-error rounded-full hover:bg-error-dim transition-all duration-200"
              id="clear-chat-btn"
            >
              <HiOutlineTrash size={12} />
              Clear chat
            </button>
          </div>
        )}

        {/* Input Form */}
        <form
          onSubmit={handleSubmit}
          className="flex items-end gap-3 p-3 rounded-2xl bg-bg-secondary border border-border focus-within:border-accent/50 transition-colors"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDocuments
                ? 'Ask a question about your documents...'
                : 'Upload a document first...'
            }
            disabled={!hasDocuments || isLoading}
            rows={1}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder-text-muted resize-none outline-none min-h-[24px] max-h-[120px] py-1 disabled:opacity-50"
            style={{
              height: 'auto',
              overflowY: input.split('\n').length > 4 ? 'auto' : 'hidden',
            }}
            onInput={(e) => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
            id="chat-input"
          />

          <button
            type="submit"
            disabled={!input.trim() || isLoading || !hasDocuments}
            className={`p-2 rounded-xl transition-all duration-200 flex-shrink-0 ${
              input.trim() && !isLoading && hasDocuments
                ? 'bg-accent text-bg-primary hover:bg-accent-hover shadow-lg shadow-accent/20'
                : 'bg-bg-tertiary text-text-muted cursor-not-allowed'
            }`}
            id="send-btn"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
            ) : (
              <HiPaperAirplane size={18} />
            )}
          </button>
        </form>

        <p className="text-center text-xs text-text-muted mt-2">
          AI answers are grounded in your uploaded documents only.
        </p>
      </div>
    </div>
  )
}

export default ChatInterface
