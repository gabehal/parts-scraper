import React, { useState } from 'react';

const ControlPanel = ({
  uploadStatus,
  processingStatus,
  onStartProcessing,
  onStopProcessing,
  onExportResults,
  resultsCount
}) => {
  const [startIndex, setStartIndex] = useState(0);
  const [endIndex, setEndIndex] = useState('');
  const [rangeError, setRangeError] = useState('');

  const validateRange = (start, end) => {
    const startNum = parseInt(start);
    const endNum = end === '' ? null : parseInt(end);
    
    if (isNaN(startNum) || startNum < 0) {
      return 'Start index must be a valid number >= 0';
    }
    
    if (endNum !== null && (isNaN(endNum) || endNum <= startNum)) {
      return 'End index must be greater than start index';
    }
    
    if (uploadStatus.data && endNum !== null && endNum > uploadStatus.data.total_automotive_parts) {
      return `End index cannot exceed ${uploadStatus.data.total_automotive_parts}`;
    }
    
    return '';
  };

  const handleStartProcessing = () => {
    const error = validateRange(startIndex, endIndex);
    if (error) {
      setRangeError(error);
      return;
    }
    
    setRangeError('');
    const endNum = endIndex === '' ? null : parseInt(endIndex);
    onStartProcessing(parseInt(startIndex), endNum, false);
  };

  const handleTestRun = () => {
    setRangeError('');
    onStartProcessing(0, null, true);
  };

  const handleRangePreset = (preset) => {
    if (!uploadStatus.data) return;
    
    const total = uploadStatus.data.total_automotive_parts;
    
    switch (preset) {
      case 'first100':
        setStartIndex(0);
        setEndIndex(Math.min(100, total).toString());
        break;
      case 'all':
        setStartIndex(0);
        setEndIndex('');
        break;
      default:
        break;
    }
    setRangeError('');
  };

  const canStartProcessing = uploadStatus.uploaded && !processingStatus.isProcessing;
  const canStopProcessing = processingStatus.isProcessing;
  const canExport = resultsCount > 0 && !processingStatus.isProcessing;

  return (
    <div className="card">
      <h2>Processing Controls</h2>
      
      {/* Quick Actions */}
      <div className="form-group">
        <label>Quick Actions</label>
        <div className="button-group">
          <button
            className="btn btn-success"
            onClick={handleTestRun}
            disabled={!canStartProcessing}
          >
            {processingStatus.isProcessing ? (
              <>
                <div className="spinner"></div>
                Processing...
              </>
            ) : (
              'Test Run (50 parts)'
            )}
          </button>
          
          <button
            className="btn btn-danger"
            onClick={onStopProcessing}
            disabled={!canStopProcessing}
          >
            Stop
          </button>
        </div>
      </div>

      {/* Range Selection */}
      <div className="form-group">
        <label>Custom Range</label>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="number"
            className="form-control"
            placeholder="Start (0)"
            value={startIndex}
            onChange={(e) => setStartIndex(e.target.value)}
            disabled={processingStatus.isProcessing}
            style={{ flex: 1 }}
          />
          <span>to</span>
          <input
            type="number"
            className="form-control"
            placeholder="End (all)"
            value={endIndex}
            onChange={(e) => setEndIndex(e.target.value)}
            disabled={processingStatus.isProcessing}
            style={{ flex: 1 }}
          />
        </div>
        
        {uploadStatus.data && (
          <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
            Total automotive parts: {uploadStatus.data.total_automotive_parts}
          </div>
        )}
      </div>

      {rangeError && (
        <div className="alert alert-error">
          {rangeError}
        </div>
      )}

      {/* Range Presets */}
      {uploadStatus.data && (
        <div className="form-group">
          <label>Quick Ranges</label>
          <div className="button-group">
            <button
              className="btn btn-secondary"
              onClick={() => handleRangePreset('first100')}
              disabled={processingStatus.isProcessing}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              First 100
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleRangePreset('all')}
              disabled={processingStatus.isProcessing}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              All Parts
            </button>
          </div>
        </div>
      )}

      {/* Start Processing Button */}
      <div className="form-group">
        <button
          className="btn btn-primary"
          onClick={handleStartProcessing}
          disabled={!canStartProcessing}
          style={{ width: '100%' }}
        >
          Start Processing Range
        </button>
      </div>

      {/* Export Results */}
      <div className="form-group">
        <button
          className="btn btn-success"
          onClick={onExportResults}
          disabled={!canExport}
          style={{ width: '100%' }}
        >
          Export Results ({resultsCount} items)
        </button>
      </div>

      {/* Status Information */}
      {!uploadStatus.uploaded && (
        <div className="alert alert-info">
          Please upload a CSV file first to enable processing.
        </div>
      )}
      
      {processingStatus.errorMessage && (
        <div className="alert alert-error">
          <strong>Error:</strong> {processingStatus.errorMessage}
        </div>
      )}
    </div>
  );
};

export default ControlPanel;