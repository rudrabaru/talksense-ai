import React from "react";
import { Lightbulb, Info } from "lucide-react";

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
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 px-1">
        <Lightbulb className="w-5 h-5 text-indigo-500" />
        <h3 className="font-semibold text-slate-800">Live Coaching</h3>
      </div>
      <div className="flex flex-col gap-2">
        {tips.map((tip) => (
          <div
            key={tip.id}
            className={`flex items-start gap-3 p-3 rounded-lg border ${getSeverityStyle(
              tip.severity
            )} shadow-sm transition-all`}
          >
            <Info className={`w-5 h-5 mt-0.5 shrink-0 ${getIconStyle(tip.severity)}`} />
            <div className="flex flex-col">
              <span className="font-semibold text-sm">{tip.title}</span>
              <span className="text-sm mt-0.5">{tip.recommendation}</span>
              {tip.reason && (
                <span className="text-xs opacity-80 mt-1 italic">
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
