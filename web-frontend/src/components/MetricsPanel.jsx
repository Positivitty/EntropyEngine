import { useEffect, useState } from 'react';
import { formatBytes } from '../hooks/useEntropy';
import ScrambleText from './ScrambleText';

function AnimatedNumber({ value, duration = 500, suffix = '' }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value == null) return;
    const start = performance.now();
    const from = 0;
    const to = value;

    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(from + (to - from) * eased);

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  if (value == null) return null;

  return (
    <span>
      {typeof value === 'number' && value % 1 !== 0
        ? display.toFixed(1)
        : Math.round(display)}
      {suffix}
    </span>
  );
}

export default function MetricsPanel({
  metrics,
  isComplete,
  originalSize,
  currentSize,
  efficiencyScore,
  simulationMode,
  simulatedSize,
  fileInfo,
  onExport,
}) {
  const totalReduction = originalSize && currentSize != null
    ? ((1 - currentSize / originalSize) * 100)
    : 0;

  const scoreColor = efficiencyScore >= 70 ? '#00ff41' : efficiencyScore >= 40 ? '#ffd700' : '#ff4444';

  return (
    <div className="panel panel-right">
      <div className="panel-header">
        <span className="header-bar"></span>
        <ScrambleText text="METRICS" />
      </div>

      {/* Efficiency Score */}
      {efficiencyScore != null && (
        <div className="metrics-efficiency">
          <div className="efficiency-label">Efficiency Score</div>
          <div className="efficiency-big-number" style={{ color: scoreColor }}>
            <AnimatedNumber value={efficiencyScore} />
          </div>
          <div className="efficiency-bar-track">
            <div
              className="efficiency-bar-fill"
              style={{
                width: `${efficiencyScore}%`,
                background: scoreColor,
              }}
            />
          </div>
        </div>
      )}

      {/* Simulation size comparison */}
      {simulationMode && simulatedSize != null && (
        <div className="metrics-simulation-compare">
          <div className="sim-compare-row">
            <span className="sim-compare-label">Original</span>
            <span className="sim-compare-value">{formatBytes(currentSize)}</span>
          </div>
          <div className="sim-compare-row">
            <span className="sim-compare-label" style={{ color: '#ffd700' }}>Simulated</span>
            <span className="sim-compare-value" style={{ color: '#ffd700' }}>{formatBytes(simulatedSize)}</span>
          </div>
          {currentSize != null && simulatedSize != null && (
            <div className="sim-compare-savings">
              Savings: {formatBytes(currentSize - simulatedSize)} ({((1 - simulatedSize / currentSize) * 100).toFixed(1)}%)
            </div>
          )}
        </div>
      )}

      {metrics.length === 0 && efficiencyScore == null ? (
        <div className="empty-state">
          <div className="empty-icon">&equiv;</div>
          <div>Awaiting data</div>
        </div>
      ) : (
        <div className="metrics-list">
          {metrics.map((m) => (
            <div key={m.stage} className="metric-item">
              <div className="metric-stage">{m.stage}</div>
              <div className="metric-sizes">
                <span>{formatBytes(m.inputSize)}</span>
                {' \u2192 '}
                <span>{formatBytes(m.outputSize)}</span>
              </div>
              <div className="metric-reduction">
                <AnimatedNumber value={m.reduction} suffix="%" /> reduction
              </div>
              <div className="metric-bar">
                <div
                  className="metric-bar-fill"
                  style={{ width: `${100 - m.reduction}%` }}
                ></div>
              </div>
            </div>
          ))}

          {isComplete && originalSize != null && (
            <div className="metrics-summary">
              <div className="summary-label">Final Result</div>
              <div className="summary-value">
                <AnimatedNumber value={totalReduction} suffix="%" />
              </div>
              <div className="summary-detail">
                <span>{formatBytes(originalSize)}</span>
                {' \u2192 '}
                <span>{formatBytes(currentSize)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Export Buttons */}
      {fileInfo && (
        <div className="metrics-export-section">
          <button
            className="btn btn-export"
            onClick={() => onExport(fileInfo.fileId, 'json', 'data')}
          >
            Export Data
          </button>
          <button
            className="btn btn-export"
            onClick={() => onExport(fileInfo.fileId, 'json', 'report')}
          >
            Export Report
          </button>
        </div>
      )}
    </div>
  );
}
