import React, { memo } from "react";

const SessionStatusBar = memo(
  ({ sessionStatus, connectionState, lastSyncAt, mode, onReconnect }) => {
    const getStatusColor = (status) => {
      switch (status) {
        case "active":
          return "#22c55e"; // Green
        case "completed":
          return "#3b82f6"; // Blue
        case "processing":
          return "#eab308"; // Yellow
        case "failed":
        case "interrupted":
          return "#ef4444"; // Red
        default:
          return "#94a3b8"; // Slate
      }
    };

    const getConnectionColor = (state) => {
      switch (state) {
        case "connected":
          return "#22c55e"; // Green
        case "connecting":
        case "reconnecting":
          return "#eab308"; // Yellow
        case "failed":
          return "#ef4444"; // Red
        default:
          return "#94a3b8"; // Slate
      }
    };

    let formattedTime = "Never";
    if (lastSyncAt) {
      let dateObj;
      if (lastSyncAt instanceof Date) {
        dateObj = lastSyncAt;
      } else if (typeof lastSyncAt === "number") {
        const ms = lastSyncAt < 1e11 ? lastSyncAt * 1000 : lastSyncAt;
        dateObj = new Date(ms);
      } else {
        const parsedNum = Number(lastSyncAt);
        if (!isNaN(parsedNum)) {
          const ms = parsedNum < 1e11 ? parsedNum * 1000 : parsedNum;
          dateObj = new Date(ms);
        } else {
          dateObj = new Date(lastSyncAt);
        }
      }

      if (dateObj && !isNaN(dateObj.getTime())) {
        formattedTime = dateObj.toLocaleTimeString();
      } else {
        formattedTime = "Invalid Date";
      }
    }

    return (
      <div
        className="session-status-bar"
        role="status"
        aria-live="polite"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          fontSize: "0.85rem",
        }}
      >
        {/* Mode Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "#f1f5f9", padding: "4px 10px", borderRadius: "16px", color: "#475569", fontWeight: 600 }}>
          <span style={{ fontSize: "1rem" }}>{mode === "sales" ? "📊" : "🎙"}</span>
          <span style={{ textTransform: "capitalize" }}>{mode || "Unknown"}</span>
        </div>

        {/* Status Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "#f8fafc", padding: "4px 10px", borderRadius: "16px", color: "#334155", fontWeight: 600, border: "1px solid #e2e8f0" }}>
          <span
            style={{
              display: "inline-block",
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: getStatusColor(sessionStatus),
            }}
            aria-hidden="true"
          />
          <span style={{ textTransform: "capitalize" }}>
            {sessionStatus || "Unknown"}
          </span>
        </div>

        {/* Connection Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "#f8fafc", padding: "4px 10px", borderRadius: "16px", color: "#334155", fontWeight: 600, border: "1px solid #e2e8f0" }}>
          <span
            style={{
              display: "inline-block",
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: getConnectionColor(connectionState),
            }}
            aria-hidden="true"
          />
          <span style={{ textTransform: "capitalize" }}>
            {connectionState === "connected" ? "Connected" : connectionState || "Unknown"}
          </span>
          {connectionState === "failed" && onReconnect && (
            <button
              onClick={onReconnect}
              style={{
                background: "#ef4444",
                color: "white",
                border: "none",
                borderRadius: "12px",
                padding: "2px 8px",
                fontSize: "0.7rem",
                marginLeft: "4px",
                cursor: "pointer",
                fontWeight: "bold",
              }}
              title="Click to reconnect"
            >
              Reconnect
            </button>
          )}
        </div>

        {/* Last Sync */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "#94a3b8", fontSize: "0.8rem", marginLeft: "4px" }} title={`Last Sync: ${formattedTime}`}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <span style={{ fontWeight: 500 }}>{formattedTime}</span>
        </div>
      </div>
    );
  },
);

SessionStatusBar.displayName = "SessionStatusBar";

export default SessionStatusBar;
