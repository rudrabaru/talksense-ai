import React, { memo, useRef, useEffect, useMemo } from "react";

// A palette of distinct background colors for speaker differentiation
const SPEAKER_COLORS = [
  "#f0f4ff", // soft blue
  "#f0fff4", // soft green
  "#fff7f0", // soft orange
  "#fdf0ff", // soft purple
  "#f0feff", // soft cyan
  "#fffbf0", // soft yellow
];

const TranscriptPanelComponent = ({ transcript }) => {
  const containerRef = useRef(null);
  const autoScrollRef = useRef(true);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  const speakerColorMap = useMemo(() => {
    const map = {};
    let idx = 0;
    (transcript || []).forEach((seg) => {
      const speaker = seg.speaker || "Unknown Speaker";
      if (!(speaker in map)) {
        map[speaker] = SPEAKER_COLORS[idx % SPEAKER_COLORS.length];
        idx++;
      }
    });
    return map;
  }, [transcript]);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div 
      className="transcript-panel-placeholder" 
      style={{ 
        border: "1px solid #ccc", 
        padding: "16px", 
        height: "100%", 
        maxHeight: "500px", 
        display: "flex", 
        flexDirection: "column" 
      }}
    >
      <h3>Live Transcript</h3>
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="transcript-list" 
        role="log" 
        aria-live="polite" 
        aria-label="Live conversation transcript"
        style={{ overflowY: "auto", flex: 1 }}
      >
        {transcript && transcript.length > 0 ? (
          <>
            {transcript.map((seg, idx) => {
              const startVal = seg.start != null ? Number(seg.start) : 0;
              const endVal = seg.end != null ? Number(seg.end) : 0;
              const normalizedStart = Math.round(startVal * 1000);
              const normalizedEnd = Math.round(endVal * 1000);
              const stableKey = seg.id 
                ? `${seg.id}-${idx}` 
                : `${seg.speaker || "unknown"}-${normalizedStart}-${normalizedEnd}-${idx}`;
              const sentimentClass = seg.sentiment_label && typeof seg.sentiment_label === "string"
                ? `sentiment-badge-${seg.sentiment_label.toLowerCase()}`
                : "";
              const speakerLabel = seg.speaker || "Unknown Speaker";
              const bgColor = speakerColorMap[speakerLabel] || SPEAKER_COLORS[0];

              return (
                <div 
                  key={stableKey} 
                  className="transcript-segment-placeholder" 
                  style={{ 
                    margin: "8px 0", 
                    padding: "8px", 
                    borderRadius: "4px", 
                    background: bgColor
                  }}
                >
                  <strong>{speakerLabel}:</strong> 
                  <span style={{ fontSize: "0.8em", color: "#666", marginLeft: "8px" }}>
                    [{startVal.toFixed(1)}s - {endVal.toFixed(1)}s]
                  </span>
                  {seg.sentiment_label && (
                    <span 
                      className={sentimentClass} 
                      style={{ 
                        marginLeft: "8px", 
                        padding: "2px 6px", 
                        borderRadius: "10px", 
                        fontSize: "0.8em", 
                        background: "#ddd" 
                      }}
                    >
                      {seg.sentiment_label}
                    </span>
                  )}
                  <p style={{ margin: "4px 0 0 0" }}>{seg.text || ""}</p>
                </div>
              );
            })}
          </>
        ) : (
          <p>No transcription yet...</p>
        )}
      </div>
    </div>
  );
};

const TranscriptPanel = memo(TranscriptPanelComponent);
TranscriptPanel.displayName = "TranscriptPanel";

export default TranscriptPanel;
