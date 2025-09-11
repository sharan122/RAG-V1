import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
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
  Moon
} from 'lucide-react';

// Navigation Component
function Navigation() {
  const location = useLocation();
  const { theme, toggleTheme, isDark } = useTheme();
  
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
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
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
    </ThemeProvider>
  );
}

export default App; 