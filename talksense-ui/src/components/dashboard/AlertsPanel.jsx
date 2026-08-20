import React, { memo, useCallback, useEffect, useRef, useState } from "react";

// ── Alert recommendation copy ─────────────────────────────────────────────────

const ALERT_RECOMMENDATIONS = {
  sentiment_crash: {
    trigger_reason: "Sharp drop in conversation sentiment",
    recommendation:
      "Acknowledge the shift in tone and ask open-ended clarifying questions.",
  },
  speaking_imbalance: {
    trigger_reason: "One person dominating >80% of conversation",
    recommendation:
      "Pause and ask the other party for their thoughts to rebalance.",
  },
  repeated_objections: {
    trigger_reason: "3+ objections detected",
    recommendation: "Stop pitching. Address the underlying concerns directly.",
  },
  long_silence: {
    trigger_reason: ">15s silence with low engagement",
    recommendation: "Re-engage by checking in: 'Does that make sense?'",
  },
  excessive_fillers: {
    trigger_reason: "High filler word density",
    recommendation: "Slow down your pace and speak more deliberately.",
  },
  low_engagement: {
    trigger_reason: "Health score < 40",
    recommendation:
      "Shift the topic or ask a highly relevant question to regain attention.",
  },
  buying_signal: {
    trigger_reason: "Positive purchasing intent detected",
    recommendation:
      "Confirm alignment and move towards next steps or closing.",
  },
};

// ── Level config ──────────────────────────────────────────────────────────────

const LEVEL = {
  critical: {
    accent: "#ef4444",
    bg: "rgba(254, 242, 242, 0.8)",
    labelBg: "#fca5a5",
    labelText: "#7f1d1d",
    recBg: "rgba(255,241,242,0.9)",
    recText: "#9f1239",
    recBorder: "#fecdd3",
  },
  warning: {
    accent: "#f59e0b",
    bg: "rgba(255, 251, 235, 0.8)",
    labelBg: "#fcd34d",
    labelText: "#78350f",
    recBg: "rgba(255,251,235,0.9)",
    recText: "#92400e",
    recBorder: "#fde68a",
  },
  info: {
    accent: "#3b82f6",
    bg: "rgba(239, 246, 255, 0.8)",
    labelBg: "#93c5fd",
    labelText: "#1e3a8a",
    recBg: "rgba(239,246,255,0.9)",
    recText: "#1e40af",
    recBorder: "#bfdbfe",
  },
};

const getLevel = (l) => LEVEL[l] || LEVEL.info;

// ── Helpers ───────────────────────────────────────────────────────────────────

let _toastSeq = 0;

function parseTimestamp(ts) {
  if (ts === undefined || ts === null) return 0;
  if (typeof ts === "number") return ts < 1e11 ? ts * 1000 : ts;
  const n = Number(ts);
  if (!isNaN(n)) return n < 1e11 ? n * 1000 : n;
  const d = Date.parse(ts);
  return isNaN(d) ? 0 : d;
}

function makeStableKey(alert) {
  const ts = parseTimestamp(alert.timestamp);
  return `${ts}|${alert.alert_type || ""}|${alert.level || ""}|${(alert.message || "").substring(0, 40)}`;
}

// ── BellIcon ──────────────────────────────────────────────────────────────────

function BellIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ color: "#94a3b8", flexShrink: 0 }}
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

// ── ToastAlert ────────────────────────────────────────────────────────────────

