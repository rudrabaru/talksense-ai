import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSessionWebSocket } from "../hooks/useSessionWebSocket";
import { useAudioCapture } from "../hooks/useAudioCapture";
import { createSession, getSession } from "../services/api";
import SessionStatusBar from "../components/dashboard/SessionStatusBar";
import TranscriptPanel from "../components/dashboard/TranscriptPanel";
import MetricsPanel from "../components/dashboard/MetricsPanel";
import AlertsPanel from "../components/dashboard/AlertsPanel";

// --- Constants ---------------------------------------------------------------
const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

export default function DashboardPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [initError, setInitError] = useState(null);
  const [validatedSessionId, setValidatedSessionId] = useState(null);

  // --- Audio WebSocket refs --------------------------------------------------
  // The audio WebSocket (/ws/audio/{session_id}) is managed locally because it
  // is an INBOUND stream (browser → server) — conceptually different from the
  // four OUTBOUND subscription channels managed by useSessionWebSocket.
  const audioWsRef = useRef(null);
  const [audioStatus, setAudioStatus] = useState("idle"); // idle | connecting | streaming | error

  // --- Hooks -----------------------------------------------------------------
  const {
    start: startCapture,
    stop: stopCapture,
    cleanup: cleanupCapture,
    isCapturing,
    permissionError,
  } = useAudioCapture();

  const {
    transcript,
    metrics,
    alerts,
    sessionStatus,
    connectionState,
    error,
    lastSyncAt,
    reconnect,
  } = useSessionWebSocket(validatedSessionId);

  // --- Session validation and creation ---------------------------------------
  useEffect(() => {
    const initializeSession = async () => {
      try {
        if (!sessionId) {
          // No session ID in URL: create a new one
          const data = await createSession("meeting");
          if (data && data.session_id) {
            navigate(`/dashboard/${data.session_id}`, { replace: true });
          } else {
            setInitError("Failed to initialize session: No session_id returned.");
          }
        } else {
          // Session ID in URL: validate it exists on the backend
          try {
            await getSession(sessionId);
            // If it succeeds, mark it as validated so WebSockets can connect
            setValidatedSessionId(sessionId);
          } catch (err) {
            console.warn(`[DashboardPage] Session ${sessionId} invalid/expired. Creating new session.`, err);
            // Session is stale (e.g. backend restarted). Auto-create a new one.
            const data = await createSession("meeting");
            if (data && data.session_id) {
              navigate(`/dashboard/${data.session_id}`, { replace: true });
            } else {
              setInitError("Failed to initialize session: No session_id returned.");
            }
          }
        }
      } catch (err) {
        setInitError(err.message || "Failed to initialize live session.");
      }
    };

    initializeSession();
  }, [sessionId, navigate]);

  // --- Cleanup audio capture on unmount --------------------------------------
  useEffect(() => {
    return () => {
      cleanupCapture();
    };
  }, [cleanupCapture]);

  // --- Audio WebSocket helpers -----------------------------------------------

  /**
   * Opens the audio WebSocket and starts microphone capture.
   *
   * Flow:
   *   1. Open /ws/audio/{session_id}
   *   2. On ws.onopen → call useAudioCapture.start({ onAudioChunk })
   *   3. onAudioChunk sends each 250ms PCM ArrayBuffer via ws.send()
   *   4. Guards against sending on a non-OPEN socket
   */
  const startMicrophone = useCallback(() => {
    if (!validatedSessionId) return;
    if (audioWsRef.current && audioWsRef.current.readyState <= WebSocket.OPEN) {
      console.warn("[DashboardPage] Audio WebSocket already open or connecting.");
      return;
    }

    setAudioStatus("connecting");
    const ws = new WebSocket(`${WS_BASE_URL}/ws/audio/${validatedSessionId}`);
    audioWsRef.current = ws;

    ws.onopen = () => {
      console.log("[DashboardPage] Audio WebSocket connected.");
      setAudioStatus("streaming");

      startCapture({
        onAudioChunk: (buffer) => {
          // Guard: only send if the socket is still open.
          if (audioWsRef.current && audioWsRef.current.readyState === WebSocket.OPEN) {
            audioWsRef.current.send(buffer);
          }
        },
      });
    };

    ws.onclose = (event) => {
      console.log(`[DashboardPage] Audio WebSocket closed (code: ${event.code}).`);
      audioWsRef.current = null;
      // If the mic is still capturing when the socket closes, stop it.
      // This prevents PCM chunks from being generated with nowhere to go.
      stopCapture();
      setAudioStatus("idle");
    };

    ws.onerror = (event) => {
      console.error("[DashboardPage] Audio WebSocket error:", event);
      setAudioStatus("error");
    };
  }, [validatedSessionId, startCapture, stopCapture]);

  /**
   * Stops microphone capture and closes the audio WebSocket.
   * Sends the "end" text command to signal session completion to the backend.
   */
  const stopMicrophone = useCallback(() => {
    // 1. Stop PCM capture first to prevent chunks being sent on a closing socket.
    stopCapture();

    // 2. Send the "end" command and close the WebSocket.
    const ws = audioWsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send("end");
      } catch (err) {
        console.warn("[DashboardPage] Failed to send 'end' command:", err);
      }
      ws.close(1000, "User stopped recording");
    }
    audioWsRef.current = null;
    setAudioStatus("idle");
  }, [stopCapture]);

  // --- Reconnect handler -----------------------------------------------------
  const handleReconnect = () => {
    if (typeof reconnect === "function") {
      try {
        reconnect();
      } catch (err) {
        console.error("Failed to trigger reconnect:", err);
      }
    }
  };

  // --- Render: Init error ----------------------------------------------------
  if (initError) {
    return (
      <main style={{ padding: "16px", fontFamily: "sans-serif" }} role="alert">
        <div style={{ border: "2px solid #ef4444", padding: "16px", background: "#fef2f2", textAlign: "center", borderRadius: "8px" }}>
          <h3 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>Session Initialization Failed</h3>
          <p style={{ margin: "0", color: "#7f1d1d" }}>{initError}</p>
        </div>
      </main>
    );
  }

  // --- Render: Loading skeleton ----------------------------------------------
  if (connectionState === "idle" || connectionState === "connecting") {
    return (
      <main
        className="dashboard-loading-skeleton"
        style={{ padding: "16px", fontFamily: "sans-serif" }}
        aria-busy="true"
        aria-label="Loading session dashboard"
      >
        <div style={{ height: "48px", background: "#e2e8f0", borderRadius: "4px", marginBottom: "16px" }} />
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
          <div style={{ height: "400px", background: "#e2e8f0", borderRadius: "4px" }} />
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ height: "192px", background: "#e2e8f0", borderRadius: "4px" }} />
            <div style={{ height: "192px", background: "#e2e8f0", borderRadius: "4px" }} />
          </div>
        </div>
      </main>
    );
  }

  // --- Render: Main dashboard ------------------------------------------------
  return (
    <main style={{ padding: "16px" }}>
      {/* --- Connection banners --- */}
      {connectionState === "reconnecting" && (
        <div
          key="banner-reconnecting"
          role="status"
          aria-live="polite"
          style={{ background: "#f59e0b", color: "white", padding: "8px", textAlign: "center", borderRadius: "4px", marginBottom: "12px" }}
        >
          Reconnecting to session...
        </div>
      )}

      {connectionState === "failed" && (
        <div
          key="banner-failed"
          role="alert"
          style={{ border: "2px solid #ef4444", padding: "16px", margin: "16px 0", background: "#fef2f2", textAlign: "center", borderRadius: "8px" }}
        >
          <h3 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>Connection Failed</h3>
          <p style={{ margin: "0 0 12px 0", color: "#7f1d1d" }}>
            {error || "Unable to connect to the session WebSocket."}
          </p>
          <button
            onClick={handleReconnect}
            style={{ padding: "8px 16px", cursor: "pointer", background: "#ef4444", color: "white", border: "none", borderRadius: "4px", fontWeight: "bold" }}
            aria-label="Retry connecting to the session"
          >
            Reconnect
          </button>
        </div>
      )}

      {/* --- Permission error banner --- */}
      {permissionError && (
        <div
          role="alert"
          style={{ border: "2px solid #f59e0b", padding: "12px", margin: "0 0 12px 0", background: "#fffbeb", textAlign: "center", borderRadius: "8px" }}
        >
          <p style={{ margin: "0", color: "#92400e" }}>{permissionError}</p>
        </div>
      )}

      {/* --- Status bar --- */}
      <SessionStatusBar
        sessionStatus={sessionStatus || "unknown"}
        connectionState={connectionState || "disconnected"}
        lastSyncAt={lastSyncAt}
      />

      {/* --- Microphone controls --- */}
      <div style={{ display: "flex", justifyContent: "center", gap: "12px", margin: "16px 0" }}>
        {!isCapturing ? (
          <button
            id="start-mic-btn"
            onClick={startMicrophone}
            disabled={audioStatus === "connecting" || !validatedSessionId}
            style={{
              padding: "12px 28px",
              fontSize: "0.95rem",
              fontWeight: 600,
              color: "#fff",
              background: audioStatus === "connecting"
                ? "#94a3b8"
                : "linear-gradient(135deg, #7c3aed, #4f46e5)",
              border: "none",
              borderRadius: "12px",
              cursor: audioStatus === "connecting" ? "wait" : "pointer",
              letterSpacing: "0.03em",
            }}
            aria-label="Start microphone capture"
          >
            {audioStatus === "connecting" ? "⏳ Connecting…" : "🎙 Start Microphone"}
          </button>
        ) : (
          <button
            id="stop-mic-btn"
            onClick={stopMicrophone}
            style={{
              padding: "12px 28px",
              fontSize: "0.95rem",
              fontWeight: 600,
              color: "#fff",
              background: "linear-gradient(135deg, #dc2626, #b91c1c)",
              border: "none",
              borderRadius: "12px",
              cursor: "pointer",
              letterSpacing: "0.03em",
            }}
            aria-label="Stop microphone capture"
          >
            ⏹ Stop Microphone
          </button>
        )}
      </div>

      {/* --- Dashboard panels --- */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px", marginTop: "16px" }}>
        <div>
          <TranscriptPanel transcript={transcript || []} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <MetricsPanel metrics={metrics || null} />
          <AlertsPanel alerts={alerts || []} />
        </div>
      </div>
    </main>
  );
}
