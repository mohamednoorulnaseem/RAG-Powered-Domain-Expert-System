/**
 * MessageBubble.jsx — Chat Message Component
 *
 * Renders a single chat message with:
 *  - User messages: right-aligned, accent colored
 *  - AI messages: left-aligned, dark background, with markdown rendering
 *  - Source citations below AI messages
 *  - Streaming animation for in-progress responses
 *  - Error state styling
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { HiOutlineDocumentText, HiOutlineExclamationTriangle } from 'react-icons/hi2'

function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError
  const isStreaming = message.isStreaming

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in mb-4`}
    >
      <div
        className={`max-w-[80%] md:max-w-[70%] ${
          isUser
            ? 'animate-slide-right'
            : 'animate-slide-left'
        }`}
      >
        {/* Role label */}
        <div
          className={`text-xs font-medium mb-1 px-1 ${
            isUser ? 'text-right text-accent' : 'text-left text-text-muted'
          }`}
        >
          {isUser ? 'You' : 'AI Expert'}
        </div>

        {/* Message bubble */}
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-user-bubble text-user-text rounded-br-md'
              : isError
                ? 'bg-error-dim border border-error/20 text-error rounded-bl-md'
                : 'bg-ai-bubble border border-border rounded-bl-md'
          }`}
        >
          {isError && (
            <div className="flex items-center gap-2 mb-2">
              <HiOutlineExclamationTriangle size={14} />
              <span className="text-xs font-medium">Error</span>
            </div>
          )}

          {isUser ? (
            <p className="text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="markdown-content text-text-primary">
              {message.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              ) : isStreaming ? (
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              ) : null}

              {/* Blinking cursor while streaming */}
              {isStreaming && message.content && (
                <span className="inline-block w-0.5 h-4 bg-accent ml-0.5 animate-pulse align-middle" />
              )}
            </div>
          )}
        </div>

        {/* Source Citations — shown below AI messages */}
        {!isUser && message.sources && message.sources.length > 0 && !isStreaming && (
          <div className="mt-2 space-y-1 animate-fade-in">
            <p className="text-xs text-text-muted px-1 font-medium">Sources:</p>
            {message.sources.map((source, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 px-3 py-2 rounded-lg bg-bg-tertiary/50 border border-border/50 hover:border-accent/30 transition-colors"
              >
                <HiOutlineDocumentText
                  size={14}
                  className="text-accent flex-shrink-0 mt-0.5"
                />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-text-secondary truncate">
                    {source.document}
                    {source.page !== undefined && source.page !== null && (
                      <span className="text-text-muted ml-1">
                        · Page {Number(source.page) + 1}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-text-muted mt-0.5 line-clamp-2">
                    {source.content_preview}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default MessageBubble
