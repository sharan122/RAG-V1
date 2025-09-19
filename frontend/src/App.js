import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { SystemProvider, useSystem } from './contexts/SystemContext';
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
  Zap,
  Sun,
  Moon,
  Trash2,
  Download
} from 'lucide-react';

// Navigation Component
function Navigation() {
  const location = useLocation();
  const { theme, toggleTheme, isDark } = useTheme();
  const { systemStatus, showSettings, setShowSettings, chatMode, setChatMode } = useSystem();
  
  const clearChat = () => {
    // This will be handled by the ChatPage component
    window.dispatchEvent(new CustomEvent('clearChat'));
  };

  const downloadChat = () => {
    // This will be handled by the ChatPage component
    window.dispatchEvent(new CustomEvent('downloadChat'));
  };
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/upload', label: 'Upload', icon: Upload },
    { path: '/chat', label: 'Chat', icon: MessageSquare },
  ];

  return (
    <div className="bg-white dark:bg-gray-900 shadow-lg border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between">
          <div className="flex items-center mb-4 sm:mb-0">
            <div className="p-2 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl mr-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">RAG API Assistant</h1>
              <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">Intelligent Documentation Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
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
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 shadow-sm'
                        : 'text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5 mr-1 sm:mr-2" />
                    <span className="hidden sm:inline">{item.label}</span>
                    <span className="sm:hidden">{item.label.charAt(0)}</span>
                  </Link>
                );
              })}
            </nav>
            
            {/* System Status - Only show on chat page */}
            {location.pathname === '/chat' && (
              <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${systemStatus.is_ready ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {systemStatus.is_ready ? 'Ready' : 'Not Ready'}
                </span>
              </div>
            )}
            
            {/* Settings Button - Only show on chat page */}
            {location.pathname === '/chat' && (
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Settings"
              >
                <Settings className="w-5 h-5" />
              </button>
            )}
            
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-200 border border-gray-200 dark:border-gray-700"
              title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
            >
              {isDark ? (
                <Sun className="w-5 h-5 text-yellow-500" />
              ) : (
                <Moon className="w-5 h-5 text-gray-600" />
              )}
            </button>
          </div>
        </div>
        
        {/* Settings Panel - Only show on chat page */}
        {location.pathname === '/chat' && showSettings && (
          <div className="max-w-7xl mx-auto px-4 pb-4">
            <div className="bg-gray-50 dark:bg-gray-700 rounded-xl border border-gray-200 dark:border-gray-600 p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Chat Mode</label>
                  <select
                    value={chatMode}
                    onChange={(e) => setChatMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="normal">Normal</option>
                    <option value="streaming">Streaming</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">System Status</label>
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    <div>Documents: {systemStatus.documents_count}</div>
                    <div>Memory: {systemStatus.memory_count} messages</div>
                  </div>
                </div>
                <div className="flex items-end space-x-2">
                  <button
                    onClick={clearChat}
                    className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors flex items-center"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Clear Chat
                  </button>
                  <button
                    onClick={downloadChat}
                    className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <SystemProvider>
        <Router>
          <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-200">
            <Navigation />
            
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/chat" element={<ChatPage />} />
            </Routes>
          
          {/* Toast Notifications */}
          <Toaster
            position="top-right"
            reverseOrder={false}
            gutter={8}
            containerClassName=""
            containerStyle={{}}
            toastOptions={{
              // Default options
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              // Success toast
              success: {
                duration: 3000,
                style: {
                  background: '#10B981',
                  color: '#fff',
                },
                iconTheme: {
                  primary: '#fff',
                  secondary: '#10B981',
                },
              },
              // Error toast
              error: {
                duration: 5000,
                style: {
                  background: '#EF4444',
                  color: '#fff',
                },
                iconTheme: {
                  primary: '#fff',
                  secondary: '#EF4444',
                },
              },
              // Loading toast
              loading: {
                style: {
                  background: '#3B82F6',
                  color: '#fff',
                },
              },
            }}
          />
          </div>
        </Router>
      </SystemProvider>
    </ThemeProvider>
  );
}

export default App; 