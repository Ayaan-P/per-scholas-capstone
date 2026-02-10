'use client'

import { useState, useRef, useCallback } from 'react'
import { supabase } from '../utils/supabaseClient'

interface UploadedDocument {
  id: string | null
  filename: string
  file_type: string
  file_size: number
  text_length: number
}

interface DocumentUploaderProps {
  onUploadComplete: (documents: UploadedDocument[]) => void
  onError: (error: string) => void
  existingDocuments?: { id: string; filename: string; file_type: string; uploaded_at: string }[]
  onDeleteDocument?: (documentId: string) => void
}

export function DocumentUploader({
  onUploadComplete,
  onError,
  existingDocuments = [],
  onDeleteDocument
}: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: 'pending' | 'uploading' | 'done' | 'error' }>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
  const allowedExtensions = ['.pdf', '.docx', '.txt']

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const validateFiles = (files: File[]): File[] => {
    const valid: File[] = []
    for (const file of files) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      if (allowedTypes.includes(file.type) || allowedExtensions.includes(ext)) {
        if (file.size > 50 * 1024 * 1024) {
          onError(`File ${file.name} exceeds 50MB limit`)
        } else {
          valid.push(file)
        }
      } else {
        onError(`File ${file.name} has unsupported type. Allowed: PDF, DOCX, TXT`)
      }
    }
    return valid
  }

  const uploadFiles = useCallback(async (files: File[]) => {
    const validFiles = validateFiles(files)
    if (validFiles.length === 0) return

    setUploading(true)
    const progress: { [key: string]: 'pending' | 'uploading' | 'done' | 'error' } = {}
    validFiles.forEach(f => progress[f.name] = 'pending')
    setUploadProgress(progress)

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      if (!token) {
        onError('Not authenticated')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const formData = new FormData()
      validFiles.forEach(file => formData.append('files', file))

      // Update progress to uploading
      setUploadProgress(prev => {
        const updated = { ...prev }
        Object.keys(updated).forEach(k => updated[k] = 'uploading')
        return updated
      })

      const response = await fetch(`${apiUrl}/api/organization/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const result = await response.json()

      // Update progress to done
      setUploadProgress(prev => {
        const updated = { ...prev }
        Object.keys(updated).forEach(k => updated[k] = 'done')
        return updated
      })

      onUploadComplete(result.uploaded)
    } catch (error) {
      setUploadProgress(prev => {
        const updated = { ...prev }
        Object.keys(updated).forEach(k => updated[k] = 'error')
        return updated
      })
      onError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setUploading(false)
      setTimeout(() => setUploadProgress({}), 2000)
    }
  }, [onUploadComplete, onError])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    uploadFiles(files)
  }, [uploadFiles])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    uploadFiles(files)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [uploadFiles])

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf': return 'PDF'
      case 'docx': return 'DOC'
      case 'txt': return 'TXT'
      default: return 'FILE'
    }
  }

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center transition-all cursor-pointer
          ${isDragging
            ? 'border-perscholas-primary bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50'
          }
          ${uploading ? 'pointer-events-none opacity-60' : ''}
        `}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="space-y-3">
          <div className="text-4xl">
            uploading ? 'Uploading...' : 'Upload'
          </div>
          <div>
            <p className="text-gray-700 font-medium">
              {uploading ? 'Uploading documents...' : 'Drop your organization docs here'}
            </p>
            <p className="text-gray-500 text-sm mt-1">
              Annual reports, 990s, grant proposals, mission statements
            </p>
          </div>
          {!uploading && (
            <button
              type="button"
              className="px-4 py-2 bg-perscholas-primary text-white rounded-lg hover:bg-perscholas-dark transition-colors text-sm font-medium"
            >
              Browse Files
            </button>
          )}
          <p className="text-xs text-gray-400">
            Supported: PDF, DOCX, TXT (max 50MB each)
          </p>
        </div>
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="space-y-2">
          {Object.entries(uploadProgress).map(([filename, status]) => (
            <div
              key={filename}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
            >
              <span className="text-lg">
                {status === 'pending' && '...'}
                {status === 'uploading' && '...'}
                {status === 'done' && 'Done'}
                {status === 'error' && 'Error'}
              </span>
              <span className="flex-1 text-sm text-gray-700 truncate">{filename}</span>
              <span className="text-xs text-gray-500">
                {status === 'pending' && 'Waiting...'}
                {status === 'uploading' && 'Uploading...'}
                {status === 'done' && 'Done'}
                {status === 'error' && 'Failed'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Existing Documents */}
      {existingDocuments.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Uploaded Documents</h4>
          <div className="space-y-2">
            {existingDocuments.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg"
              >
                <span className="text-lg">{getFileIcon(doc.file_type)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 truncate">{doc.filename}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </p>
                </div>
                {onDeleteDocument && (
                  <button
                    onClick={() => onDeleteDocument(doc.id)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                    title="Delete document"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
