import React from 'react';

const ProgressIndicator = ({ 
  processingStatus, 
  currentPart, 
  wsConnected, 
  resultsCount 
}) => {
  const getStatusDisplay = () => {
    if (processingStatus.isProcessing) {
      return {
        text: 'Processing...',
        className: 'status-processing'
      };
    } else if (processingStatus.errorMessage) {
      return {
        text: 'Error',
        className: 'status-error'
      };
    } else if (resultsCount > 0) {
      return {
        text: 'Completed',
        className: 'status-completed'
      };
    } else {
      return {
        text: 'Ready',
        className: 'status-idle'
      };
    }
  };

  const status = getStatusDisplay();
  
  // Use real-time success statistics from backend
  const successfulLookups = processingStatus.successfulLookups || 0;
  const processedCount = processingStatus.processedCount || 0;
  const successRate = processingStatus.successRate || 0;

  const getConnectionStatus = () => {
    return wsConnected ? 'Connected' : 'Disconnected';
  };

  return (
    <div className="card">
      <h2>Progress & Status</h2>
      
      {/* Status Indicator */}
      <div className="form-group">
        <div className={`status-indicator ${status.className}`}>
          <div className="status-dot" style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: processingStatus.isProcessing ? '#007bff' : 
                            processingStatus.errorMessage ? '#dc3545' :
                            resultsCount > 0 ? '#28a745' : '#6c757d'
          }}></div>
          {status.text}
        </div>
      </div>

      {/* Progress Bar */}
      {processingStatus.isProcessing && (
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${processingStatus.progressPercentage || 0}%` }}
            ></div>
          </div>
          <div className="progress-text">
            {processedCount} processed 
            ({(processingStatus.progressPercentage || 0).toFixed(1)}%)
            {processedCount > 0 && (
              <span> • {successfulLookups}/{processedCount} found ({successRate.toFixed(1)}%)</span>
            )}
          </div>
        </div>
      )}

      {/* Current Part Being Processed */}
      {currentPart && (
        <div className="current-part">
          <strong>Currently processing:</strong>
          <br />
          {currentPart.part_number}
          <br />
          <small>{currentPart.description}</small>
        </div>
      )}

      {/* Statistics */}
      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-value">{processingStatus.totalParts || 0}</div>
          <div className="stat-label">Total Parts</div>
        </div>
        
        <div className="stat-item">
          <div className="stat-value">{processedCount}</div>
          <div className="stat-label">Processed</div>
        </div>
        
        <div className="stat-item">
          <div className="stat-value">{successfulLookups}/{processedCount}</div>
          <div className="stat-label">Found Makes</div>
        </div>
        
        {processedCount > 0 && (
          <div className="stat-item">
            <div className="stat-value">{successRate.toFixed(1)}%</div>
            <div className="stat-label">Success Rate</div>
          </div>
        )}
      </div>

      {/* Session Information */}
      {processingStatus.sessionId && (
        <div style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
          <div>Session: {processingStatus.sessionId.substring(0, 8)}...</div>
          <div>WebSocket: {getConnectionStatus()}</div>
        </div>
      )}

      {/* Connection Status */}
      <div style={{ 
        fontSize: '12px', 
        color: wsConnected ? '#28a745' : '#dc3545',
        marginTop: '10px'
      }}>
        ● {wsConnected ? 'Real-time updates active' : 'Real-time updates unavailable'}
      </div>
    </div>
  );
};

export default ProgressIndicator;