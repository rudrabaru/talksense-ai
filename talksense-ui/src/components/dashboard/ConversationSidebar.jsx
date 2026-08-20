import React, { memo } from "react";
import CoachingPanel from "./CoachingPanel";
import AlertsPanel from "./AlertsPanel";
import MetricsPanel from "./MetricsPanel";

/**
 * ConversationSidebar
 *
 * Three isolated flex zones — none can grow large enough to displace siblings:
 *
 *   ┌──────────────────────────────────┐  flexShrink: 0
 *   │  Live Coaching   (accordion)     │  ← bounded by internal maxHeight
 *   ├──────────────────────────────────┤  flexShrink: 0
 *   │  Real-Time Alerts  (toast-stack) │  ← bounded by toast-stack footprint
 *   ├──────────────────────────────────┤
 *   │  Session Metrics  (flex: 1)      │  ← always fills remaining space
 *   └──────────────────────────────────┘
 */
const ConversationSidebar = memo(
  ({ tips, alerts, metrics, sessionStatus, lastSyncAt, mode }) => {
    return (
      <div
        className="bg-white rounded-xl border border-slate-200"
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
          boxSizing: "border-box",
          padding: "0 14px",
          boxShadow:
            "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04), inset 0 -1px 0 rgba(226,232,240,0.6)",
        }}
      >
        {/* ── Zone 1: Live Coaching ─────────────────────────────────────── */}
        <div
          style={{
            flexShrink: 0,
            borderBottom: "1px solid rgba(226, 232, 240, 0.7)",
          }}
        >
          <CoachingPanel tips={tips} />
        </div>

        {/* ── Zone 2: Real-Time Alerts ──────────────────────────────────── */}
        <div
          style={{
            flexShrink: 0,
            borderBottom: "1px solid rgba(226, 232, 240, 0.7)",
          }}
        >
          <AlertsPanel alerts={alerts} />
        </div>

        {/* ── Zone 3: Session Metrics (always visible, own scroll) ──────── */}
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            paddingRight: "2px",
            paddingBottom: "12px",
          }}
        >
          <MetricsPanel
            metrics={metrics}
            sessionStatus={sessionStatus}
            lastSyncAt={lastSyncAt}
            mode={mode}
          />
        </div>
      </div>
    );
  }
);

ConversationSidebar.displayName = "ConversationSidebar";
export default ConversationSidebar;
