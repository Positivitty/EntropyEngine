import { useEntropy } from './hooks/useEntropy';
import UploadPanel from './components/UploadPanel';
import PipelineView from './components/PipelineView';
import MetricsPanel from './components/MetricsPanel';
import TerminalPanel from './components/TerminalPanel';
import './App.css';

function App() {
  const {
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
  } = useEntropy();

  return (
    <div className="app-layout">
      <UploadPanel
        fileInfo={fileInfo}
        onUpload={uploadFile}
        onRunPipeline={runPipeline}
        onReset={reset}
        isProcessing={isProcessing}
        isComplete={isComplete}
      />

      <PipelineView
        stages={stages}
        activeStage={activeStage}
        currentSize={currentSize}
        originalSize={originalSize}
      />

      <MetricsPanel
        metrics={metrics}
        isComplete={isComplete}
        originalSize={originalSize}
        currentSize={currentSize}
      />

      <TerminalPanel logs={logs} />
    </div>
  );
}

export default App;
