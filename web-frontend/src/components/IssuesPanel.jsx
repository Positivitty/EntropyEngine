import { useState } from 'react';
import { formatBytes } from '../hooks/useEntropy';

function SeverityBadge({ severity }) {
  const colors = {
    high: '#ff4444',
    medium: '#ffd700',
    low: '#00ff41',
  };
  const color = colors[severity?.toLowerCase()] || '#666';

  return (
    <span className="severity-badge" style={{ color, borderColor: color }}>
      {(severity || 'unknown').toUpperCase()}
    </span>
  );
}

function AffectedFieldsTable({ fields }) {
  if (!fields || fields.length === 0) return null;

  return (
    <div className="affected-fields">
      <div className="affected-fields-title">Affected Fields</div>
      <table className="affected-fields-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Repetition</th>
            <th>Top Values</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field, i) => (
            <tr key={i}>
              <td className="field-name">{field.field_name}</td>
              <td className="field-ratio">
                {field.repetition_ratio != null
                  ? `${(field.repetition_ratio * 100).toFixed(1)}%`
                  : '--'}
              </td>
              <td className="field-values">
                {field.top_values
                  ? field.top_values.map(([val, count]) => `${val} (${count})`).slice(0, 3).join(', ')
                  : '--'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IssueCard({ issue, onSimulate, onApply, onIgnore, simulationResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="issue-card">
      <div className="issue-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="issue-card-title-row">
          <span className="issue-card-title">{issue.title}</span>
          <SeverityBadge severity={issue.severity} />
        </div>
        <div className="issue-impact-bar-container">
          <div className="issue-impact-bar">
            <div
              className="issue-impact-bar-fill"
              style={{ width: `${Math.min(issue.impact_pct || 0, 100)}%` }}
            />
          </div>
          <span className="issue-impact-value">{(issue.impact_pct || 0).toFixed(1)}%</span>
        </div>
        <div className="issue-card-desc">{issue.description}</div>
      </div>

      <div className={`issue-card-expand ${expanded ? 'open' : ''}`}>
        {issue.explanation && (
          <div className="issue-explanation">{issue.explanation}</div>
        )}
        <AffectedFieldsTable fields={issue.affected_fields} />
        {issue.projected_1m && (
          <div className="issue-projected">
            At 1M records:{' '}
            <span className="projected-value">
              {issue.projected_1m.wasted_mb?.toFixed(1)} MB wasted
            </span>
          </div>
        )}
        {simulationResult && (
          <div className="simulation-result-inline">
            Simulated: {formatBytes(simulationResult.original_size)} {'\u2192'}{' '}
            {formatBytes(simulationResult.simulated_size)} (-{simulationResult.reduction_pct}%)
          </div>
        )}
      </div>

      <div className="issue-card-actions">
        <button className="btn-issue btn-simulate" onClick={() => onSimulate(issue.id)}>
          Simulate
        </button>
        <button className="btn-issue btn-apply" onClick={() => onApply(issue.id)}>
          Apply
        </button>
        <button className="btn-issue btn-ignore" onClick={() => onIgnore(issue.id)}>
          Ignore
        </button>
      </div>
    </div>
  );
}

export default function IssuesPanel({
  issues,
  primaryIssue,
  efficiencyScore,
  onSimulate,
  onApply,
  onIgnore,
  simulationResults,
}) {
  const primary = primaryIssue || issues[0];
  const otherIssues = primary
    ? issues.filter((i) => i.id !== primary.id)
    : issues;

  return (
    <div className="issues-panel">
      {/* Primary Issue Callout */}
      {primary && (
        <div className="primary-issue">
          <div className="issue-badge">PRIMARY ISSUE DETECTED</div>
          <div className="issue-title">{primary.title}</div>
          <div className="issue-impact">
            Impact: {(primary.impact_pct || 0).toFixed(1)}% of data size
            {primary.impact_bytes != null && ` (${formatBytes(primary.impact_bytes)} wasted)`}
          </div>
          <button
            className="btn btn-simulate-primary"
            onClick={() => onSimulate(primary.id)}
          >
            Simulate Fix
          </button>
          {primary.projected_1m && (
            <div className="issue-projected-primary">
              At 1M records:{' '}
              <span className="projected-value">
                {primary.projected_1m.wasted_mb?.toFixed(1)} MB wasted
              </span>
            </div>
          )}
        </div>
      )}

      {/* Issue List */}
      {otherIssues.length > 0 && (
        <div className="issues-list">
          {otherIssues.map((issue) => (
            <IssueCard
              key={issue.id}
              issue={issue}
              onSimulate={onSimulate}
              onApply={onApply}
              onIgnore={onIgnore}
              simulationResult={simulationResults?.[issue.id]}
            />
          ))}
        </div>
      )}

      {/* Efficiency Score */}
      {efficiencyScore != null && (
        <div className="efficiency-score-container">
          <div className="efficiency-score-label">Efficiency Score</div>
          <div
            className={`efficiency-score-value ${
              efficiencyScore >= 70 ? 'score-good' : efficiencyScore >= 40 ? 'score-warn' : 'score-bad'
            }`}
          >
            {efficiencyScore}
          </div>
          <div className="efficiency-score-bar">
            <div
              className="efficiency-score-bar-fill"
              style={{
                width: `${efficiencyScore}%`,
                background:
                  efficiencyScore >= 70
                    ? '#00ff41'
                    : efficiencyScore >= 40
                    ? '#ffd700'
                    : '#ff4444',
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
