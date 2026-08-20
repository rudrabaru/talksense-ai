import React, { useState, useEffect, useRef } from "react";

// ── Icons ─────────────────────────────────────────────────────────────────────

function LightbulbIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, color: "#6366f1" }}
    >
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1 .3 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
      <path d="M9 18h6" />
      <path d="M10 22h4" />
    </svg>
  );
}

function InfoIcon({ color }) {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, marginTop: "1px" }}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </svg>
  );
}

function ChevronIcon({ isOpen }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
        transition: "transform 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        flexShrink: 0,
        color: "#94a3b8",
      }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// ── Severity config ───────────────────────────────────────────────────────────

const SEVERITY = {
  high: {
    bg: "rgba(255, 251, 235, 1)",
    border: "rgba(251, 191, 36, 0.4)",
    text: "#92400e",
    icon: "#f59e0b",
  },
  medium: {
    bg: "rgba(239, 246, 255, 1)",
    border: "rgba(147, 197, 253, 0.5)",
    text: "#1e40af",
    icon: "#3b82f6",
  },
  low: {
    bg: "rgba(248, 250, 252, 1)",
    border: "rgba(203, 213, 225, 0.6)",
    text: "#374151",
    icon: "#94a3b8",
  },
};

const getSev = (s) => SEVERITY[s] || SEVERITY.low;

// ── CoachingPanel ─────────────────────────────────────────────────────────────

export default function CoachingPanel({ tips = [] }) {
  const [isOpen, setIsOpen] = useState(true);
  const [isPulsing, setIsPulsing] = useState(false);
  const prevCountRef = useRef(tips.length);

  // Auto-expand + pulse ring when a new tip arrives
  useEffect(() => {
    if (tips.length > prevCountRef.current) {
      setIsOpen(true);
      setIsPulsing(true);
      const t = setTimeout(() => setIsPulsing(false), 900);
      prevCountRef.current = tips.length;
      return () => clearTimeout(t);
    }
    prevCountRef.current = tips.length;
  }, [tips.length]);

  return (
    <div
      className={isPulsing ? "animate-panel-pulse" : ""}
      style={{
        width: "100%",
        borderRadius: "8px",
        outline: "2px solid transparent",
        outlineOffset: "0px",
      }}
    >
      {/* ── Accordion header ── */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        aria-expanded={isOpen}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "11px 0 10px",
          background: "none",
          border: "none",
          cursor: "pointer",
          userSelect: "none",
          borderRadius: "6px",
          transition: "background 0.15s ease",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(99,102,241,0.04)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
          <LightbulbIcon />
          <span
            style={{
              fontWeight: 700,
              fontSize: "0.875rem",
              color: "#1e293b",
              letterSpacing: "-0.015em",
            }}
          >
            Live Coaching
          </span>
          {/* Active tip count badge */}
          {tips.length > 0 && (
            <span
              style={{
                background: isPulsing
                  ? "linear-gradient(135deg, #6366f1, #818cf8)"
                  : "#4f46e5",
                color: "#fff",
                borderRadius: "999px",
                fontSize: "0.62em",
                fontWeight: 800,
                padding: "1px 7px",
                lineHeight: "1.75",
                letterSpacing: "0.03em",
                boxShadow: isPulsing
                  ? "0 0 0 4px rgba(99,102,241,0.18)"
                  : "none",
                transition: "box-shadow 0.3s ease, background 0.3s ease",
              }}
              aria-label={`${tips.length} active coaching tip${tips.length !== 1 ? "s" : ""}`}
            >
              {tips.length}
            </span>
          )}
        </div>
        <ChevronIcon isOpen={isOpen} />
      </button>

      {/* ── Collapsible tip list ── */}
      <div
        style={{
          maxHeight: isOpen ? "148px" : "0px",
          opacity: isOpen ? 1 : 0,
          overflowY: "auto",
          paddingBottom: isOpen ? "10px" : "0px",
          paddingRight: "2px",
          transition: "max-height 0.25s ease, opacity 0.2s ease, padding 0.25s ease",
        }}
      >
          {tips.length === 0 ? (
            <p
              style={{
                margin: 0,
                fontSize: "0.8em",
                color: "#94a3b8",
                fontStyle: "italic",
                paddingBottom: "6px",
              }}
            >
              No coaching suggestions yet.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {tips.map((tip) => {
                const sev = getSev(tip.severity);
                return (
                  <div
                    key={tip.id}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "8px",
                      padding: "7px 10px",
                      borderRadius: "7px",
                      border: `1px solid ${sev.border}`,
                      background: sev.bg,
                    }}
                  >
                    <InfoIcon color={sev.icon} />
                    <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
                      <span
                        style={{
                          fontWeight: 600,
                          fontSize: "0.77em",
                          lineHeight: 1.35,
                          color: sev.text,
                        }}
                      >
                        {tip.title}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75em",
                          lineHeight: 1.4,
                          color: "#475569",
                        }}
                      >
                        {tip.recommendation}
                      </span>
                      {tip.reason && (
                        <span
                          style={{
                            fontSize: "0.7em",
                            opacity: 0.65,
                            fontStyle: "italic",
                            lineHeight: 1.3,
                            color: "#64748b",
                          }}
                        >
                          {tip.reason}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
    </div>
  );
}
