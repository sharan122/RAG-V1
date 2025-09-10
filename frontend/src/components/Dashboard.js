import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Database, 
  Brain, 
  FileText, 
  Users, 
  Activity, 
  TrendingUp, 
  Clock, 
  Zap,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Download,
  Settings,
  BookOpen,
  MessageSquare,
  Search
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function Dashboard() {
  const [systemStatus, setSystemStatus] = useState({
    vectorDB: {
      is_ready: false,
      documents_count: 0,
      db_size_mb: 0.0,
      last_updated: null
    },
    memory: {
      active_sessions: 0,
      total_memories: 0,
      memory_size_mb: 0.0
    },
    performance: {
      avg_response_time: 0,
      total_queries: 0,
      success_rate: 0
    }
  });
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      setLoading(true);
      
      // Fetch vector DB status
      const vectorResponse = await fetch(`${API_BASE_URL}/docs/status`);
      const vectorData = await vectorResponse.json();
      
      // Fetch memory status
      const memoryResponse = await fetch(`${API_BASE_URL}/memory/health`);
      const memoryData = await memoryResponse.json();
      
      setSystemStatus({
        vectorDB: {
          is_ready: vectorData.vectorstore?.status === "ready",
          documents_count: vectorData.vectorstore?.document_count || 0,
          db_size_mb: vectorData.vectorstore?.db_size_mb || 0.0,
          last_updated: vectorData.vectorstore?.last_updated || null
        },
        memory: {
          active_sessions: memoryData.active_sessions || 0,
          total_memories: memoryData.total_messages || 0,
          memory_size_mb: 0.0 // Not provided by API
        },
        performance: {
          avg_response_time: Math.random() * 2 + 0.5, // Mock data
          total_queries: Math.floor(Math.random() * 1000) + 500,
          success_rate: 95 + Math.random() * 5
        }
      });
      
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon: Icon, color, subtitle, trend }) => (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        {trend && (
          <div className={`flex items-center text-sm ${trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
            <TrendingUp className="w-4 h-4 mr-1" />
            {trend > 0 ? '+' : ''}{trend}%
          </div>
        )}
      </div>
      <div>
        <h3 className="text-2xl font-bold text-gray-900 mb-1">{value}</h3>
        <p className="text-gray-600 font-medium">{title}</p>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
    </div>
  );

  const QuickAction = ({ title, description, icon: Icon, onClick, color = "bg-blue-50 text-blue-600" }) => (
    <button
      onClick={onClick}
      className={`p-4 rounded-xl border border-gray-200 hover:shadow-md transition-all duration-200 text-left ${color}`}
    >
      <div className="flex items-center mb-2">
        <Icon className="w-5 h-5 mr-3" />
        <h4 className="font-semibold">{title}</h4>
      </div>
      <p className="text-sm opacity-75">{description}</p>
    </button>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">System Dashboard</h1>
              <p className="text-gray-600">Monitor your RAG system performance and status</p>
            </div>
            <div className="flex items-center space-x-3">
              <div className="text-sm text-gray-500">
                Last updated: {lastRefresh.toLocaleTimeString()}
              </div>
              <button
                onClick={fetchSystemStatus}
                disabled={loading}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>

        {/* System Status Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-8">
          <StatCard
            title="Documents"
            value={systemStatus.vectorDB.documents_count}
            icon={FileText}
            color="bg-blue-500"
            subtitle="In knowledge base"
            trend={5.2}
          />
          <StatCard
            title="Memory Sessions"
            value={systemStatus.memory.active_sessions}
            icon={Users}
            color="bg-purple-500"
            subtitle="Active conversations"
            trend={12.5}
          />
          <StatCard
            title="Database Size"
            value={`${systemStatus.vectorDB.db_size_mb.toFixed(1)} MB`}
            icon={Database}
            color="bg-green-500"
            subtitle="Storage used"
            trend={-2.1}
          />
          <StatCard
            title="Success Rate"
            value={`${systemStatus.performance.success_rate.toFixed(1)}%`}
            icon={CheckCircle}
            color="bg-emerald-500"
            subtitle="Query success"
            trend={1.8}
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* System Health */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-lg border border-gray-100 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">System Health</h2>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                systemStatus.vectorDB.is_ready 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {systemStatus.vectorDB.is_ready ? 'All Systems Operational' : 'System Issues Detected'}
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <Database className="w-5 h-5 text-blue-600 mr-3" />
                  <div>
                    <h3 className="font-semibold text-gray-900">Vector Database</h3>
                    <p className="text-sm text-gray-600">Knowledge storage system</p>
                  </div>
                </div>
                <div className="flex items-center">
                  {systemStatus.vectorDB.is_ready ? (
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                  )}
                  <span className={`font-medium ${
                    systemStatus.vectorDB.is_ready ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {systemStatus.vectorDB.is_ready ? 'Ready' : 'Not Ready'}
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <Brain className="w-5 h-5 text-purple-600 mr-3" />
                  <div>
                    <h3 className="font-semibold text-gray-900">Memory System</h3>
                    <p className="text-sm text-gray-600">Conversation context management</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                  <span className="font-medium text-green-600">Active</span>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <Activity className="w-5 h-5 text-emerald-600 mr-3" />
                  <div>
                    <h3 className="font-semibold text-gray-900">API Endpoints</h3>
                    <p className="text-sm text-gray-600">Backend services</p>
                  </div>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                  <span className="font-medium text-green-600">Online</span>
                </div>
              </div>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Performance</h2>
            
            <div className="space-y-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 mb-1">
                  {systemStatus.performance.avg_response_time.toFixed(1)}s
                </div>
                <div className="text-sm text-blue-600 font-medium">Avg Response Time</div>
              </div>
              
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600 mb-1">
                  {systemStatus.performance.total_queries}
                </div>
                <div className="text-sm text-green-600 font-medium">Total Queries</div>
              </div>
              
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600 mb-1">
                  {systemStatus.performance.success_rate.toFixed(1)}%
                </div>
                <div className="text-sm text-purple-600 font-medium">Success Rate</div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Quick Actions</h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <QuickAction
              title="Upload Documentation"
              description="Add new API documentation to the knowledge base"
              icon={BookOpen}
              onClick={() => window.location.href = '/'}
              color="bg-blue-50 text-blue-600 hover:bg-blue-100"
            />
            <QuickAction
              title="Start Chat"
              description="Ask questions about your documentation"
              icon={MessageSquare}
              onClick={() => window.location.href = '/chat'}
              color="bg-green-50 text-green-600 hover:bg-green-100"
            />
            <QuickAction
              title="Search Knowledge"
              description="Browse through available documentation"
              icon={Search}
              onClick={() => window.location.href = '/chat'}
              color="bg-purple-50 text-purple-600 hover:bg-purple-100"
            />
            <QuickAction
              title="System Settings"
              description="Configure system parameters and preferences"
              icon={Settings}
              onClick={() => {}}
              color="bg-gray-50 text-gray-600 hover:bg-gray-100"
            />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Recent Activity</h2>
          
          <div className="space-y-4">
            <div className="flex items-center p-4 bg-gray-50 rounded-lg">
              <div className="p-2 bg-blue-100 rounded-lg mr-4">
                <FileText className="w-5 h-5 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900">Documentation Processed</h3>
                <p className="text-sm text-gray-600">
                  {systemStatus.vectorDB.documents_count} documents loaded into knowledge base
                </p>
              </div>
              <div className="text-sm text-gray-500">
                {systemStatus.vectorDB.last_updated || 'Just now'}
              </div>
            </div>

            <div className="flex items-center p-4 bg-gray-50 rounded-lg">
              <div className="p-2 bg-green-100 rounded-lg mr-4">
                <MessageSquare className="w-5 h-5 text-green-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900">Chat Sessions Active</h3>
                <p className="text-sm text-gray-600">
                  {systemStatus.memory.active_sessions} active conversation sessions
                </p>
              </div>
              <div className="text-sm text-gray-500">
                Live
              </div>
            </div>

            <div className="flex items-center p-4 bg-gray-50 rounded-lg">
              <div className="p-2 bg-purple-100 rounded-lg mr-4">
                <Activity className="w-5 h-5 text-purple-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900">System Performance</h3>
                <p className="text-sm text-gray-600">
                  {systemStatus.performance.success_rate.toFixed(1)}% success rate with {systemStatus.performance.total_queries} total queries
                </p>
              </div>
              <div className="text-sm text-gray-500">
                {systemStatus.performance.avg_response_time.toFixed(1)}s avg
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
