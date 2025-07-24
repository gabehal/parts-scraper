import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SessionManager = ({ 
  uploadStatus, 
  processingStatus, 
  onResumeSession,
  API_BASE 
}) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSessions, setShowSessions] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/api/sessions`);
      setSessions(response.data);
      
      // Auto-show sessions if there are any incomplete ones
      const incompleteSessions = response.data.filter(s => s.progress_percentage < 100);
      if (incompleteSessions.length > 0 && !uploadStatus.uploaded && !processingStatus.isProcessing) {
        setShowSessions(true);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleResumeSession = async (sessionId) => {
    try {
      await onResumeSession(sessionId);
      setShowSessions(false);
    } catch (error) {
      console.error('Error resuming session:', error);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this session? This cannot be undone.')) {
      return;
    }
    
    try {
      await axios.delete(`${API_BASE}/api/sessions/${sessionId}`);
      await loadSessions();
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getStatusColor = (percentage) => {
    if (percentage >= 100) return '#28a745';
    if (percentage >= 50) return '#ffc107';
    return '#007bff';
  };

  if (sessions.length === 0) {
    return null;
  }

  return (
    <div className="card">
      <div className="session-header">
        <h2>Session Management</h2>
        <button
          className="btn btn-secondary"
          onClick={() => setShowSessions(!showSessions)}
          style={{ fontSize: '12px', padding: '4px 8px' }}
        >
          {showSessions ? 'Hide' : `Show (${sessions.length})`}
        </button>
      </div>

      {showSessions && (
        <div className="session-list">
          {loading && (
            <div className="alert alert-info">Loading sessions...</div>
          )}
          
          {sessions.length === 0 ? (
            <div className="alert alert-info">No saved sessions found.</div>
          ) : (
            <div>
              <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
                Found {sessions.length} saved session{sessions.length !== 1 ? 's' : ''}
              </p>
              
              {sessions.map((session) => (
                <div key={session.session_id} className="session-item">
                  <div className="session-info">
                    <div className="session-id">
                      Session: {session.session_id.substring(0, 8)}...
                    </div>
                    <div className="session-details">
                      <span className="session-progress">
                        {session.processed_count}/{session.total_parts} parts 
                        ({session.progress_percentage.toFixed(1)}%)
                      </span>
                      <span className="session-timestamp">
                        {formatTimestamp(session.timestamp)}
                      </span>
                    </div>
                    <div className="session-progress-bar">
                      <div 
                        className="session-progress-fill"
                        style={{ 
                          width: `${session.progress_percentage}%`,
                          backgroundColor: getStatusColor(session.progress_percentage)
                        }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="session-actions">
                    {session.progress_percentage < 100 ? (
                      <button
                        className="btn btn-primary"
                        onClick={() => handleResumeSession(session.session_id)}
                        disabled={processingStatus.isProcessing}
                        style={{ fontSize: '12px', padding: '4px 8px', marginRight: '5px' }}
                      >
                        Resume
                      </button>
                    ) : (
                      <span className="session-completed">✅ Completed</span>
                    )}
                    
                    <button
                      className="btn btn-danger"
                      onClick={() => handleDeleteSession(session.session_id)}
                      disabled={processingStatus.isProcessing}
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
            onClick={loadSessions}
            disabled={loading}
            style={{ width: '100%', marginTop: '10px' }}
          >
            Refresh Sessions
          </button>
        </div>
      )}
    </div>
  );
};

export default SessionManager;