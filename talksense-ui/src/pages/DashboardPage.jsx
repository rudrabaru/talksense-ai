import React from "react";
import { useParams } from "react-router-dom";
import { useSessionWebSocket } from "../hooks/useSessionWebSocket";
import SessionStatusBar from "../components/dashboard/SessionStatusBar";
import TranscriptPanel from "../components/dashboard/TranscriptPanel";
import MetricsPanel from "../components/dashboard/MetricsPanel";
import AlertsPanel from "../components/dashboard/AlertsPanel";

export default function DashboardPage() {
  const { sessionId } = useParams();
  const {
    transcript,
    metrics,
    alerts,
    sessionStatus,
    connectionState,
    error,
    lastSyncAt,
    reconnect,
  } = useSessionWebSocket(sessionId);

  const handleReconnect = () => {
    if (typeof reconnect === "function") {
      try {
        reconnect();
      } catch (err) {
        console.error("Failed to trigger reconnect:", err);
      }
    }
  };

  if (connectionState === "idle" || connectionState === "connecting") {
    return (
      <main 
        className="dashboard-loading-skeleton" 
        style={{ padding: "16px", fontFamily: "sans-serif" }}
        aria-busy="true"
        aria-label="Loading session dashboard"
      >
        <div style={{ height: "48px", background: "#e2e8f0", borderRadius: "4px", marginBottom: "16px" }} />
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
          <div style={{ height: "400px", background: "#e2e8f0", borderRadius: "4px" }} />
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ height: "192px", background: "#e2e8f0", borderRadius: "4px" }} />
            <div style={{ height: "192px", background: "#e2e8f0", borderRadius: "4px" }} />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main style={{ padding: "16px" }}>
      {connectionState === "reconnecting" && (
        <div 
          key="banner-reconnecting"
          role="status"
          aria-live="polite"
          style={{ background: "#f59e0b", color: "white", padding: "8px", textAlign: "center", borderRadius: "4px", marginBottom: "12px" }}
        >
          Reconnecting to session...
        </div>
      )}

      {connectionState === "failed" && (
        <div 
          key="banner-failed"
          role="alert"
          style={{ border: "2px solid #ef4444", padding: "16px", margin: "16px 0", background: "#fef2f2", textAlign: "center", borderRadius: "8px" }}
        >
          <h3 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>Connection Failed</h3>
          <p style={{ margin: "0 0 12px 0", color: "#7f1d1d" }}>
            {error || "Unable to connect to the session WebSocket."}
          </p>
          <button 
            onClick={handleReconnect} 
            style={{ padding: "8px 16px", cursor: "pointer", background: "#ef4444", color: "white", border: "none", borderRadius: "4px", fontWeight: "bold" }}
            aria-label="Retry connecting to the session"
          >
            Reconnect
          </button>
        </div>
      )}

      <SessionStatusBar
        sessionStatus={sessionStatus || "unknown"}
        connectionState={connectionState || "disconnected"}
        lastSyncAt={lastSyncAt}
      />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px", marginTop: "16px" }}>
        <div>
          <TranscriptPanel transcript={transcript || []} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <MetricsPanel metrics={metrics || null} />
          <AlertsPanel alerts={alerts || []} />
        </div>
      </div>
    </main>
  );
}

