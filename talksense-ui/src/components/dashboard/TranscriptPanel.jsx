import React, { memo, useRef, useEffect } from "react";

const TranscriptPanelComponent = ({ transcript }) => {
  const bottomRef = useRef(null);
  const prevLengthRef = useRef(0);

  useEffect(() => {
    const currentLength = transcript ? transcript.length : 0;
    if (currentLength > prevLengthRef.current) {
      if (bottomRef.current) {
        bottomRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }
    prevLengthRef.current = currentLength;
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
        className="transcript-list" 
        role="log" 
        aria-live="polite" 
        aria-label="Live conversation transcript"
        style={{ overflowY: "auto", flex: 1 }}
      >
        {transcript && transcript.length > 0 ? (
          <>
            {transcript.map((seg) => {
              const startVal = seg.start != null ? Number(seg.start) : 0;
              const endVal = seg.end != null ? Number(seg.end) : 0;
              const normalizedStart = Math.round(startVal * 1000);
              const normalizedEnd = Math.round(endVal * 1000);
              const stableKey = seg.id || `${seg.speaker || "unknown"}-${normalizedStart}-${normalizedEnd}`;
              const sentimentClass = seg.sentiment_label && typeof seg.sentiment_label === "string"
                ? `sentiment-badge-${seg.sentiment_label.toLowerCase()}`
                : "";

              return (
                <div 
                  key={stableKey} 
                  className="transcript-segment-placeholder" 
                  style={{ 
                    margin: "8px 0", 
                    padding: "8px", 
                    borderRadius: "4px", 
                    background: seg.speaker === "Speaker A" ? "#f0f0f0" : "#e0e0ff" 
                  }}
                >
                  <strong>{seg.speaker || "Unknown Speaker"}:</strong> 
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
            <div ref={bottomRef} />
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
