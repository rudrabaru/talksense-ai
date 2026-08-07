import { useEffect, useRef, useState } from "react";
import { MicVAD } from "@ricky0123/vad-web";

const WS_URL = "ws://localhost:8000/ws/transcript";

export default function TranscriptLive() {
  // ─── Day 1: WebSocket receive ──────────────────────────────────────────────
  const [messages, setMessages] = useState([]);
  const [wsStatus, setWsStatus] = useState("connecting");

  // ─── Day 2: Local mic chunks ───────────────────────────────────────────────
  const [micStatus, setMicStatus] = useState("idle"); // idle | active | error
  const [chunks, setChunks] = useState([]);

  // ─── Day 3: Audio streaming over WebSocket ─────────────────────────────────
  const [streamStatus, setStreamStatus] = useState("idle"); // idle | streaming | error
  const [sentChunks, setSentChunks] = useState([]);
  const [acks, setAcks] = useState(0);

  // ─── Day 4: Voice Activity Detection ───────────────────────────────────────
  const [vadStatus, setVadStatus] = useState("idle"); // idle | loading | listening | error
  const [speechEvents, setSpeechEvents] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Refs
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const wsRef = useRef(null);
  const streamWsRef = useRef(null);
  const streamRecorderRef = useRef(null);
  const streamMicRef = useRef(null);
  const vadRef = useRef(null);

  // ─── Day 1: Connect to WS and receive greeting messages ────────────────────
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] Connected to", WS_URL);
      setWsStatus("live");
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.text) {
        setMessages((prev) => [...prev, data.text]);
      }
    };
    ws.onclose = () => {
      console.log("[WS] Disconnected");
      setWsStatus("disconnected");
    };
    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
      setWsStatus("disconnected");
    };

    return () => ws.close();
  }, []);

  // ─── Day 2: Local mic capture (no network) ────────────────────────────────
  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      console.log("Microphone access granted", stream);
      setMicStatus("active");

      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        const time = new Date().toLocaleTimeString();
        const size = event.data.size;
        console.log(time, "Chunk Size:", size);
        setChunks((prev) => [...prev.slice(-19), { time, size }]);
      };

      recorder.start(1000);
    } catch (err) {
      console.error("Mic error:", err);
      setMicStatus("error");
    }
  };

  const stopMic = () => {
    recorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setMicStatus("idle");
  };

  // ─── Day 3: Stream audio chunks to FastAPI via WebSocket ───────────────────
  const startStreaming = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamMicRef.current = stream;

      const ws = new WebSocket(WS_URL);
      streamWsRef.current = ws;

      ws.onopen = () => {

        setStreamStatus("streaming");

        const recorder = new MediaRecorder(stream);
        streamRecorderRef.current = recorder;

        recorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            const time = new Date().toLocaleTimeString();


            const buffer = await event.data.arrayBuffer();
            ws.send(buffer);

            setSentChunks((prev) => [
              ...prev.slice(-19),
              { time, size: event.data.size, status: "sent" },
            ]);
          }
        };

        recorder.start(1000);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "chunk_ack") {
          setAcks((prev) => prev + 1);
        }
        // Day 1 greeting messages also arrive here
        if (data.text) {

        }
      };

      ws.onclose = () => {

        setStreamStatus("idle");
      };

      ws.onerror = (err) => {
        console.error("[Day3] WebSocket Error:", err);
        setStreamStatus("error");
      };
    } catch (err) {
      console.error("[Day3] Error:", err);
      setStreamStatus("error");
    }
  };

  const stopStreaming = () => {
    streamRecorderRef.current?.stop();
    streamMicRef.current?.getTracks().forEach((t) => t.stop());
    streamWsRef.current?.close();
    setStreamStatus("idle");
  };

  // ─── Day 4: VAD — Voice Activity Detection (no network, detection only) ────
  const startVAD = async () => {
    try {
      setVadStatus("loading");


      const vad = await MicVAD.new({
        baseAssetPath: "/vad/",
        onnxWASMBasePath: "/vad/",
        startOnLoad: false,

        // Use local WASM files from public/vad/ (copied via vite-plugin-static-copy)
        ortConfig: (ort) => {
          ort.env.wasm.numThreads = 1;
          ort.env.wasm.wasmPaths = "/vad/";
        },

        onSpeechStart: () => {

          setIsSpeaking(true);
          setSpeechEvents((prev) => [
            ...prev.slice(-29),
            {
              type: "start",
              time: new Date().toLocaleTimeString(),
            },
          ]);
        },

        onSpeechEnd: (audio) => {
          // audio is a Float32Array of 16kHz samples
          const durationSec = (audio.length / 16000).toFixed(2);

          setIsSpeaking(false);
          setSpeechEvents((prev) => [
            ...prev.slice(-29),
            {
              type: "end",
              time: new Date().toLocaleTimeString(),
              samples: audio.length,
              duration: parseFloat(durationSec),
            },
          ]);
        },
      });

      vadRef.current = vad;
      await vad.start();
      setVadStatus("listening");

    } catch (err) {
      console.error("[Day4] VAD Error:", err);
      setVadStatus("error");
    }
  };

  const stopVAD = async () => {
    if (vadRef.current) {
      await vadRef.current.destroy();
      vadRef.current = null;
    }
    setVadStatus("idle");
    setIsSpeaking(false);

  };

  // ─── Render ────────────────────────────────────────────────────────────────
  const wsBadgeColor = { connecting: "#f59e0b", live: "#10b981", disconnected: "#ef4444" }[wsStatus];
  const micBadgeColor = { idle: "#6b7280", active: "#10b981", error: "#ef4444" }[micStatus];
  const streamBadgeColor = { idle: "#6b7280", streaming: "#10b981", error: "#ef4444" }[streamStatus];
  const vadBadgeColor = { idle: "#6b7280", loading: "#f59e0b", listening: "#10b981", error: "#ef4444" }[vadStatus];
  const vadBadgeText = { idle: "○ Idle", loading: "◌ Loading…", listening: "● LISTENING", error: "✕ Error" }[vadStatus];

  return (
    <div style={styles.page}>
      {/* ── Header ── */}
      <div style={styles.header}>
        <h1 style={styles.title}>TalkSense AI</h1>
        <span style={styles.subtitle}>Conversation Intelligence Platform</span>
      </div>

      {/* ── Top row: Day 1 + Day 2 ── */}
      <div style={styles.grid}>
        {/* Day 1 */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <div style={styles.cardTitle}>
              <span style={styles.dayTag}>Day 1</span>
              <span style={styles.cardName}>WebSocket Transcript</span>
            </div>
            <span style={{ ...styles.badge, background: wsBadgeColor }}>
              {wsStatus === "live" ? "● LIVE" : wsStatus === "connecting" ? "◌ Connecting…" : "✕ Disconnected"}
            </span>
          </div>
          <div style={styles.messageBox}>
            {messages.length === 0 ? (
              <p style={styles.placeholder}>Waiting for messages…</p>
            ) : (
              messages.map((msg, i) => (
                <div key={i} style={{ ...styles.message, animationDelay: `${i * 0.05}s` }}>
                  <span style={styles.msgIndex}>{String(i + 1).padStart(2, "0")}</span>
                  <span style={styles.msgText}>{msg}</span>
                </div>
              ))
            )}
          </div>
          <div style={styles.flowLabel}>FastAPI → WebSocket → React ✓</div>
        </div>

        {/* Day 2 */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <div style={styles.cardTitle}>
              <span style={{ ...styles.dayTag, background: "rgba(99,102,241,0.2)", color: "#a5b4fc" }}>Day 2</span>
              <span style={styles.cardName}>Microphone Capture</span>
            </div>
            <span style={{ ...styles.badge, background: micBadgeColor }}>
              {micStatus === "active" ? "● RECORDING" : micStatus === "error" ? "✕ Error" : "○ Idle"}
            </span>
          </div>
          <div style={styles.micControls}>
            {micStatus !== "active" ? (
              <button id="start-mic-btn" style={styles.btnStart} onClick={startMic}>🎙 Start Microphone</button>
            ) : (
              <button id="stop-mic-btn" style={styles.btnStop} onClick={stopMic}>⏹ Stop Recording</button>
            )}
          </div>
          <div style={styles.chunkBox}>
            {chunks.length === 0 ? (
              <p style={styles.placeholder}>
                {micStatus === "idle" ? "Click Start Microphone to begin…" : "Listening for chunks…"}
              </p>
            ) : (
              chunks.map((c, i) => (
                <div key={i} style={{ ...styles.chunkRow, animationDelay: `${i * 0.03}s` }}>
                  <span style={styles.chunkTime}>{c.time}</span>
                  <span style={styles.chunkLabel}>Chunk Size:</span>
                  <span style={styles.chunkSize}>{c.size.toLocaleString()}</span>
                  <div style={{ ...styles.chunkBar, width: `${Math.min(100, (c.size / 20000) * 100)}%` }} />
                </div>
              ))
            )}
          </div>
          <div style={styles.flowLabel}>Browser → Microphone → Audio Chunks ✓</div>
        </div>
      </div>

      {/* ── Day 3 Panel: full width ── */}
      <div style={{ ...styles.grid, maxWidth: "900px", marginTop: "24px" }}>
        <div style={{ ...styles.card, gridColumn: "1 / -1" }}>
          <div style={styles.cardHeader}>
            <div style={styles.cardTitle}>
              <span style={{ ...styles.dayTag, background: "rgba(245,158,11,0.2)", color: "#fbbf24" }}>Day 3</span>
              <span style={styles.cardName}>Audio → WebSocket → FastAPI</span>
            </div>
            <span style={{ ...styles.badge, background: streamBadgeColor }}>
              {streamStatus === "streaming" ? "● STREAMING" : streamStatus === "error" ? "✕ Error" : "○ Idle"}
            </span>
          </div>

          <div style={styles.micControls}>
            {streamStatus !== "streaming" ? (
              <button id="start-stream-btn" style={{ ...styles.btnStart, background: "linear-gradient(135deg, #f59e0b, #d97706)" }} onClick={startStreaming}>
                📡 Start Audio Stream
              </button>
            ) : (
              <button id="stop-stream-btn" style={styles.btnStop} onClick={stopStreaming}>
                ⏹ Stop Stream
              </button>
            )}
          </div>

          {/* Stats row */}
          <div style={styles.statsRow}>
            <div style={styles.statCard}>
              <span style={styles.statValue}>{sentChunks.length}</span>
              <span style={styles.statLabel}>Chunks Sent</span>
            </div>
            <div style={styles.statCard}>
              <span style={styles.statValue}>{acks}</span>
              <span style={styles.statLabel}>Acks Received</span>
            </div>
            <div style={styles.statCard}>
              <span style={styles.statValue}>
                {sentChunks.length > 0
                  ? `${(sentChunks.reduce((sum, c) => sum + c.size, 0) / 1024).toFixed(1)} KB`
                  : "0 KB"}
              </span>
              <span style={styles.statLabel}>Total Sent</span>
            </div>
          </div>

          {/* Chunk log */}
          <div style={{ ...styles.chunkBox, maxHeight: "200px" }}>
            {sentChunks.length === 0 ? (
              <p style={styles.placeholder}>Click Start Audio Stream to begin…</p>
            ) : (
              sentChunks.map((c, i) => (
                <div key={i} style={{ ...styles.chunkRow, animationDelay: `${i * 0.03}s` }}>
                  <span style={styles.chunkTime}>{c.time}</span>
                  <span style={styles.chunkLabel}>Sent:</span>
                  <span style={{ ...styles.chunkSize, color: "#fbbf24" }}>{c.size.toLocaleString()} bytes</span>
                  <div style={{ ...styles.chunkBar, width: `${Math.min(100, (c.size / 20000) * 100)}%`, background: "linear-gradient(90deg, #f59e0b, #fbbf24)" }} />
                </div>
              ))
            )}
          </div>

          <div style={styles.flowLabel}>Browser 🎙 → WebSocket 📡 → FastAPI 🖥 (check backend terminal for logs) ✓</div>
        </div>
      </div>

      {/* ── Day 4 Panel: VAD — full width ── */}
      <div style={{ ...styles.grid, maxWidth: "900px", marginTop: "24px" }}>
        <div style={{ ...styles.card, gridColumn: "1 / -1", border: isSpeaking ? "1px solid rgba(16,185,129,0.5)" : "1px solid rgba(255,255,255,0.1)", transition: "border-color 0.3s ease" }}>
          <div style={styles.cardHeader}>
            <div style={styles.cardTitle}>
              <span style={{ ...styles.dayTag, background: "rgba(236,72,153,0.2)", color: "#f9a8d4" }}>Day 4</span>
              <span style={styles.cardName}>Voice Activity Detection (VAD)</span>
            </div>
            <span style={{ ...styles.badge, background: vadBadgeColor }}>
              {vadBadgeText}
            </span>
          </div>

          <div style={styles.micControls}>
            {vadStatus !== "listening" ? (
              <button
                id="start-vad-btn"
                style={{ ...styles.btnStart, background: "linear-gradient(135deg, #ec4899, #be185d)" }}
                onClick={startVAD}
                disabled={vadStatus === "loading"}
              >
                {vadStatus === "loading" ? "⏳ Loading VAD Model…" : "🧠 Start VAD"}
              </button>
            ) : (
              <button id="stop-vad-btn" style={styles.btnStop} onClick={stopVAD}>
                ⏹ Stop VAD
              </button>
            )}
          </div>

          {/* Speaking indicator */}
          {vadStatus === "listening" && (
            <div style={styles.speakingIndicator}>
              <div style={{
                ...styles.speakingDot,
                background: isSpeaking ? "#10b981" : "#6b7280",
                boxShadow: isSpeaking ? "0 0 12px rgba(16,185,129,0.6)" : "none",
                animation: isSpeaking ? "pulseSubtle 0.8s ease-in-out infinite" : "none",
              }} />
              <span style={{
                ...styles.speakingText,
                color: isSpeaking ? "#6ee7b7" : "rgba(255,255,255,0.4)",
              }}>
                {isSpeaking ? "🗣 Speech Detected" : "🤫 Silence — Waiting for speech…"}
              </span>
            </div>
          )}

          {/* Stats row */}
          <div style={styles.statsRow}>
            <div style={styles.statCard}>
              <span style={{ ...styles.statValue, color: "#f9a8d4" }}>
                {speechEvents.filter((e) => e.type === "end").length}
              </span>
              <span style={styles.statLabel}>Speech Segments</span>
            </div>
            <div style={styles.statCard}>
              <span style={{ ...styles.statValue, color: "#f9a8d4" }}>
                {speechEvents.filter((e) => e.type === "end").reduce((sum, e) => sum + (e.duration || 0), 0).toFixed(1)}s
              </span>
              <span style={styles.statLabel}>Total Speech</span>
            </div>
            <div style={styles.statCard}>
              <span style={{ ...styles.statValue, color: "#f9a8d4" }}>
                {speechEvents.filter((e) => e.type === "start").length - speechEvents.filter((e) => e.type === "end").length > 0 ? "Yes" : "No"}
              </span>
              <span style={styles.statLabel}>Speaking Now</span>
            </div>
          </div>

          {/* Speech events log */}
          <div style={{ ...styles.chunkBox, maxHeight: "220px" }}>
            {speechEvents.length === 0 ? (
              <p style={styles.placeholder}>
                {vadStatus === "idle" ? "Click Start VAD to begin…" : vadStatus === "loading" ? "Loading Silero VAD model…" : "Listening — speak to trigger events…"}
              </p>
            ) : (
              speechEvents.map((e, i) => (
                <div key={i} style={{ ...styles.chunkRow, animationDelay: `${i * 0.03}s` }}>
                  <span style={styles.chunkTime}>{e.time}</span>
                  <span style={{
                    ...styles.chunkLabel,
                    color: e.type === "start" ? "#6ee7b7" : "#f9a8d4",
                    fontWeight: 600,
                  }}>
                    {e.type === "start" ? "▶ START" : "■ END"}
                  </span>
                  <span style={{ ...styles.chunkSize, color: "#f9a8d4" }}>
                    {e.type === "end" ? `${e.duration}s (${e.samples?.toLocaleString()} samples)` : ""}
                  </span>
                </div>
              ))
            )}
          </div>

          <div style={styles.flowLabel}>Mic 🎙 → Silero VAD 🧠 → Speech? YES/NO ✓</div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
    fontFamily: "'Inter', sans-serif",
    padding: "40px 24px",
    boxSizing: "border-box",
  },
  header: {
    textAlign: "center",
    marginBottom: "40px",
  },
  title: {
    fontSize: "2.6rem",
    fontWeight: 800,
    background: "linear-gradient(90deg, #a78bfa, #60a5fa)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    margin: 0,
  },
  subtitle: {
    display: "block",
    marginTop: "8px",
    fontSize: "0.9rem",
    color: "rgba(255,255,255,0.4)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
    gap: "24px",
    maxWidth: "900px",
    margin: "0 auto",
  },
  card: {
    background: "rgba(255,255,255,0.05)",
    backdropFilter: "blur(14px)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: "20px",
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  cardTitle: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  dayTag: {
    fontSize: "0.7rem",
    fontWeight: 700,
    background: "rgba(16,185,129,0.2)",
    color: "#6ee7b7",
    padding: "3px 8px",
    borderRadius: "6px",
    letterSpacing: "0.05em",
  },
  cardName: {
    fontSize: "1rem",
    fontWeight: 600,
    color: "#e2e8f0",
  },
  badge: {
    fontSize: "0.7rem",
    fontWeight: 700,
    color: "#fff",
    padding: "4px 10px",
    borderRadius: "999px",
    letterSpacing: "0.06em",
  },
  messageBox: {
    background: "rgba(0,0,0,0.2)",
    borderRadius: "12px",
    padding: "16px",
    minHeight: "140px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  placeholder: {
    color: "rgba(255,255,255,0.25)",
    fontStyle: "italic",
    fontSize: "0.85rem",
    margin: "auto",
    textAlign: "center",
  },
  message: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    animation: "fadeSlideIn 0.4s ease both",
  },
  msgIndex: {
    fontSize: "0.65rem",
    color: "rgba(167,139,250,0.6)",
    fontWeight: 600,
    minWidth: "22px",
  },
  msgText: {
    fontSize: "1.1rem",
    color: "#e2e8f0",
    fontWeight: 500,
  },
  micControls: {
    display: "flex",
    justifyContent: "center",
  },
  btnStart: {
    background: "linear-gradient(135deg, #7c3aed, #4f46e5)",
    color: "#fff",
    border: "none",
    borderRadius: "12px",
    padding: "12px 28px",
    fontSize: "0.95rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "opacity 0.2s, transform 0.2s",
    letterSpacing: "0.03em",
  },
  btnStop: {
    background: "linear-gradient(135deg, #dc2626, #b91c1c)",
    color: "#fff",
    border: "none",
    borderRadius: "12px",
    padding: "12px 28px",
    fontSize: "0.95rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "opacity 0.2s, transform 0.2s",
    letterSpacing: "0.03em",
  },
  chunkBox: {
    background: "rgba(0,0,0,0.2)",
    borderRadius: "12px",
    padding: "14px 16px",
    minHeight: "140px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    overflowY: "auto",
    maxHeight: "220px",
  },
  chunkRow: {
    display: "grid",
    gridTemplateColumns: "80px 90px 1fr",
    alignItems: "center",
    gap: "8px",
    animation: "fadeSlideIn 0.3s ease both",
    position: "relative",
  },
  chunkTime: {
    fontSize: "0.7rem",
    color: "rgba(165,243,252,0.7)",
    fontVariantNumeric: "tabular-nums",
  },
  chunkLabel: {
    fontSize: "0.72rem",
    color: "rgba(255,255,255,0.4)",
  },
  chunkSize: {
    fontSize: "0.85rem",
    fontWeight: 700,
    color: "#a5b4fc",
    fontVariantNumeric: "tabular-nums",
  },
  chunkBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    height: "2px",
    background: "linear-gradient(90deg, #7c3aed, #60a5fa)",
    borderRadius: "1px",
    transition: "width 0.3s ease",
  },
  flowLabel: {
    fontSize: "0.7rem",
    color: "rgba(255,255,255,0.25)",
    textAlign: "center",
    letterSpacing: "0.05em",
    fontFamily: "monospace",
  },
  statsRow: {
    display: "flex",
    gap: "16px",
    justifyContent: "center",
  },
  statCard: {
    background: "rgba(0,0,0,0.25)",
    borderRadius: "12px",
    padding: "12px 20px",
    textAlign: "center",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    minWidth: "100px",
  },
  statValue: {
    fontSize: "1.3rem",
    fontWeight: 700,
    color: "#fbbf24",
    fontVariantNumeric: "tabular-nums",
  },
  statLabel: {
    fontSize: "0.65rem",
    color: "rgba(255,255,255,0.4)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  speakingIndicator: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    padding: "12px 0",
  },
  speakingDot: {
    width: "12px",
    height: "12px",
    borderRadius: "50%",
    transition: "all 0.3s ease",
  },
  speakingText: {
    fontSize: "0.9rem",
    fontWeight: 600,
    transition: "color 0.3s ease",
  },
};
