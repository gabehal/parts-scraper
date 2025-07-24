import React, { useEffect, useRef } from 'react';

const ResultsTable = ({ results }) => {
  const tableContainerRef = useRef(null);
  const shouldAutoScroll = useRef(true);

  // Auto-scroll to bottom when new results are added
  useEffect(() => {
    if (shouldAutoScroll.current && tableContainerRef.current) {
      const container = tableContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [results]);

  // Handle manual scrolling - disable auto-scroll if user scrolls up
  const handleScroll = () => {
    if (tableContainerRef.current) {
      const container = tableContainerRef.current;
      const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10;
      shouldAutoScroll.current = isAtBottom;
    }
  };

  const getStatusBadge = (makes, source) => {
    if (makes === 'NOT_FOUND' || !makes) {
      return <span className="status-badge status-not-found">Not Found</span>;
    } else {
      return <span className="status-badge status-found">Found</span>;
    }
  };

  const formatMakes = (makes) => {
    if (!makes || makes === 'NOT_FOUND') {
      return '-';
    }
    return makes;
  };

  const formatCurrency = (value) => {
    if (typeof value === 'number') {
      return `$${value.toFixed(2)}`;
    }
    return value;
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  if (results.length === 0) {
    return (
      <div className="results-table-container">
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          color: '#666',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>📋</div>
          <h3 style={{ margin: '0 0 10px 0', color: '#333' }}>No Results Yet</h3>
          <p style={{ margin: 0 }}>
            Upload a CSV file and start processing to see results here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={tableContainerRef}
      className="results-table-container"
      onScroll={handleScroll}
    >
      <table className="results-table">
        <thead>
          <tr>
            <th style={{ width: '50px' }}>#</th>
            <th style={{ width: '120px' }}>Item #</th>
            <th style={{ width: '100px' }}>Part Number</th>
            <th style={{ minWidth: '200px' }}>Description</th>
            <th style={{ width: '60px' }}>Qty</th>
            <th style={{ width: '80px' }}>Unit Price</th>
            <th style={{ width: '80px' }}>Ext. Price</th>
            <th style={{ width: '80px' }}>Category</th>
            <th style={{ width: '100px' }}>Status</th>
            <th style={{ minWidth: '150px' }}>Makes</th>
            <th style={{ width: '80px' }}>Source</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result) => (
            <tr key={result.index || result.item_num}>
              <td>{result.index + 1}</td>
              <td title={result.item_num}>
                {truncateText(result.item_num, 15)}
              </td>
              <td title={result.part_number}>
                {truncateText(result.part_number, 12)}
              </td>
              <td title={result.description}>
                {truncateText(result.description, 40)}
              </td>
              <td>{result.qty}</td>
              <td>{formatCurrency(result.unit_retail)}</td>
              <td>{formatCurrency(result.ext_retail)}</td>
              <td>
                <span style={{
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontSize: '11px',
                  fontWeight: '500',
                  backgroundColor: result.category === 'Automotive' ? '#e7f3ff' : '#f0f0f0',
                  color: result.category === 'Automotive' ? '#0066cc' : '#666'
                }}>
                  {result.category}
                </span>
              </td>
              <td className="status-cell">
                {getStatusBadge(result.makes, result.source)}
              </td>
              <td title={result.makes}>
                {formatMakes(result.makes)}
              </td>
              <td>
                <span style={{
                  fontSize: '11px',
                  color: '#666',
                  fontWeight: '500'
                }}>
                  {result.source || '-'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Scroll to bottom button */}
      {!shouldAutoScroll.current && (
        <div style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          zIndex: 10
        }}>
          <button
            className="btn btn-primary"
            onClick={() => {
              shouldAutoScroll.current = true;
              if (tableContainerRef.current) {
                tableContainerRef.current.scrollTop = tableContainerRef.current.scrollHeight;
              }
            }}
            style={{
              borderRadius: '20px',
              fontSize: '12px',
              padding: '6px 12px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}
          >
            ↓ Scroll to Latest
          </button>
        </div>
      )}
    </div>
  );
};

export default ResultsTable;