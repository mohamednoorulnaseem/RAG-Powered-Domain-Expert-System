/**
 * App.jsx — Root Application Component
 *
 * Three-panel layout:
 *  - Left: Document Sidebar (upload & list)
 *  - Center: Chat Interface (messages + input)
 *  - Right: Settings Panel (collapsible)
 *
 * All state (documents, messages, settings) lives here and is
 * passed down as props. No external state management needed.
 */

import { useState, useCallback, useEffect } from 'react'
import DocumentSidebar from './components/DocumentSidebar.jsx'
import ChatInterface from './components/ChatInterface.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import { HiCog6Tooth, HiXMark, HiBars3 } from 'react-icons/hi2'

// API base URL — /api prefix is used in both dev (Vite proxy) and prod (nginx proxy)
const API_BASE = '/api'

function App() {
  // ── State ─────────────────────────────────────────────
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState([])
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).slice(2)}`)

  // Settings state — stored in memory only, never persisted
  const [settings, setSettings] = useState({
    apiKey: '',
    model: 'gpt-4o',
    chunkSize: 1000,
    chunkOverlap: 200,
    topK: 5,
    temperature: 0.1,
  })

  // ── Document Management ───────────────────────────────

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`)
      if (res.ok) {
        const data = await res.json()
        setDocuments(data)
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const handleUploadComplete = useCallback((newDoc) => {
    setDocuments(prev => [...prev, newDoc])
  }, [])

  const handleDeleteDocument = useCallback(async (docId) => {
    try {
      const params = new URLSearchParams()
      if (settings.apiKey) params.set('api_key', settings.apiKey)

      const res = await fetch(`${API_BASE}/documents/${docId}?${params}`, {
        method: 'DELETE',
      })

      if (res.ok) {
        setDocuments(prev => prev.filter(d => d.id !== docId))
      } else {
        const err = await res.json()
        alert(err.detail || 'Failed to delete document')
      }
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Failed to delete document')
    }
  }, [settings.apiKey])

  // ── Chat ──────────────────────────────────────────────

  const handleSendMessage = useCallback(async (message) => {
    if (!message.trim() || isLoading) return

    // Add user message immediately
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    // Prepare the AI message placeholder for streaming
    const aiMsgId = Date.now() + 1
    const aiMsg = {
      id: aiMsgId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    setMessages(prev => [...prev, aiMsg])

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          session_id: sessionId,
          api_key: settings.apiKey || undefined,
          model: settings.model,
          top_k: settings.topK,
          temperature: settings.temperature,
          chunk_size: settings.chunkSize,
          chunk_overlap: settings.chunkOverlap,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Server error: ${response.status}`)
      }

      // Read the SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE events from the buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'token') {
                setMessages(prev =>
                  prev.map(m =>
                    m.id === aiMsgId
                      ? { ...m, content: m.content + data.content }
                      : m
                  )
                )
              } else if (data.type === 'done') {
                setMessages(prev =>
                  prev.map(m =>
                    m.id === aiMsgId
                      ? { ...m, sources: data.sources || [], isStreaming: false }
                      : m
                  )
                )
              } else if (data.type === 'error') {
                setMessages(prev =>
                  prev.map(m =>
                    m.id === aiMsgId
                      ? { ...m, content: `Error: ${data.content}`, isStreaming: false, isError: true }
                      : m
                  )
                )
              }
            } catch (parseErr) {
              // Skip malformed SSE events
            }
          }
        }
      }

      // Ensure streaming flag is cleared
      setMessages(prev =>
        prev.map(m =>
          m.id === aiMsgId ? { ...m, isStreaming: false } : m
        )
      )
    } catch (err) {
      console.error('Chat error:', err)
      setMessages(prev =>
        prev.map(m =>
          m.id === aiMsgId
            ? {
                ...m,
                content: err.message || 'Failed to get response. Check your API key and try again.',
                isStreaming: false,
                isError: true,
              }
            : m
        )
      )
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, sessionId, settings])

  const handleClearChat = useCallback(async () => {
    setMessages([])
    try {
      await fetch(`${API_BASE}/chat/history?session_id=${sessionId}`, {
        method: 'DELETE',
      })
    } catch (err) {
      console.error('Failed to clear history:', err)
    }
  }, [sessionId])

  // ── Render ────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden bg-bg-primary">
      {/* Mobile sidebar toggle */}
      <button
        id="sidebar-toggle"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-bg-secondary border border-border text-text-secondary hover:text-accent transition-colors md:hidden"
      >
        {isSidebarOpen ? <HiXMark size={20} /> : <HiBars3 size={20} />}
      </button>

      {/* Left Sidebar — Document Upload & List */}
      <aside
        className={`
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          fixed md:relative md:translate-x-0
          z-40 h-full w-80 flex-shrink-0
          bg-bg-secondary border-r border-border
          transition-transform duration-300 ease-in-out
        `}
      >
        <DocumentSidebar
          documents={documents}
          onUploadComplete={handleUploadComplete}
          onDeleteDocument={handleDeleteDocument}
          apiKey={settings.apiKey}
          chunkSize={settings.chunkSize}
          chunkOverlap={settings.chunkOverlap}
          apiBase={API_BASE}
        />
      </aside>

      {/* Mobile sidebar overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-bg-secondary/50 backdrop-blur-sm">
          <div className="flex items-center gap-3 ml-10 md:ml-0">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse-glow" />
            <h1 className="text-lg font-semibold text-text-primary">
              RAG Domain Expert
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-accent-dim text-accent border border-accent/20">
              {documents.length} doc{documents.length !== 1 ? 's' : ''}
            </span>
          </div>
          <button
            id="settings-toggle"
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
            className={`p-2 rounded-lg transition-all duration-200 ${
              isSettingsOpen
                ? 'bg-accent/20 text-accent'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
            }`}
            title="Settings"
          >
            <HiCog6Tooth size={20} className={isSettingsOpen ? 'animate-spin' : ''} style={isSettingsOpen ? { animationDuration: '3s' } : {}} />
          </button>
        </header>

        {/* Chat Interface */}
        <ChatInterface
          messages={messages}
          onSendMessage={handleSendMessage}
          onClearChat={handleClearChat}
          isLoading={isLoading}
          hasDocuments={documents.length > 0}
        />
      </main>

      {/* Right Panel — Settings (Collapsible) */}
      <aside
        className={`
          ${isSettingsOpen ? 'translate-x-0 w-80' : 'translate-x-full w-0'}
          fixed md:relative right-0 top-0 h-full
          z-40 flex-shrink-0
          bg-bg-secondary border-l border-border
          transition-all duration-300 ease-in-out
          overflow-hidden
        `}
      >
        <SettingsPanel
          settings={settings}
          onSettingsChange={setSettings}
          onClose={() => setIsSettingsOpen(false)}
        />
      </aside>

      {/* Settings overlay on mobile */}
      {isSettingsOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setIsSettingsOpen(false)}
        />
      )}
    </div>
  )
}

export default App
