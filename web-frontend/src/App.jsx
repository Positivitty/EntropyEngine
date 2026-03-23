import { useEntropy } from './hooks/useEntropy';
import UploadPanel from './components/UploadPanel';
import PipelineView from './components/PipelineView';
import MetricsPanel from './components/MetricsPanel';
import TerminalPanel from './components/TerminalPanel';
import IssuesPanel from './components/IssuesPanel';
import SimulationBanner from './components/SimulationBanner';
import ScrambleText from './components/ScrambleText';
import AsciiCube from './components/AsciiCube';
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
  } = useEntropy();

  const handleAnalyze = () => {
    if (fileInfo) analyzeFile(fileInfo.fileId);
  };

  const handleSimulate = (issueId) => {
    if (fileInfo) simulateIssue(fileInfo.fileId, issueId);
  };

  const handleApply = () => {
    if (fileInfo) applyFixes(fileInfo.fileId);
  };

  const handleIgnore = () => {};

  return (
    <div className="app-layout">
      <UploadPanel
        fileInfo={fileInfo}
        onUpload={uploadFile}
        onRunPipeline={runPipeline}
        onReset={reset}
        isProcessing={isProcessing}
        isComplete={isComplete}
        analysisComplete={analysisComplete}
        onAnalyze={handleAnalyze}
      />

      <div className="panel panel-center">
        <div className="panel-header" style={{ alignSelf: 'flex-start', width: '100%' }}>
          <span className="header-bar"></span>
          <ScrambleText text="PIPELINE" />
        </div>

        {simulationMode && (
          <SimulationBanner
            simulationMode={simulationMode}
            onToggle={toggleSimulation}
          />
        )}

        {analysisComplete && issues.length > 0 && (
          <IssuesPanel
            issues={issues}
            primaryIssue={primaryIssue}
            efficiencyScore={efficiencyScore}
            onSimulate={handleSimulate}
            onApply={handleApply}
            onIgnore={handleIgnore}
            simulationResults={simulationResults}
          />
        )}

        <PipelineView
          stages={stages}
          activeStage={activeStage}
          currentSize={currentSize}
          originalSize={originalSize}
          embedded
        />

        <AsciiCube
          sizeRatio={originalSize && currentSize != null ? currentSize / originalSize : 1}
          isProcessing={isProcessing}
          isComplete={isComplete}
          activeStage={activeStage}
        />
      </div>

      <MetricsPanel
        metrics={metrics}
        isComplete={isComplete}
        originalSize={originalSize}
        currentSize={currentSize}
        efficiencyScore={efficiencyScore}
        simulationMode={simulationMode}
        simulatedSize={simulatedSize}
        fileInfo={fileInfo}
        onExport={exportData}
      />

      <TerminalPanel logs={logs} />
    </div>
  );
}

export default App;
