import { useEffect, useState } from 'react'
import { useRAG } from '../contexts/RAGContext'
import { MessageCircle, FileText, Code, Zap } from 'lucide-react'

const MainContent: React.FC = () => {
  const { isReady, documentsCount, getStatus, loading, error } = useRAG()
  const [activeTab, setActiveTab] = useState<'chat' | 'docs' | 'curl'>('chat')

  useEffect(() => {
    getStatus()
  }, [getStatus])

  const tabs = [
    { id: 'chat', label: 'AI Chat', icon: MessageCircle, description: 'Ask questions about your documentation' },
    { id: 'docs', label: 'Documentation', icon: FileText, description: 'View and manage uploaded documents' },
    { id: 'curl', label: 'cURL Generator', icon: Code, description: 'Generate cURL commands for your APIs' },
  ]

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return (
          <div className="h-full flex flex-col">
            <div className="flex-1 min-h-0 p-6">
              <div className="card">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">AI Chat Interface</h2>
                <p className="text-gray-600 mb-4">
                  This will be replaced with CopilotKit chat interface once the backend is ready.
                </p>
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <textarea 
                    className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none"
                    placeholder="Ask me anything about your API documentation..."
                  />
                  <button className="mt-3 btn-primary">
                    Send Message
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
      
      case 'docs':
        return (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Documentation Status</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-primary-600">{documentsCount}</div>
                  <div className="text-sm text-gray-600">Documents</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className={`text-2xl font-bold ${isReady ? 'text-green-600' : 'text-yellow-600'}`}>
                    {isReady ? 'Ready' : 'Not Ready'}
                  </div>
                  <div className="text-sm text-gray-600">System Status</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">RAG</div>
                  <div className="text-sm text-gray-600">AI System</div>
                </div>
              </div>
            </div>
            
            {error && (
              <div className="card border-red-200 bg-red-50">
                <div className="text-red-800">
                  <strong>Error:</strong> {error}
                </div>
              </div>
            )}
            
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Add Documentation Text</h3>
              <p className="text-gray-600 mb-4">
                Paste your API documentation text in the sidebar to enable AI-powered assistance and cURL generation.
              </p>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <FileText className="mx-auto h-12 w-12 text-gray-400" />
                <div className="mt-2">
                  <p className="text-sm text-gray-600">
                    Use the sidebar to paste your documentation text
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Supports any text format (markdown, plain text, etc.)
                  </p>
                </div>
              </div>
            </div>
          </div>
        )
      
      case 'curl':
        return (
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">cURL Command Generator</h2>
              <p className="text-gray-600 mb-6">
                Generate perfect, usable cURL commands for your API endpoints. Ask for specific endpoints or generate commands for all endpoints of a specific type.
              </p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Generate cURL Commands
                  </label>
                  <textarea
                    className="input-field min-h-[120px]"
                    placeholder="Examples:
• create curl for all POST endpoints in the doc
• generate curl for /file-upload endpoint
• create curl commands for file operations"
                  />
                  <button className="mt-3 btn-primary">
                    Generate cURL
                  </button>
                </div>
                
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <Zap className="h-5 w-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
                    <div className="text-sm text-blue-800">
                      <strong>Pro Tip:</strong> The AI will analyze your documentation and generate perfect, single-line cURL commands with proper headers, authentication, and JSON formatting.
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Example Requests</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <button 
                  onClick={() => setActiveTab('chat')}
                  className="text-left p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="font-medium text-gray-900">All POST Endpoints</div>
                  <div className="text-sm text-gray-600">Generate cURL for every POST API</div>
                </button>
                <button 
                  onClick={() => setActiveTab('chat')}
                  className="text-left p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="font-medium text-gray-900">Specific Endpoint</div>
                  <div className="text-sm text-gray-600">Generate cURL for a specific path</div>
                </button>
                <button 
                  onClick={() => setActiveTab('chat')}
                  className="text-left p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="font-medium text-gray-900">File Operations</div>
                  <div className="text-sm text-gray-600">Generate cURL for file-related APIs</div>
                </button>
                <button 
                  onClick={() => setActiveTab('chat')}
                  className="text-left p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="font-medium text-gray-900">Authentication</div>
                  <div className="text-sm text-gray-600">Generate cURL for auth endpoints</div>
                </button>
              </div>
            </div>
          </div>
        )
      
      default:
        return null
    }
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <div className="flex items-center">
                    <Icon className="h-4 w-4 mr-2" />
                    {tab.label}
                  </div>
                </button>
              )
            })}
          </nav>
        </div>
      </div>
      
      {/* Tab Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {renderTabContent()}
        </div>
      </div>
    </div>
  )
}

export default MainContent
