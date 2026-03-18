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

  // New state for Issue Detection, Simulation, Export
  const [issues, setIssues] = useState([]);
  const [primaryIssue, setPrimaryIssue] = useState(null);
  const [efficiencyScore, setEfficiencyScore] = useState(null);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [simulationMode, setSimulationMode] = useState(false);
  const [simulatedSize, setSimulatedSize] = useState(null);
  const [simulationResults, setSimulationResults] = useState({});

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

  const analyzeFile = useCallback(async (fileId) => {
    addLog('ANALYZING FILE FOR ISSUES...');
    try {
      const response = await fetch(`${API_BASE}/analyze/${fileId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
      }

      const data = await response.json();
      const issueList = data.issues || [];
      setIssues(issueList);
      setPrimaryIssue(data.primary_issue || issueList[0] || null);
      setEfficiencyScore(data.efficiency_score ?? null);
      setAnalysisComplete(true);

      addLog(`ANALYSIS COMPLETE: ${issueList.length} issue(s) detected`);
      if (data.efficiency_score != null) {
        addLog(`EFFICIENCY SCORE: ${data.efficiency_score}/100`);
      }

      return data;
    } catch (err) {
      addLog(`ERROR: ${err.message}`);
      throw err;
    }
  }, [addLog]);

  const simulateIssue = useCallback(async (fileId, issueId) => {
    addLog(`SIMULATING FIX FOR ISSUE: ${issueId}...`);
    setSimulationMode(true);

    try {
      const response = await fetch(`${API_BASE}/simulate/${fileId}/${issueId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Simulation failed: ${response.status}`);
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

            if (eventName === 'stage_start') {
              const stageName = parsed.stage?.toUpperCase();
              addLog(`SIMULATING: ${stageName}...`);
              setActiveStage(stageName);
              setStages((prev) =>
                prev.map((s) =>
                  s.name === stageName ? { ...s, status: 'active' } : s
                )
              );
            } else if (eventName === 'stage_complete') {
              const stageName = parsed.stage?.toUpperCase();
              setActiveStage(null);
              setStages((prev) =>
                prev.map((s) =>
                  s.name === stageName ? { ...s, status: 'complete' } : s
                )
              );
              addLog(`${stageName}: ${formatBytes(parsed.input_size)} \u2192 ${formatBytes(parsed.output_size)} [-${parsed.reduction_pct}%]`);
            } else if (eventName === 'simulation_complete') {
              setSimulatedSize(parsed.simulated_size);
              setSimulationResults((prev) => ({
                ...prev,
                [issueId]: parsed,
              }));
              addLog(`SIMULATION COMPLETE: ${formatBytes(parsed.original_size)} \u2192 ${formatBytes(parsed.simulated_size)} [-${parsed.reduction_pct}%]`);
            }
          } catch {
            // Non-JSON data, skip
          }
        }
      }
    } catch (err) {
      addLog(`ERROR: ${err.message}`);
      throw err;
    }
  }, [addLog]);

  const applyFixes = useCallback(async (fileId) => {
    addLog('APPLYING FIXES...');
    try {
      const response = await fetch(`${API_BASE}/apply/${fileId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Apply fixes failed: ${response.status}`);
      }

      const data = await response.json();

      if (data.new_size != null) {
        setCurrentSize(data.new_size);
      }

      if (data.issues) {
        setIssues(data.issues);
      }

      if (data.efficiency_score != null) {
        setEfficiencyScore(data.efficiency_score);
      }

      setSimulationMode(false);
      setSimulatedSize(null);
      setSimulationResults({});

      addLog('FIXES APPLIED SUCCESSFULLY.');

      return data;
    } catch (err) {
      addLog(`ERROR: ${err.message}`);
      throw err;
    }
  }, [addLog]);

  const exportData = useCallback(async (fileId, format, type) => {
    addLog(`EXPORTING ${type.toUpperCase()} AS ${format.toUpperCase()}...`);
    try {
      const response = await fetch(
        `${API_BASE}/export/${fileId}?format=${encodeURIComponent(format)}&type=${encodeURIComponent(type)}`
      );

      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const disposition = response.headers.get('Content-Disposition');
      let filename = `export.${format}`;
      if (disposition) {
        const match = disposition.match(/filename="?([^";\n]+)"?/);
        if (match) filename = match[1];
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      addLog(`EXPORT COMPLETE: ${filename}`);
    } catch (err) {
      addLog(`ERROR: ${err.message}`);
      throw err;
    }
  }, [addLog]);

  const toggleSimulation = useCallback(() => {
    setSimulationMode((prev) => !prev);
  }, []);

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
    // Clear new state
    setIssues([]);
    setPrimaryIssue(null);
    setEfficiencyScore(null);
    setAnalysisComplete(false);
    setSimulationMode(false);
    setSimulatedSize(null);
    setSimulationResults({});
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
    // New exports
    issues,
    primaryIssue,
    efficiencyScore,
    analysisComplete,
    simulationMode,
    simulatedSize,
    simulationResults,
    analyzeFile,
    simulateIssue,
    applyFixes,
    exportData,
    toggleSimulation,
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
