import React, { memo } from "react";

const MetricsPanel = memo(({ metrics }) => {
  const hasValidMetrics = !!(
    metrics && (
      metrics.health_score != null ||
      metrics.speaking_ratio != null ||
      metrics.filler_count != null ||
      (metrics.duration_seconds != null && !isNaN(Number(metrics.duration_seconds))) ||
      (metrics.participation != null &&
        typeof metrics.participation === "object" &&
        Object.keys(metrics.participation).length > 0)
    )
  );

  if (!hasValidMetrics) {
    return (
      <div 
        className="metrics-panel-placeholder" 
        role="region" 
        aria-label="Conversation intelligence metrics" 
        style={{ border: "1px solid #ccc", padding: "16px", height: "100%" }}
      >
        <h3>Conversation Intelligence</h3>
        <p>No metrics available.</p>
      </div>
    );
  }

  const {
    health_score,
    speaking_ratio,
    participation,
    filler_count,
    duration_seconds,
  } = metrics;

  const sortedParticipation = participation && typeof participation === "object"
    ? Object.entries(participation).sort(([a], [b]) => a.localeCompare(b))
    : [];

  const parsedDuration = duration_seconds != null ? Number(duration_seconds) : NaN;
  const durationText = !isNaN(parsedDuration) ? `${parsedDuration.toFixed(1)}s` : "N/A";

  return (
    <div 
      className="metrics-panel-placeholder" 
      role="region" 
      aria-label="Conversation intelligence metrics" 
      style={{ border: "1px solid #ccc", padding: "16px", height: "100%" }}
    >
      <h3>Conversation Intelligence</h3>
      <div className="metrics-content">
        <div style={{ margin: "12px 0" }}>
          <strong>Health Score:</strong> {health_score != null ? `${health_score}%` : "N/A"}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Speaking Ratio:</strong> {speaking_ratio ?? "N/A"}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Participation:</strong>
          {sortedParticipation.length > 0 ? (
            <ul>
              {sortedParticipation.map(([speaker, percent]) => (
                <li key={speaker}>
                  {speaker}: {percent != null ? `${percent}%` : "N/A"}
                </li>
              ))}
            </ul>
          ) : (
            " N/A"
          )}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Filler Words:</strong> {filler_count ?? "N/A"}
        </div>
        <div style={{ margin: "12px 0" }}>
          <strong>Duration:</strong> {durationText}
        </div>
      </div>
    </div>
  );
});

MetricsPanel.displayName = "MetricsPanel";

export default MetricsPanel;