function ToastAlert({ toast, onDismiss, onPin }) {
  const lv = getLevel(toast.level);
  const rec = ALERT_RECOMMENDATIONS[toast.alert_type] || {};
  const timeStr =
    toast._parsedTimestamp > 0
      ? new Date(toast._parsedTimestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";

  return (
    <div
      className="animate-toast-in"
      role="alert"
      aria-live="polite"
      style={{
        position: "relative",
        background: lv.bg,
        borderRadius: "0 8px 8px 0",
        padding: "9px 10px 8px",
        marginBottom: "5px",
        border: `1px solid rgba(${lv.accent === "#ef4444" ? "239,68,68" : lv.accent === "#f59e0b" ? "245,158,11" : "59,130,246"},0.18)`,
        borderLeft: `3px solid ${lv.accent}`,
        boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
        transition: "box-shadow 0.2s ease",
      }}
    >
      {/* Row 1: level pill + time + actions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "5px",
          gap: "6px",
        }}
      >
        {/* Level pill */}
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            background: lv.labelBg,
            color: lv.labelText,
            borderRadius: "999px",
            fontSize: "0.62em",
            fontWeight: 800,
            padding: "1px 7px",
            lineHeight: "1.7",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {toast.level || "info"}
        </span>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "2px",
            marginLeft: "auto",
          }}
        >
          {timeStr && (
            <small
              style={{
                color: "#94a3b8",
                fontSize: "0.67em",
                marginRight: "2px",
                letterSpacing: "0.01em",
              }}
            >
              {timeStr}
            </small>
          )}

          {/* Pin */}
          <button
            onClick={() => onPin(toast._toastId)}
            title={toast._isPinned ? "Unpin (resumes auto-dismiss)" : "Pin to keep visible"}
            aria-label={toast._isPinned ? "Unpin alert" : "Pin alert"}
            style={{
              background: toast._isPinned ? "rgba(99,102,241,0.1)" : "none",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              padding: "2px 3px",
              fontSize: "10px",
              lineHeight: 1,
              opacity: toast._isPinned ? 1 : 0.3,
              transition: "opacity 0.18s ease, background 0.18s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
            onMouseLeave={(e) =>
              (e.currentTarget.style.opacity = toast._isPinned ? "1" : "0.3")
            }
          >
            📌
          </button>

          {/* Dismiss */}
          <button
            onClick={() => onDismiss(toast._toastId)}
            aria-label="Dismiss alert"
            style={{
              background: "none",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              padding: "2px 4px",
              color: "#94a3b8",
              fontSize: "13px",
              lineHeight: 1,
              fontWeight: 300,
              transition: "color 0.15s ease, background 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "#475569";
              e.currentTarget.style.background = "rgba(0,0,0,0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "#94a3b8";
              e.currentTarget.style.background = "none";
            }}
          >
            ×
          </button>
        </div>
      </div>

      {/* Row 2: message */}
      <p
        style={{
          margin: "0 0 0 0",
          fontWeight: 600,
          color: "#1e293b",
          fontSize: "0.8em",
          lineHeight: 1.45,
        }}
      >
        {toast.message || "Unknown alert"}
      </p>

      {/* Row 3: recommendation */}
      {rec.recommendation && (
        <div
          style={{
            marginTop: "6px",
            fontSize: "0.72em",
            color: lv.recText,
            background: lv.recBg,
            padding: "4px 8px",
            borderRadius: "5px",
            border: `1px solid ${lv.recBorder}`,
            lineHeight: 1.45,
          }}
        >
          💡 {rec.recommendation}
        </div>
      )}

      {/* Auto-dismiss progress bar (only when not pinned) */}
      {!toast._isPinned && (
        <div
          key={`bar-${toast._toastId}-${toast._isPinned}`}
          style={{
            position: "absolute",
            bottom: 0,
            left: 3,
            right: 0,
            height: "2px",
            borderRadius: "0 0 8px 0",
            background: "rgba(0,0,0,0.06)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: "100%",
              background: lv.accent,
              opacity: 0.45,
              animation: "toastProgress 8s linear forwards",
            }}
          />
        </div>
      )}
    </div>
  );
}

// ── AlertsDrawer ──────────────────────────────────────────────────────────────

function AlertsDrawer({ alerts, onClose }) {
  useEffect(() => {
    const h = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(15, 23, 42, 0.3)",
          zIndex: 200,
          backdropFilter: "blur(3px)",
          WebkitBackdropFilter: "blur(3px)",
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="All session alerts"
        className="fixed right-0 top-0 bottom-0 bg-white/95 backdrop-blur-md z-[201] p-5 overflow-y-auto flex flex-col shadow-[-6px_0_40px_rgba(0,0,0,0.12)]"
        style={{
          width: "clamp(300px, 28vw, 390px)",
          animation: "drawerSlideIn 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
        // Basic focus trap workaround: add inert to main content (if we had access to it), but since we don't, we just focus the dialog on mount
        ref={(el) => { if (el) el.focus(); }}
        tabIndex={-1}
      >
        {/* Drawer header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "14px",
            paddingBottom: "12px",
            borderBottom: "1px solid rgba(226,232,240,0.9)",
            flexShrink: 0,
          }}
        >
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: "0.92rem",
                fontWeight: 700,
                color: "#1e293b",
                letterSpacing: "-0.015em",
              }}
            >
              Alert History
            </h3>
            <p
              style={{
                margin: "2px 0 0",
                fontSize: "0.72em",
                color: "#64748b",
              }}
            >
              {alerts.length} alert{alerts.length !== 1 ? "s" : ""} this session
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close alert history"
            style={{
              background: "#f1f5f9",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              width: "30px",
              height: "30px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "16px",
              color: "#475569",
              lineHeight: 1,
              transition: "background 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#e2e8f0")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#f1f5f9")}
          >
            ×
          </button>
        </div>

        {alerts.length === 0 ? (
          <p
            style={{
              color: "#94a3b8",
              fontSize: "0.83em",
              fontStyle: "italic",
              margin: 0,
            }}
          >
            No alerts recorded yet.
          </p>
        ) : (
          alerts.map((alert) => {
            const lv = getLevel(alert.level);
            const rec = ALERT_RECOMMENDATIONS[alert.alert_type] || {};
            const timeStr =
              alert._parsedTimestamp > 0
                ? new Date(alert._parsedTimestamp).toLocaleTimeString()
                : "";
            return (
              <div
                key={alert._toastId}
                style={{
                  background: lv.bg,
                  borderRadius: "0 8px 8px 0",
                  padding: "9px 12px",
                  marginBottom: "7px",
                  border: `1px solid rgba(${lv.accent === "#ef4444" ? "239,68,68" : lv.accent === "#f59e0b" ? "245,158,11" : "59,130,246"},0.15)`,
                  borderLeft: `3px solid ${lv.accent}`,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "4px",
                  }}
                >
                  <span
                    style={{
                      background: lv.labelBg,
                      color: lv.labelText,
                      borderRadius: "999px",
                      fontSize: "0.6em",
                      fontWeight: 800,
                      padding: "1px 7px",
                      textTransform: "uppercase",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {alert.level || "info"}
                  </span>
                  {timeStr && (
                    <small style={{ color: "#94a3b8", fontSize: "0.72em" }}>{timeStr}</small>
                  )}
                </div>
                <p
                  style={{
                    margin: "0 0 0 0",
                    fontWeight: 600,
                    color: "#1e293b",
                    fontSize: "0.82em",
                    lineHeight: 1.45,
                  }}
                >
                  {alert.message}
                </p>
                {rec.trigger_reason && (
                  <div
                    style={{
                      marginTop: "5px",
                      fontSize: "0.73em",
                      color: "#64748b",
                    }}
                  >
                    <strong>Trigger:</strong> {rec.trigger_reason}
                  </div>
                )}
                {rec.recommendation && (
                  <div
                    style={{
                      marginTop: "4px",
                      fontSize: "0.73em",
                      color: lv.recText,
                      background: lv.recBg,
                      padding: "4px 7px",
                      borderRadius: "5px",
                      border: `1px solid ${lv.recBorder}`,
                    }}
                  >
                    💡 {rec.recommendation}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </>
  );
}

// ── AlertsPanel ───────────────────────────────────────────────────────────────

const AlertsPanel = memo(({ alerts }) => {
  const [visibleToasts, setVisibleToasts] = useState([]);
  const [allAlerts, setAllAlerts] = useState([]);
  const [showDrawer, setShowDrawer] = useState(false);

  const seenKeysRef = useRef(new Set());
  const pinnedIdsRef = useRef(new Set());
  const timersRef = useRef({});

  const prevAlertsLengthRef = useRef(0);

  useEffect(() => {
    if (!alerts || alerts.length === 0) return;
    if (alerts.length === prevAlertsLengthRef.current) return;
    prevAlertsLengthRef.current = alerts.length;

    const newItems = [];
    alerts.forEach((alert) => {
      const tsMs = parseTimestamp(alert.timestamp);
      const key = makeStableKey({ ...alert, timestamp: tsMs });
      if (seenKeysRef.current.has(key)) return;
      seenKeysRef.current.add(key);

      newItems.push({
        ...alert,
        _parsedTimestamp: tsMs,
        _toastId: `toast-${++_toastSeq}`,
        _isPinned: false,
      });
    });

    if (newItems.length === 0) return;

    setAllAlerts((prev) => [...newItems, ...prev]);
    setVisibleToasts((prev) => [...newItems, ...prev].slice(0, 3));

    newItems.forEach((item) => {
      const tid = setTimeout(() => {
        setVisibleToasts((prev) =>
          prev.filter(
            (t) =>
              t._toastId !== item._toastId ||
              pinnedIdsRef.current.has(t._toastId)
          )
        );
        delete timersRef.current[item._toastId];
      }, 8000);
      timersRef.current[item._toastId] = tid;
    });
  }, [alerts]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      Object.values(timers).forEach(clearTimeout);
    };
  }, []);

  const handleDismiss = useCallback((toastId) => {
    if (timersRef.current[toastId]) {
      clearTimeout(timersRef.current[toastId]);
      delete timersRef.current[toastId];
    }
    pinnedIdsRef.current.delete(toastId);
    setVisibleToasts((prev) => prev.filter((t) => t._toastId !== toastId));
  }, []);

  const handlePin = useCallback((toastId) => {
    setVisibleToasts((prev) =>
      prev.map((t) => {
        if (t._toastId !== toastId) return t;
        const nowPinned = !t._isPinned;
        if (nowPinned) {
          pinnedIdsRef.current.add(toastId);
          if (timersRef.current[toastId]) {
            clearTimeout(timersRef.current[toastId]);
            delete timersRef.current[toastId];
          }
        } else {
          pinnedIdsRef.current.delete(toastId);
          const tid = setTimeout(() => {
            setVisibleToasts((p) =>
              p.filter(
                (x) =>
                  x._toastId !== toastId ||
                  pinnedIdsRef.current.has(x._toastId)
              )
            );
            delete timersRef.current[toastId];
          }, 4000);
          timersRef.current[toastId] = tid;
        }
        return { ...t, _isPinned: nowPinned };
      })
    );
  }, []);

  const hiddenCount = Math.max(0, allAlerts.length - visibleToasts.length);

  return (
    <div style={{ width: "100%" }}>
      {/* Section header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 0 7px",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <BellIcon />
          <h3
            style={{
              margin: 0,
              fontWeight: 700,
              fontSize: "0.875rem",
              color: "#1e293b",
              letterSpacing: "-0.015em",
            }}
          >
            Real-Time Alerts
          </h3>
          {/* Live indicator dot when toasts exist */}
          {visibleToasts.length > 0 && (
            <span
              className="animate-pulse-subtle"
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#ef4444",
                display: "inline-block",
                flexShrink: 0,
              }}
              aria-hidden="true"
            />
          )}
        </div>

        {allAlerts.length > 0 && (
          <button
            onClick={() => setShowDrawer(true)}
            style={{
              background: "rgba(241,245,249,0.9)",
              border: "1px solid #e2e8f0",
              borderRadius: "999px",
              padding: "2px 9px",
              fontSize: "0.67em",
              fontWeight: 600,
              color: "#475569",
              cursor: "pointer",
              letterSpacing: "0.01em",
              transition: "background 0.15s ease, border-color 0.15s ease",
              whiteSpace: "nowrap",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "#e2e8f0";
              e.currentTarget.style.borderColor = "#cbd5e1";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(241,245,249,0.9)";
              e.currentTarget.style.borderColor = "#e2e8f0";
            }}
          >
            View all ({allAlerts.length})
          </button>
        )}
      </div>

      {/* Toast stack */}
      <div style={{ minHeight: "44px", paddingBottom: "4px" }}>
        {visibleToasts.length === 0 ? (
          <p
            style={{
              margin: 0,
              fontSize: "0.8em",
              color: "#94a3b8",
              fontStyle: "italic",
              padding: "2px 0 8px",
            }}
          >
            No active alerts.
          </p>
        ) : (
          visibleToasts.map((toast) => (
            <ToastAlert
              key={toast._toastId}
              toast={toast}
              onDismiss={handleDismiss}
              onPin={handlePin}
            />
          ))
        )}

        {/* Overflow chip */}
        {hiddenCount > 0 && visibleToasts.length > 0 && (
          <button
            onClick={() => setShowDrawer(true)}
            style={{
              width: "100%",
              textAlign: "center",
              fontSize: "0.71em",
              color: "#6366f1",
              fontWeight: 600,
              background: "rgba(238,242,255,0.8)",
              border: "1px dashed #c7d2fe",
              borderRadius: "6px",
              padding: "4px 8px",
              cursor: "pointer",
              marginTop: "2px",
              transition: "background 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#e0e7ff")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(238,242,255,0.8)")}
          >
            +{hiddenCount} more — View all alerts
          </button>
        )}
      </div>

      {/* History drawer */}
      {showDrawer && (
        <AlertsDrawer alerts={allAlerts} onClose={() => setShowDrawer(false)} />
      )}
    </div>
  );
});

AlertsPanel.displayName = "AlertsPanel";
export default AlertsPanel;
