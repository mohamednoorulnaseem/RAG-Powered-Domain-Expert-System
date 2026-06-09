/**
 * DocumentSidebar.jsx — Left Panel
 *
 * Features:
 *  - Drag-and-drop file upload (PDF, TXT, DOCX)
 *  - Upload progress indicator per file
 *  - List of uploaded documents with file size and chunk count
 *  - Delete button per document
 *  - Empty state when no documents
 */

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  HiOutlineDocumentText,
  HiOutlineTrash,
  HiOutlineCloudArrowUp,
  HiOutlineDocumentPlus,
} from 'react-icons/hi2'

function DocumentSidebar({
  documents,
  onUploadComplete,
  onDeleteDocument,
  apiKey,
  chunkSize,
  chunkOverlap,
  apiBase,
}) {
  const [uploadingFiles, setUploadingFiles] = useState([])
  const [error, setError] = useState(null)

  /**
   * Format file size into human-readable string.
   */
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  /**
   * Get the icon color based on file extension.
   */
  const getFileColor = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf': return '#ff5c5c'
      case 'docx': return '#4a9eff'
      case 'txt': return '#00e5a0'
      default: return '#9ca0b4'
    }
  }

  /**
   * Upload a single file to the backend.
   * Updates progress state as the upload proceeds.
   */
  const uploadFile = async (file) => {
    const fileId = `upload_${Date.now()}_${Math.random().toString(36).slice(2)}`

    // Add to uploading list
    setUploadingFiles(prev => [...prev, {
      id: fileId,
      name: file.name,
      progress: 0,
      status: 'uploading',
    }])

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (apiKey) formData.append('api_key', apiKey)
      formData.append('chunk_size', chunkSize.toString())
      formData.append('chunk_overlap', chunkOverlap.toString())

      // Use XMLHttpRequest for progress tracking
      const result = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest()

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100)
            setUploadingFiles(prev =>
              prev.map(f => f.id === fileId ? { ...f, progress: pct } : f)
            )
          }
        })

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText))
          } else {
            try {
              const errData = JSON.parse(xhr.responseText)
              reject(new Error(errData.detail || `Upload failed (${xhr.status})`))
            } catch {
              reject(new Error(`Upload failed with status ${xhr.status}`))
            }
          }
        })

        xhr.addEventListener('error', () => reject(new Error('Network error during upload')))
        xhr.addEventListener('abort', () => reject(new Error('Upload cancelled')))

        xhr.open('POST', `${apiBase}/upload`)
        xhr.send(formData)
      })

      // Update status to complete
      setUploadingFiles(prev =>
        prev.map(f => f.id === fileId ? { ...f, progress: 100, status: 'complete' } : f)
      )

      // Notify parent of the new document
      onUploadComplete(result)

      // Remove from uploading list after a brief delay
      setTimeout(() => {
        setUploadingFiles(prev => prev.filter(f => f.id !== fileId))
      }, 1500)

    } catch (err) {
      console.error('Upload error:', err)
      setUploadingFiles(prev =>
        prev.map(f => f.id === fileId ? { ...f, status: 'error', error: err.message } : f)
      )
      setError(err.message)

      // Remove error state after 5 seconds
      setTimeout(() => {
        setUploadingFiles(prev => prev.filter(f => f.id !== fileId))
        setError(null)
      }, 5000)
    }
  }

  /**
   * Handle dropped or selected files.
   */
  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setError(null)

    if (rejectedFiles.length > 0) {
      const reasons = rejectedFiles.map(r =>
        r.errors.map(e => e.message).join(', ')
      ).join('; ')
      setError(`Rejected: ${reasons}`)
      return
    }

    // Upload each file
    acceptedFiles.forEach(file => uploadFile(file))
  }, [apiKey, chunkSize, chunkOverlap, apiBase])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  // ── Render ────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2">
          <HiOutlineDocumentPlus className="text-accent" size={22} />
          <h2 className="text-base font-semibold text-text-primary">Documents</h2>
        </div>
        <p className="text-xs text-text-muted mt-1">
          Upload PDF, TXT, or DOCX files
        </p>
      </div>

      {/* Upload Dropzone */}
      <div className="px-4 py-3">
        <div
          {...getRootProps()}
          className={`dropzone ${isDragActive ? 'active' : ''}`}
          id="file-dropzone"
        >
          <input {...getInputProps()} />
          <HiOutlineCloudArrowUp
            size={32}
            className={`mx-auto mb-2 transition-colors ${
              isDragActive ? 'text-accent' : 'text-text-muted'
            }`}
          />
          {isDragActive ? (
            <p className="text-sm text-accent font-medium">Drop files here...</p>
          ) : (
            <>
              <p className="text-sm text-text-secondary">
                Drag & drop files here
              </p>
              <p className="text-xs text-text-muted mt-1">
                or click to browse
              </p>
            </>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-4 mb-2 px-3 py-2 rounded-lg bg-error-dim text-error text-xs animate-fade-in">
          {error}
        </div>
      )}

      {/* Upload Progress */}
      {uploadingFiles.length > 0 && (
        <div className="px-4 space-y-2 mb-2">
          {uploadingFiles.map(file => (
            <div
              key={file.id}
              className="px-3 py-2 rounded-lg bg-bg-tertiary animate-fade-in"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-secondary truncate max-w-[180px]">
                  {file.name}
                </span>
                <span className={`text-xs font-medium ${
                  file.status === 'error' ? 'text-error' :
                  file.status === 'complete' ? 'text-accent' :
                  'text-text-muted'
                }`}>
                  {file.status === 'error' ? 'Failed' :
                   file.status === 'complete' ? '✓ Done' :
                   `${file.progress}%`}
                </span>
              </div>
              {file.status === 'uploading' && (
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${file.progress}%` }}
                  />
                </div>
              )}
              {file.status === 'error' && (
                <p className="text-xs text-error/70 mt-1">{file.error}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Document List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {documents.length === 0 && uploadingFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-bg-tertiary flex items-center justify-center mb-4">
              <HiOutlineDocumentText size={28} className="text-text-muted" />
            </div>
            <p className="text-sm text-text-secondary font-medium">
              No documents yet
            </p>
            <p className="text-xs text-text-muted mt-1 max-w-[200px]">
              Upload a document to get started with your domain expert
            </p>
          </div>
        ) : (
          <div className="space-y-2 mt-1">
            {documents.map((doc, index) => (
              <div
                key={doc.id}
                className="group flex items-center gap-3 px-3 py-2.5 rounded-xl bg-bg-tertiary/50 hover:bg-bg-hover border border-transparent hover:border-border-light transition-all duration-200 animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {/* File icon with color based on type */}
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: `${getFileColor(doc.filename)}15` }}
                >
                  <HiOutlineDocumentText
                    size={16}
                    style={{ color: getFileColor(doc.filename) }}
                  />
                </div>

                {/* File info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate font-medium">
                    {doc.filename}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <span>{formatFileSize(doc.file_size)}</span>
                    <span>•</span>
                    <span>{doc.chunk_count} chunks</span>
                  </div>
                </div>

                {/* Delete button */}
                <button
                  onClick={() => onDeleteDocument(doc.id)}
                  className="p-1.5 rounded-lg text-text-muted hover:text-error hover:bg-error-dim opacity-0 group-hover:opacity-100 transition-all duration-200"
                  title="Delete document"
                  id={`delete-doc-${doc.id}`}
                >
                  <HiOutlineTrash size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default DocumentSidebar
