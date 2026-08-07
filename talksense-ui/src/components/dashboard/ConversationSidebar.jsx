import React, { memo } from "react";
import CoachingPanel from "./CoachingPanel";
import AlertsPanel from "./AlertsPanel";
import MetricsPanel from "./MetricsPanel";

const ConversationSidebar = memo(({ tips, alerts, metrics, sessionStatus, lastSyncAt, mode }) => {
  return (
    <div 
      className="bg-white rounded-xl shadow-sm border border-slate-200"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
        padding: "16px",
        boxSizing: "border-box"
      }}
    >
      <div style={{ height: "auto", flexShrink: 0, borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "8px" }}>
        <CoachingPanel tips={tips} />
      </div>

      <div style={{ height: "auto", flexShrink: 0, borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "8px" }}>
        <AlertsPanel alerts={alerts} />
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: "auto", paddingRight: "4px" }}>
        <MetricsPanel 
          metrics={metrics}
          sessionStatus={sessionStatus}
          lastSyncAt={lastSyncAt}
          mode={mode}
        />
      </div>
    </div>
  );
});

ConversationSidebar.displayName = "ConversationSidebar";

export default ConversationSidebar;
