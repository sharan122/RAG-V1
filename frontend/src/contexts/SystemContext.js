import React, { createContext, useContext, useState, useEffect } from 'react';

const SystemContext = createContext();

export const useSystem = () => {
  const context = useContext(SystemContext);
  if (!context) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
};

export const SystemProvider = ({ children }) => {
  const [systemStatus, setSystemStatus] = useState({
    is_ready: false,
    documents_count: 0,
    memory_count: 0
  });
  const [showSettings, setShowSettings] = useState(false);
  const [chatMode, setChatMode] = useState('normal');

  // Fetch system status
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/docs/status');
        if (response.ok) {
          const data = await response.json();
          setSystemStatus({
            is_ready: data.vectorstore?.status === "ready",
            documents_count: data.vectorstore?.document_count || 0,
            memory_count: data.memory_count || 0
          });
        }
      } catch (error) {
        console.error('Failed to fetch system status:', error);
        setSystemStatus({
          is_ready: false,
          documents_count: 0,
          memory_count: 0
        });
      }
    };

    fetchSystemStatus();
    // Poll every 30 seconds
    const interval = setInterval(fetchSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const value = {
    systemStatus,
    setSystemStatus,
    showSettings,
    setShowSettings,
    chatMode,
    setChatMode
  };

  return <SystemContext.Provider value={value}>{children}</SystemContext.Provider>;
};
