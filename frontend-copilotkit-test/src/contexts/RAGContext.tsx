import { createContext, useContext, useState, ReactNode } from 'react'
import axios from 'axios'

interface RAGContextType {
  isReady: boolean
  documentsCount: number
  processText: (text: string) => Promise<void>
  clearDocuments: () => Promise<void>
  getStatus: () => Promise<void>
  loading: boolean
  error: string | null
}

const RAGContext = createContext<RAGContextType | undefined>(undefined)

export const useRAG = () => {
  const context = useContext(RAGContext)
  if (context === undefined) {
    throw new Error('useRAG must be used within a RAGProvider')
  }
  return context
}

interface RAGProviderProps {
  children: ReactNode
}

export const RAGProvider: React.FC<RAGProviderProps> = ({ children }) => {
  const [isReady, setIsReady] = useState(false)
  const [documentsCount, setDocumentsCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const API_BASE = '/api'

  const processText = async (text: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.post(`${API_BASE}/docs/process`, {
        text: text
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (response.data.success) {
        await getStatus()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process text')
    } finally {
      setLoading(false)
    }
  }

  const clearDocuments = async () => {
    setLoading(true)
    setError(null)
    
    try {
      await axios.post(`${API_BASE}/docs/clear`)
      setIsReady(false)
      setDocumentsCount(0)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to clear documents')
    } finally {
      setLoading(false)
    }
  }

  const getStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/docs/status`)
      const data = response.data
      setIsReady(data.is_ready)
      setDocumentsCount(data.documents_count)
    } catch (err: any) {
      console.error('Failed to get status:', err)
    }
  }

  const value: RAGContextType = {
    isReady,
    documentsCount,
    processText,
    clearDocuments,
    getStatus,
    loading,
    error,
  }

  return <RAGContext.Provider value={value}>{children}</RAGContext.Provider>
}
