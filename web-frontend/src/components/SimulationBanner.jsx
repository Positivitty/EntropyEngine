export default function SimulationBanner({ simulationMode, onToggle }) {
  if (!simulationMode) return null;

  return (
    <div className="simulation-banner">
      <div className="simulation-banner-content">
        <span className="simulation-warning-icon">!</span>
        <span className="simulation-banner-text">
          SIMULATION ACTIVE — Original data unchanged
        </span>
      </div>
      <div className="simulation-banner-actions">
        <button
          className="btn-sim-toggle"
          onClick={() => onToggle()}
        >
          View Original
        </button>
        <button
          className="btn-sim-toggle btn-sim-active"
          disabled
        >
          View Simulated
        </button>
      </div>
    </div>
  );
}
