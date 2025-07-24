import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './index.css';

// Components
import FileUpload from './components/FileUpload';
import ControlPanel from './components/ControlPanel';
import ProgressIndicator from './components/ProgressIndicator';
import ResultsTable from './components/ResultsTable';
import MakeLeaderboard from './components/MakeLeaderboard';
import SessionManager from './components/SessionManager';
import HistoryManager from './components/HistoryManager';

const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000';

function App() {
  const [uploadStatus, setUploadStatus] = useState({ uploaded: false, data: null, error: null });
  const [processingStatus, setProcessingStatus] = useState({
    isProcessing: false,
    sessionId: null,
    totalParts: 0,
    processedCount: 0,
    progressPercentage: 0,
    errorMessage: null,
    hasData: false
  });
  const [results, setResults] = useState([]);
  const [currentPart, setCurrentPart] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [viewingHistory, setViewingHistory] = useState(false);
  const [historicalData, setHistoricalData] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? `ws://${window.location.host}/ws`
        : 'ws://localhost:8000/ws';
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
        // Clear any reconnection timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
      
      wsRef.current.onmessage = (event) => {
        console.log('Raw WebSocket message received:', event.data);
        try {
          const message = JSON.parse(event.data);
          console.log('Parsed WebSocket message:', message);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          console.error('Raw data was:', event.data);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        
        // Attempt to reconnect after 3 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect WebSocket...');
            connectWebSocket();
          }, 3000);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsConnected(false);
      };
      
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      setWsConnected(false);
    }
  };

  const handleWebSocketMessage = (message) => {
    console.log('WebSocket message received:', message);
    console.log('Current viewingHistory state:', viewingHistory);
    console.log('Current processingStatus.isProcessing:', processingStatus.isProcessing);
    
    switch (message.type) {
      case 'progress':
        console.log('Processing progress message:', message);
        setProcessingStatus(prev => ({
          ...prev,
          processedCount: message.processed_count,
          progressPercentage: message.progress_percentage,
          successfulLookups: message.successful_lookups || 0,
          successRate: message.success_rate || 0
        }));
        setCurrentPart(message.current_part);
        if (message.leaderboard) {
          setLeaderboard(message.leaderboard);
        }
        break;
        
      case 'result':
        console.log('Processing result message:', message);
        const newResult = message.result;
        console.log('Adding result to table:', newResult);
        setResults(prev => {
          // Check if this result already exists (by index)
          const existingIndex = prev.findIndex(r => r.index === newResult.index);
          if (existingIndex >= 0) {
            // Update existing result
            const updated = [...prev];
            updated[existingIndex] = newResult;
            return updated;
          } else {
            // Add new result
            return [...prev, newResult];
          }
        });
        if (message.leaderboard) {
          setLeaderboard(message.leaderboard);
        }
        break;
        
      case 'completed':
        setProcessingStatus(prev => ({ ...prev, isProcessing: false }));
        setCurrentPart(null);
        addNotification('Processing completed successfully!', 'success');
        break;
        
      case 'stopped':
        setProcessingStatus(prev => ({ ...prev, isProcessing: false }));
        setCurrentPart(null);
        addNotification('Processing stopped by user', 'info');
        break;
        
      case 'error':
        setProcessingStatus(prev => ({ 
          ...prev, 
          isProcessing: false, 
          errorMessage: message.message 
        }));
        setCurrentPart(null);
        addNotification(`Error: ${message.message}`, 'error');
        break;
        
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const addNotification = (message, type = 'info') => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, message, type }]);
    
    // Auto-remove notification after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // Poll for status updates
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/status`);
        setProcessingStatus(response.data);
      } catch (error) {
        console.error('Error polling status:', error);
      }
    };

    const interval = setInterval(pollStatus, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (file) => {
    try {
      setUploadStatus({ uploaded: false, data: null, error: null });
      
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(`${API_BASE}/api/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setUploadStatus({ 
        uploaded: true, 
        data: response.data, 
        error: null 
      });
      
      addNotification('File uploaded successfully!', 'success');
      
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error.response?.data?.detail || 'Upload failed';
      setUploadStatus({ uploaded: false, data: null, error: errorMessage });
      addNotification(`Upload failed: ${errorMessage}`, 'error');
    }
  };

  const handleStartProcessing = async (startIndex, endIndex, isTest) => {
    try {
      const response = await axios.post(`${API_BASE}/api/start`, {
        start_index: startIndex,
        end_index: endIndex,
        is_test: isTest
      });
      
      setResults([]); // Clear previous results
      setCurrentPart(null);
      setLeaderboard([]); // Clear previous leaderboard
      setViewingHistory(false); // Exit historical viewing mode
      setHistoricalData(null); // Clear historical data
      addNotification('Processing started!', 'success');
      
    } catch (error) {
      console.error('Start processing error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to start processing';
      addNotification(`Failed to start: ${errorMessage}`, 'error');
    }
  };

  const handleStopProcessing = async () => {
    try {
      await axios.post(`${API_BASE}/api/stop`);
      addNotification('Stop request sent', 'info');
    } catch (error) {
      console.error('Stop processing error:', error);
      addNotification('Failed to stop processing', 'error');
    }
  };

  const handleExportResults = async () => {
    try {
      const response = await axios.post(`${API_BASE}/api/export`);
      addNotification(`Results exported to ${response.data.filename}`, 'success');
    } catch (error) {
      console.error('Export error:', error);
      const errorMessage = error.response?.data?.detail || 'Export failed';
      addNotification(`Export failed: ${errorMessage}`, 'error');
    }
  };

  const handleResumeSession = async (sessionId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/resume`, {
        session_id: sessionId
      });
      
      // Clear current state and update with resumed session
      setResults([]);
      setCurrentPart(null);
      setLeaderboard([]);
      setViewingHistory(false); // Exit historical viewing mode
      setHistoricalData(null); // Clear historical data
      
      addNotification(`Session resumed: ${response.data.already_processed} parts already processed`, 'success');
      
    } catch (error) {
      console.error('Resume session error:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to resume session';
      addNotification(`Resume failed: ${errorMessage}`, 'error');
    }
  };

  const handleViewHistory = (historyEntry) => {
    if (historyEntry === null) {
      // Back to current view
      setViewingHistory(false);
      setHistoricalData(null);
    } else {
      // View historical data
      setViewingHistory(true);
      setHistoricalData(historyEntry);
      
      // Update the UI with historical data
      setResults(historyEntry.results || []);
      
      // Convert leaderboard format if needed
      const leaderboardArray = historyEntry.leaderboard ? 
        Object.entries(historyEntry.leaderboard) : [];
      setLeaderboard(leaderboardArray);
      
      addNotification(`Viewing historical results: ${historyEntry.summary.total_processed} parts processed`, 'info');
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>Automotive Parts Scraper</h1>
        <p>Upload CSV files and automatically detect vehicle makes for automotive parts</p>
      </div>

      {/* Notifications */}
      {notifications.length > 0 && (
        <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 1000 }}>
          {notifications.map(notification => (
            <div
              key={notification.id}
              className={`alert alert-${notification.type}`}
              style={{ marginBottom: 10, cursor: 'pointer' }}
              onClick={() => removeNotification(notification.id)}
            >
              {notification.message}
            </div>
          ))}
        </div>
      )}

      <div className="main-content">
        <div className="left-panel">
          <FileUpload 
            onFileUpload={handleFileUpload}
            uploadStatus={uploadStatus}
          />
          
          <ControlPanel
            uploadStatus={uploadStatus}
            processingStatus={processingStatus}
            onStartProcessing={handleStartProcessing}
            onStopProcessing={handleStopProcessing}
            onExportResults={handleExportResults}
            resultsCount={results.length}
          />
          
          <ProgressIndicator
            processingStatus={processingStatus}
            currentPart={currentPart}
            wsConnected={wsConnected}
            resultsCount={results.length}
          />
          
          <SessionManager
            uploadStatus={uploadStatus}
            processingStatus={processingStatus}
            onResumeSession={handleResumeSession}
            API_BASE={API_BASE}
          />
          
          <HistoryManager
            API_BASE={API_BASE}
            onViewHistory={handleViewHistory}
          />
        </div>

        <div className="middle-panel">
          <MakeLeaderboard 
            leaderboard={leaderboard}
            isProcessing={processingStatus.isProcessing}
          />
        </div>

        <div className="right-panel">
          <div style={{ padding: '20px', borderBottom: '1px solid #e9ecef' }}>
            <h2 style={{ margin: '0 0 10px 0' }}>
              Results {viewingHistory && <span style={{ color: '#007bff', fontSize: '16px' }}>(Historical)</span>}
            </h2>
            <p style={{ margin: 0, color: '#666', fontSize: '14px' }}>
              {viewingHistory ? (
                historicalData ? 
                  `Historical results: ${results.length} processed parts (${historicalData.summary.success_rate.toFixed(1)}% success rate)` :
                  'Viewing historical data'
              ) : (
                results.length > 0 
                  ? `Showing ${results.length} results`
                  : 'No results yet. Upload a file and start processing to see results here.'
              )}
            </p>
          </div>
          <ResultsTable results={results} />
        </div>
      </div>
    </div>
  );
}

export default App;