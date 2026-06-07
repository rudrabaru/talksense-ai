import React, { memo } from "react";

const SessionStatusBar = memo(({ 
  sessionStatus, 
  connectionState, 
  lastSyncAt 
}) => {
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
      style={{ display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #ccc", padding: "12px", background: "#fafafa" }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <strong>Session Status:</strong>
        <span 
          style={{ 
            display: "inline-block", 
            width: "8px", 
            height: "8px", 
            borderRadius: "50%", 
            background: getStatusColor(sessionStatus) 
          }} 
          aria-hidden="true"
        />
        <span style={{ textTransform: "capitalize" }}>{sessionStatus || "Unknown"}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <strong>Connection:</strong>
        <span 
          style={{ 
            display: "inline-block", 
            width: "8px", 
            height: "8px", 
            borderRadius: "50%", 
            background: getConnectionColor(connectionState) 
          }} 
          aria-hidden="true"
        />
        <span style={{ textTransform: "capitalize" }}>{connectionState || "Unknown"}</span>
      </div>

      <div>
        <strong>Last Synced:</strong> <span>{formattedTime}</span>
      </div>
    </div>
  );
});

SessionStatusBar.displayName = "SessionStatusBar";

export default SessionStatusBar;


