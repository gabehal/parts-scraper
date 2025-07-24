import React, { useState, useRef } from 'react';

const FileUpload = ({ onFileUpload, uploadStatus }) => {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const csvFile = files.find(file => file.name.toLowerCase().endsWith('.csv'));
    
    if (csvFile) {
      handleFileUpload(csvFile);
    } else {
      alert('Please upload a CSV file');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleFileUpload = async (file) => {
    setUploading(true);
    try {
      await onFileUpload(file);
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="card">
      <h2>Upload CSV File</h2>
      
      <div 
        className={`file-upload ${dragOver ? 'dragover' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          disabled={uploading}
        />
        
        {uploading ? (
          <div>
            <div className="spinner" style={{ margin: '0 auto 10px' }}></div>
            <p className="upload-text">Uploading and processing file...</p>
          </div>
        ) : (
          <div>
            <p className="upload-text">
              Drag and drop a CSV file here, or click to browse
            </p>
            <button 
              className="btn btn-primary"
              onClick={handleBrowseClick}
              disabled={uploading}
            >
              Browse Files
            </button>
          </div>
        )}
      </div>

      {uploadStatus.error && (
        <div className="alert alert-error">
          {uploadStatus.error}
        </div>
      )}

      {uploadStatus.uploaded && uploadStatus.data && (
        <div className="alert alert-success">
          <strong>File uploaded successfully!</strong>
          <br />
          Automotive parts: {uploadStatus.data.total_automotive_parts}
          <br />
          Tool parts: {uploadStatus.data.total_tool_parts}
          <br />
          Unknown parts: {uploadStatus.data.total_unknown_parts}
        </div>
      )}
    </div>
  );
};

export default FileUpload;