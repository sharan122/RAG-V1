
import { useState } from 'react'
import { X, Upload, Trash2, FileText, Settings } from 'lucide-react'
import { useRAG } from '../contexts/RAGContext'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { isReady, documentsCount, processText, clearDocuments, loading } = useRAG()

  const [textInput, setTextInput] = useState('')

  const handleProcessText = () => {
    if (textInput.trim()) {
      processText(textInput.trim())
      setTextInput('')
    }
  }

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-gray-600 bg-opacity-75 z-40 md:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Documentation</h2>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 md:hidden"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          
          {/* Content */}
          <div className="flex-1 p-4 space-y-4">
            {/* Status */}
            <div className="card">
              <h3 className="text-sm font-medium text-gray-900 mb-2">System Status</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Status:</span>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    isReady ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {isReady ? 'Ready' : 'Not Ready'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Documents:</span>
                  <span className="text-sm font-medium text-gray-900">{documentsCount}</span>
                </div>
              </div>
            </div>
            
            {/* Actions */}
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Paste Documentation Text
                </label>
                <textarea
                  className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none text-sm"
                  placeholder="Paste your API documentation text here..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                />
                <button 
                  className="btn-primary w-full flex items-center justify-center mt-2"
                  disabled={loading || !textInput.trim()}
                  onClick={handleProcessText}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Process Text
                </button>
              </div>
              
              <button
                onClick={clearDocuments}
                disabled={!isReady || loading}
                className="btn-secondary w-full flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear All
              </button>
            </div>
            
            {/* Quick Actions */}
            <div className="card">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button className="w-full text-left p-2 text-sm text-gray-600 hover:bg-gray-50 rounded-md transition-colors">
                  <FileText className="h-4 w-4 inline mr-2" />
                  View Documentation
                </button>
                <button className="w-full text-left p-2 text-sm text-gray-600 hover:bg-gray-50 rounded-md transition-colors">
                  <Settings className="h-4 w-4 inline mr-2" />
                  Settings
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default Sidebar
