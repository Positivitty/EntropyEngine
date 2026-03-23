import { useState, useRef } from 'react';
import ScrambleText from './ScrambleText';

export default function UploadPanel({ fileInfo, onUpload, onRunPipeline, onReset, isProcessing, isComplete, analysisComplete, onAnalyze }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) await handleFile(file);
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) await handleFile(file);
  };

  const handleFile = async (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['json', 'csv'].includes(ext)) {
      return;
    }
    setUploading(true);
    try {
      await onUpload(file);
    } catch {
      // Error handled in hook
    }
    setUploading(false);
  };

  const canRun = fileInfo && !isProcessing && !isComplete;
  const canAnalyze = fileInfo && !isProcessing && !analysisComplete;

  return (
    <div className="panel panel-left">
      <div className="panel-header">
        <span className="header-bar"></span>
        <ScrambleText text="FILE INPUT" />
      </div>

      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".json,.csv"
          onChange={handleFileSelect}
        />
        {uploading ? (
          <>
            <div className="upload-icon">...</div>
            <div className="upload-text active">UPLOADING</div>
          </>
        ) : fileInfo ? (
          <div className="file-info">
            <div className="file-name">{fileInfo.name}</div>
            <div className="file-size">{fileInfo.sizeFormatted}</div>
          </div>
        ) : (
          <>
            <div className="upload-icon">&darr;</div>
            <div className="upload-text">DROP FILE</div>
            <div className="upload-text" style={{ fontSize: '9px', marginTop: '4px', color: '#333' }}>
              .json / .csv
            </div>
          </>
        )}
      </div>

      <button
        className="btn btn-analyze"
        disabled={!canAnalyze}
        onClick={onAnalyze}
      >
        Analyze Issues
      </button>

      <button
        className="btn btn-primary"
        disabled={!canRun}
        onClick={() => onRunPipeline(fileInfo.fileId)}
      >
        Initialize Pipeline
      </button>

      <button
        className="btn btn-danger"
        disabled={isProcessing}
        onClick={onReset}
      >
        Reset
      </button>
    </div>
  );
}
