import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import UploadPage from './components/UploadPage';
import ChatPage from './components/ChatPage';
import Dashboard from './components/Dashboard';
import { 
  Sparkles, 
  Upload, 
  MessageSquare, 
  BarChart3, 
  BookOpen,
  Settings,
  Zap
} from 'lucide-react';

// Navigation Component
function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/chat', label: 'Chat', icon: MessageSquare },
  ];

  return (
    <div className="bg-white shadow-lg border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between">
          <div className="flex items-center mb-4 sm:mb-0">
            <div className="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl mr-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">RAG API Assistant</h1>
              <p className="text-xs sm:text-sm text-gray-600">Intelligent Documentation Assistant</p>
            </div>
          </div>
          
          <nav className="flex flex-wrap gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-3 sm:px-4 py-2 rounded-lg font-medium transition-all duration-200 text-sm sm:text-base ${
                    isActive
                      ? 'bg-blue-100 text-blue-700 shadow-sm'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-4 h-4 sm:w-5 sm:h-5 mr-1 sm:mr-2" />
                  <span className="hidden sm:inline">{item.label}</span>
                  <span className="sm:hidden">{item.label.charAt(0)}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
        <Navigation />
        
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App; 