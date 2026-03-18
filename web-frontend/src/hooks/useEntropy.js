import { useState, useCallback, useRef } from 'react';

const API_BASE = 'http://localhost:8000';

const STAGES = ['INPUT', 'DEDUP', 'ENCODE', 'TRIM', 'COMPRESS'];

const initialStages = STAGES.map((name) => ({
  name,
  status: 'idle', // idle | pending | active | complete
  inputSize: null,
  outputSize: null,
  reduction: null,
}));

export function useEntropy() {
  const [fileInfo, setFileInfo] = useState(null);
  const [stages, setStages] = useState(initialStages);
  const [activeStage, setActiveStage] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [currentSize, setCurrentSize] = useState(null);
  const [originalSize, setOriginalSize] = useState(null);
  const abortRef = useRef(null);

  const addLog = useCallback((message) => {
    setLogs((prev) => [
      ...prev,
      { message, timestamp: new Date() },
    ]);
  }, []);

  const uploadFile = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    addLog(`UPLOADING: ${file.name} (${formatBytes(file.size)})`);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const data = await response.json();
      const info = {
        fileId: data.file_id,
        name: file.name,
        size: file.size,
        sizeFormatted: formatBytes(file.size),
      };

      setFileInfo(info);
      setOriginalSize(file.size);
      setCurrentSize(file.size);
      addLog(`FILE LOADED: ${file.name} (${formatBytes(file.size)})`);

      return info;
    } catch (err) {
      addLog(`ERROR: ${err.message}`);
      throw err;
    }
  }, [addLog]);

  const runPipeline = useCallback(async (fileId) => {
    setIsProcessing(true);
    setIsComplete(false);
    setMetrics([]);
    setStages(initialStages.map((s) => ({ ...s, status: 'pending' })));

    addLog('INITIALIZING ENTROPY ENGINE...');
    addLog(`PROCESSING FILE ID: ${fileId}`);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${API_BASE}/process/${fileId}`, {
        method: 'POST',
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Process failed: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          let eventName = 'message';
          let eventData = '';

          for (const line of eventBlock.split('\n')) {
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              eventData = line.slice(5).trim();
            }
          }

          if (!eventData) continue;

          try {
            const parsed = JSON.parse(eventData);
            handleSSEEvent(eventName, parsed);
          } catch {
            // Non-JSON data, skip
          }
        }
      }

      setIsProcessing(false);
      setIsComplete(true);
      addLog('PIPELINE COMPLETE. ALL STAGES FINISHED.');
    } catch (err) {
      if (err.name === 'AbortError') {
        addLog('PIPELINE ABORTED.');
      } else {
        addLog(`ERROR: ${err.message}`);
      }
      setIsProcessing(false);
    }
  }, [addLog]);

  const handleSSEEvent = useCallback((eventName, data) => {
    switch (eventName) {
      case 'stage_start': {
        const stageName = data.stage?.toUpperCase();
        addLog(`STAGE: ${stageName}...`);
        setActiveStage(stageName);
        setStages((prev) =>
          prev.map((s) =>
            s.name === stageName ? { ...s, status: 'active' } : s
          )
        );
        break;
      }

      case 'stage_complete': {
        const stageName = data.stage?.toUpperCase();
        const inputSize = data.input_size;
        const outputSize = data.output_size;
        const reduction = inputSize > 0
          ? ((1 - outputSize / inputSize) * 100).toFixed(1)
          : '0.0';

        addLog(
          `${stageName} COMPLETE: ${formatBytes(inputSize)} -> ${formatBytes(outputSize)} [-${reduction}%]`
        );

        setActiveStage(null);
        setCurrentSize(outputSize);

        setStages((prev) =>
          prev.map((s) =>
            s.name === stageName
              ? { ...s, status: 'complete', inputSize, outputSize, reduction: parseFloat(reduction) }
              : s
          )
        );

        setMetrics((prev) => [
          ...prev,
          {
            stage: stageName,
            inputSize,
            outputSize,
            reduction: parseFloat(reduction),
          },
        ]);
        break;
      }

      case 'pipeline_complete': {
        const origSize = data.original_size;
        const finalSize = data.final_size;
        const totalReduction = origSize > 0
          ? ((1 - finalSize / origSize) * 100).toFixed(1)
          : '0.0';

        addLog(`TOTAL REDUCTION: ${formatBytes(origSize)} -> ${formatBytes(finalSize)} [-${totalReduction}%]`);
        setOriginalSize(origSize);
        setCurrentSize(finalSize);
        setIsComplete(true);
        setIsProcessing(false);
        break;
      }

      case 'error': {
        addLog(`ERROR: ${data.message || 'Unknown error'}`);
        setIsProcessing(false);
        break;
      }

      default:
        break;
    }
  }, [addLog]);

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setFileInfo(null);
    setStages(initialStages);
    setActiveStage(null);
    setMetrics([]);
    setLogs([]);
    setIsProcessing(false);
    setIsComplete(false);
    setCurrentSize(null);
    setOriginalSize(null);
  }, []);

  return {
    fileInfo,
    stages,
    activeStage,
    metrics,
    logs,
    isProcessing,
    isComplete,
    currentSize,
    originalSize,
    uploadFile,
    runPipeline,
    reset,
    addLog,
  };
}

function formatBytes(bytes) {
  if (bytes == null) return '0 B';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export { formatBytes };
