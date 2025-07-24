import React, { useState, useEffect } from 'react';
import axios from 'axios';

const HistoryManager = ({ 
  API_BASE,
  onViewHistory  // Callback to load historical results into main UI
}) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [viewingHistorical, setViewingHistorical] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/api/history`);
      setHistory(response.data);
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewEntry = async (entryId) => {
    try {
      const response = await axios.post(`${API_BASE}/api/history/${entryId}/view`);
      const entry = response.data;
      
      // Call parent callback to load the historical data into main UI
      onViewHistory(entry);
      setViewingHistorical(true);
      setSelectedEntry(entryId);
      
    } catch (error) {
      console.error('Error viewing history entry:', error);
    }
  };

  const handleDeleteEntry = async (entryId) => {
    if (!window.confirm('Are you sure you want to delete this history entry? This cannot be undone.')) {
      return;
    }
    
    try {
      await axios.delete(`${API_BASE}/api/history/${entryId}`);
      await loadHistory();
      
      // If we were viewing this entry, clear the view
      if (selectedEntry === entryId) {
        setViewingHistorical(false);
        setSelectedEntry(null);
      }
    } catch (error) {
      console.error('Error deleting history entry:', error);
    }
  };

  const handleBackToCurrent = () => {
    setViewingHistorical(false);
    setSelectedEntry(null);
    // Call parent to restore current results
    onViewHistory(null);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatTopMakes = (topMakes) => {
    if (!topMakes || topMakes.length === 0) return 'No makes found';
    return topMakes.map(([make, stats]) => `${make} (${stats.weighted_count})`).join(', ');
  };

  if (history.length === 0 && !loading) {
    return null; // Don't show component if no history
  }

  return (
    <div className="card">
      <div className="session-header">
        <h2>Processing History</h2>
        <div>
          {viewingHistorical && (
            <button
              className="btn btn-secondary"
              onClick={handleBackToCurrent}
              style={{ fontSize: '12px', padding: '4px 8px', marginRight: '5px' }}
            >
              Back to Current
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => setShowHistory(!showHistory)}
            style={{ fontSize: '12px', padding: '4px 8px' }}
          >
            {showHistory ? 'Hide' : `Show (${history.length})`}
          </button>
        </div>
      </div>

      {viewingHistorical && (
        <div className="alert alert-info" style={{ marginBottom: '15px' }}>
          <strong>Viewing Historical Results</strong> - Click "Back to Current" to return to your latest session
        </div>
      )}

      {showHistory && (
        <div className="history-list">
          {loading && (
            <div className="alert alert-info">Loading history...</div>
          )}
          
          {history.length === 0 ? (
            <div className="alert alert-info">No processing history found.</div>
          ) : (
            <div>
              <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
                Found {history.length} completed processing run{history.length !== 1 ? 's' : ''}
              </p>
              
              {history.map((entry) => (
                <div 
                  key={entry.id} 
                  className={`history-item ${selectedEntry === entry.id ? 'history-item-selected' : ''}`}
                >
                  <div className="history-info">
                    <div className="history-header">
                      <span className="history-id">
                        {entry.id.substring(0, 8)}...
                      </span>
                      <span className="history-timestamp">
                        {formatTimestamp(entry.timestamp)}
                      </span>
                    </div>
                    
                    <div className="history-stats">
                      <div className="history-stat">
                        <strong>{entry.summary.successful_lookups}/{entry.summary.total_processed}</strong> found
                        <span className="history-percentage"> 
                          ({entry.summary.success_rate.toFixed(1)}%)
                        </span>
                      </div>
                      <div className="history-range">
                        Range: {entry.summary.start_index}-{entry.summary.end_index} 
                        of {entry.summary.total_parts_in_file} total parts
                      </div>
                    </div>
                    
                    {entry.summary.top_makes && entry.summary.top_makes.length > 0 && (
                      <div className="history-top-makes">
                        <strong>Top makes:</strong> {formatTopMakes(entry.summary.top_makes)}
                      </div>
                    )}
                    
                    <div className="history-progress-bar">
                      <div 
                        className="history-progress-fill"
                        style={{ 
                          width: `${entry.summary.success_rate}%`,
                          backgroundColor: entry.summary.success_rate >= 50 ? '#28a745' : '#ffc107'
                        }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="history-actions">
                    <button
                      className="btn btn-primary"
                      onClick={() => handleViewEntry(entry.id)}
                      style={{ fontSize: '12px', padding: '4px 8px', marginRight: '5px' }}
                    >
                      {selectedEntry === entry.id ? 'Viewing' : 'View'}
                    </button>
                    
                    <button
                      className="btn btn-danger"
                      onClick={() => handleDeleteEntry(entry.id)}
                      style={{ fontSize: '12px', padding: '4px 8px' }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          <button
            className="btn btn-secondary"
            onClick={loadHistory}
            disabled={loading}
            style={{ width: '100%', marginTop: '10px' }}
          >
            Refresh History
          </button>
        </div>
      )}
    </div>
  );
};

export default HistoryManager;