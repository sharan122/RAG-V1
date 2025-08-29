import { useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import MainContent from './components/MainContent'
import { RAGProvider } from './contexts/RAGContext'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <RAGProvider>
      <div className="min-h-screen bg-gray-50">
        <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        
        <div className="flex">
          <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <MainContent />
        </div>
      </div>
    </RAGProvider>
  )
}

export default App
