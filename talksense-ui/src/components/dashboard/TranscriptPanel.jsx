import React, { memo, useRef, useEffect, useMemo, useState } from "react";

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
  const listRef = useRef(null);
  const prevLengthRef = useRef(0);

  // Build a stable speaker → color index map from the current transcript
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

  const [isNearBottom, setIsNearBottom] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const isUserNearBottomRef = useRef(true);

  const handleScroll = (e) => {
    const list = e.target;
    const scrollHeight = list.scrollHeight;
    const scrollTop = list.scrollTop;
    const clientHeight = list.clientHeight;
    
    // User intent is the single source of truth.
    const gap = scrollHeight - scrollTop - clientHeight;
    const nearBottom = gap <= 150;
    
    isUserNearBottomRef.current = nearBottom;
    setIsNearBottom(nearBottom);
    
    if (nearBottom) {
      setUnreadCount(0);
    }
  };

  useEffect(() => {
    const currentLength = transcript ? transcript.length : 0;
    
    // Only attempt scroll when new segments actually arrive
    if (currentLength > prevLengthRef.current) {
      if (listRef.current && isUserNearBottomRef.current) {
        const list = listRef.current;
        // Deterministic scroll: push to bottom on next frame to ensure React paint completes
        requestAnimationFrame(() => {
          list.scrollTop = list.scrollHeight;
        });
      } else {
        setUnreadCount(prev => prev + (currentLength - prevLengthRef.current));
      }
    }
    
    prevLengthRef.current = currentLength;
  }, [transcript]);
  return (
    <div 
      className="transcript-panel-placeholder bg-white rounded-xl shadow-sm border border-slate-200" 
      style={{ 
        padding: "16px", 
        flex: 1, 
        minHeight: 0, 
        display: "flex", 
        flexDirection: "column",
        position: "relative"
      }}
    >
      <h3 className="font-semibold text-slate-800 text-lg mb-3">Live Transcript</h3>
      
      <button
        onClick={() => {
          if (listRef.current) {
            listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
            isUserNearBottomRef.current = true;
            setIsNearBottom(true);
            setUnreadCount(0);
          }
        }}
        aria-label="Jump to latest transcript"
        className={`absolute bottom-6 right-6 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg rounded-full px-4 py-2 text-sm font-semibold transition-all duration-300 z-10 flex items-center gap-2 ${
          isNearBottom ? "opacity-0 translate-y-4 pointer-events-none" : "opacity-100 translate-y-0"
        }`}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
        Live {unreadCount > 0 ? `(${unreadCount})` : ""}
      </button>

      <div 
        ref={listRef}
        onScroll={handleScroll}
        className="transcript-list" 
        role="log" 
        aria-live="polite" 
        aria-label="Live conversation transcript"
        style={{ overflowY: "auto", overflowX: "hidden", flex: 1, minHeight: 0 }}
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
                    background: bgColor,
                    wordBreak: "break-word",
                    overflowWrap: "break-word"
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
