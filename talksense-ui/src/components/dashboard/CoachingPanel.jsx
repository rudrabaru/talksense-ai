import React from "react";

function LightbulbIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1 .3 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" />
      <path d="M9 18h6" />
      <path d="M10 22h4" />
    </svg>
  );
}

function InfoIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </svg>
  );
}

export default function CoachingPanel({ tips = [] }) {
  if (!tips || tips.length === 0) {
    return null;
  }

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case "high":
        return "bg-amber-50 border-amber-500/30 text-amber-900";
      case "medium":
        return "bg-blue-50 border-blue-500/30 text-blue-900";
      case "low":
      default:
        return "bg-slate-50 border-slate-500/30 text-slate-900";
    }
  };

  const getIconStyle = (severity) => {
    switch (severity) {
      case "high":
        return "text-amber-500";
      case "medium":
        return "text-blue-500";
      case "low":
      default:
        return "text-slate-500";
    }
  };

  return (
    <div className="flex flex-col gap-3 bg-white rounded-xl shadow-sm border border-slate-200" style={{ padding: "16px", maxHeight: "100%", overflowY: "auto" }}>
      <div className="flex items-center gap-2">
        <LightbulbIcon className="w-5 h-5 text-indigo-500" />
        <h3 className="font-semibold text-slate-800 text-lg">Live Coaching</h3>
      </div>
      <div className="flex flex-col gap-2">
        {tips.map((tip) => (
          <div
            key={tip.id}
            className={`flex items-start gap-3 py-2 px-3 rounded-lg border ${getSeverityStyle(
              tip.severity
            )} shadow-sm transition-all`}
          >
            <InfoIcon className={`w-5 h-5 mt-0.5 shrink-0 ${getIconStyle(tip.severity)}`} />
            <div className="flex flex-col gap-0.5">
              <span className="font-semibold text-sm leading-tight">{tip.title}</span>
              <span className="text-sm leading-tight">{tip.recommendation}</span>
              {tip.reason && (
                <span className="text-xs opacity-80 italic leading-tight">
                  {tip.reason}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
