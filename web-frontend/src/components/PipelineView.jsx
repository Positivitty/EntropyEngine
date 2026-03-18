import { formatBytes } from '../hooks/useEntropy';

const STAGE_LABELS = {
  INPUT: 'Input',
  DEDUP: 'Dedup',
  ENCODE: 'Encode',
  TRIM: 'Trim',
  COMPRESS: 'Compress',
};

export default function PipelineView({ stages, activeStage, currentSize, originalSize }) {
  const sizePercent = originalSize && currentSize != null
    ? Math.max((currentSize / originalSize) * 100, 5)
    : 100;

  const getConnectorState = (index) => {
    if (index >= stages.length - 1) return 'idle';
    const current = stages[index];
    const next = stages[index + 1];
    if (current.status === 'complete' && next.status === 'active') return 'active';
    if (current.status === 'complete' && (next.status === 'complete' || next.status === 'active')) return 'complete';
    if (current.status === 'active') return 'active';
    return 'idle';
  };

  return (
    <div className="panel panel-center">
      <div className="panel-header" style={{ alignSelf: 'flex-start', width: '100%' }}>
        <span className="dot"></span>
        Pipeline
      </div>

      <div className="pipeline-container">
        {stages.map((stage, i) => (
          <div key={stage.name} style={{ display: 'flex', alignItems: 'center' }}>
            <div className={`pipeline-node ${stage.status}`}>
              <div className="node-box">
                {stage.name}
              </div>
              <div className="node-label">{STAGE_LABELS[stage.name]}</div>
            </div>
            {i < stages.length - 1 && (
              <div className={`pipeline-connector ${getConnectorState(i)}`}>
                <div className="connector-line"></div>
                <div className="connector-arrow"></div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="size-bar-container">
        <div className="size-bar-label">
          <span>Data Size</span>
          <span className="size-value">
            {currentSize != null ? formatBytes(currentSize) : '--'}
            {originalSize != null && currentSize != null && currentSize !== originalSize && (
              <span style={{ color: '#ffd700', marginLeft: '8px' }}>
                (-{((1 - currentSize / originalSize) * 100).toFixed(1)}%)
              </span>
            )}
          </span>
        </div>
        <div className="size-bar-track">
          <div
            className="size-bar-fill"
            style={{ width: `${originalSize ? sizePercent : 100}%` }}
          >
            {currentSize != null && (
              <span className="size-text">{formatBytes(currentSize)}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
