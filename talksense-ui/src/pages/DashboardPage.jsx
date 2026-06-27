import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSessionWebSocket } from "../hooks/useSessionWebSocket";
import { useAudioCapture } from "../hooks/useAudioCapture";
import { createSession, getSession, listClients, getClientBriefing, createClient } from "../services/api";
import ClientBriefingCard from "../components/ClientBriefingCard";
import SessionStatusBar from "../components/dashboard/SessionStatusBar";
import TranscriptPanel from "../components/dashboard/TranscriptPanel";
import MetricsPanel from "../components/dashboard/MetricsPanel";
import AlertsPanel from "../components/dashboard/AlertsPanel";
import CoachingPanel from "../components/dashboard/CoachingPanel";
import logoImage from "../assets/logo/logo.png";

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

  // --- Client memory / Launcher states ---------------------------------------
  const [launcherMode, setLauncherMode] = useState("sales"); // "meeting" | "sales"
  const [clients, setClients] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [clientBriefing, setClientBriefing] = useState(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [isCreatingClient, setIsCreatingClient] = useState(false);
  const [newClientName, setNewClientName] = useState("");
  const [newClientIndustry, setNewClientIndustry] = useState("");
  const [clientCreateError, setClientCreateError] = useState(null);
  const [launchLoading, setLaunchLoading] = useState(false);

  // Fetch clients on mount if no session present
  useEffect(() => {
    if (!sessionId) {
      const fetchClients = async () => {
        try {
          const data = await listClients();
          setClients(data);
          if (data.length > 0) {
            setSelectedClientId(data[0].id);
          }
        } catch (err) {
          console.error("Failed to load clients list:", err);
        }
      };
      fetchClients();
    }
  }, [sessionId]);

  // Fetch briefing card details when client changes
  useEffect(() => {
    if (!sessionId && selectedClientId && launcherMode === "sales") {
      const fetchBriefing = async () => {
        setBriefingLoading(true);
        try {
          const data = await getClientBriefing(selectedClientId);
          setClientBriefing(data);
        } catch (err) {
          console.error("Failed to load client briefing:", err);
        } finally {
          setBriefingLoading(false);
        }
      };
      fetchBriefing();
    } else {
      setClientBriefing(null);
    }
  }, [selectedClientId, launcherMode, sessionId]);

  // Create a new client profile
  const handleCreateClient = async (e) => {
    e.preventDefault();
    if (!newClientName.trim()) {
      setClientCreateError("Client name is required");
      return;
    }
    try {
      setClientCreateError(null);
      const newClient = await createClient({
        name: newClientName.trim(),
        industry: newClientIndustry.trim() || null
      });
      setClients(prev => [...prev, newClient]);
      setSelectedClientId(newClient.id);
      setNewClientName("");
      setNewClientIndustry("");
      setIsCreatingClient(false);
    } catch (err) {
      setClientCreateError("Failed to create client.");
    }
  };

  // Launch live session
  const handleLaunchSession = async () => {
    setLaunchLoading(true);
    setInitError(null);
    try {
      const data = await createSession(
        launcherMode, 
        launcherMode === "sales" && selectedClientId ? selectedClientId : null
      );
      if (data && data.session_id) {
        navigate(`/dashboard/${data.session_id}`);
      } else {
        setInitError("Failed to start session: No session_id returned.");
      }
    } catch (err) {
      setInitError(err.message || "Failed to launch session.");
    } finally {
      setLaunchLoading(false);
    }
  };

  // --- Session validation -----------------------------------------------------
  useEffect(() => {
    const initializeSession = async () => {
      if (!sessionId) return;
      try {
        await getSession(sessionId);
        setValidatedSessionId(sessionId);
      } catch (err) {
        console.warn(`[DashboardPage] Session ${sessionId} invalid/expired.`, err);
        setInitError("Session not found or invalid. Please return to home or launch a new session.");
      }
    };

    initializeSession();
  }, [sessionId]);


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

    ws.onopen = async () => {
      console.log("[DashboardPage] Audio WebSocket connected.");
      setAudioStatus("streaming");

      try {
        await startCapture({
          onAudioChunk: (buffer) => {
            // Guard: only send if the socket is still open.
            if (audioWsRef.current && audioWsRef.current.readyState === WebSocket.OPEN) {
              audioWsRef.current.send(buffer);
            }
          },
        });
      } catch (err) {
        console.error("[DashboardPage] startCapture failed:", err);
        setAudioStatus("error");
      }
    };

    ws.onclose = (event) => {
      console.log(`[DashboardPage] Audio WebSocket closed (code: ${event.code}).`);
      audioWsRef.current = null;
      stopCapture();
      setAudioStatus("idle");

      // 4009 = backend rejected because session is terminal.
      // Navigate to /dashboard so a fresh session is auto-created.
      if (event.code === 4009) {
        console.warn("[DashboardPage] Session ended on backend — navigating to fresh session.");
        navigate("/dashboard", { replace: true });
      }
    };

    ws.onerror = (event) => {
      console.error("[DashboardPage] Audio WebSocket error:", event);
      setAudioStatus("error");
    };
  }, [validatedSessionId, startCapture, stopCapture, navigate]);

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

  // --- Render: Launcher dashboard when no sessionId is active ────────────────
  if (!sessionId) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Navbar */}
        <nav className="border-b border-gray-200 bg-white sticky top-0 z-50 shadow-sm">
          <div className="mx-auto px-6 lg:px-12 xl:px-16 h-16 flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-3 hover:opacity-85 transition-all"
            >
              <div className="relative w-9 h-9">
                <img src={logoImage} alt="TalkSense AI Logo" className="w-full h-full object-contain" />
              </div>
              <span className="font-bold text-xl tracking-tight">
                <span style={{ color: '#4F46E5' }}>TalkSense</span>
                <span style={{ color: '#14B8A6' }}> AI</span>
              </span>
            </button>
            <div className="flex gap-6 items-center text-sm font-medium">
              <button
                onClick={() => navigate('/')}
                className="text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Home
              </button>
              <button
                onClick={() => navigate('/upload')}
                className="text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Analyze
              </button>
              <button
                onClick={() => navigate('/sessions')}
                className="text-gray-500 hover:text-indigo-600 transition-colors"
              >
                History
              </button>
            </div>
          </div>
        </nav>

        <main className="max-w-4xl mx-auto px-6 py-12 lg:py-16 w-full flex-1 flex flex-col justify-center">
          <div className="bg-white rounded-3xl border border-gray-200 shadow-xl p-8 lg:p-10 animate-fade-in">
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight text-center mb-2">
              Launch Live Intelligence Session
            </h1>
            <p className="text-gray-500 text-center mb-8">
              Configure your workspace and review client memory before starting the live session.
            </p>

            <div className="grid md:grid-cols-2 gap-8 mb-8 items-start">
              {/* Left Column: Config */}
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-3">
                    Conversation Mode
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => setLauncherMode("meeting")}
                      className={`py-3 px-4 rounded-xl border-2 text-center font-semibold transition-smooth ${
                        launcherMode === "meeting"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300 text-gray-700"
                      }`}
                    >
                      Meeting
                    </button>
                    <button
                      onClick={() => setLauncherMode("sales")}
                      className={`py-3 px-4 rounded-xl border-2 text-center font-semibold transition-smooth ${
                        launcherMode === "sales"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300 text-gray-700"
                      }`}
                    >
                      Sales Call
                    </button>
                  </div>
                </div>

                {launcherMode === "sales" && (
                  <div className="bg-gray-50 border border-gray-150 rounded-2xl p-4 space-y-4">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-semibold text-gray-900">
                        Select Client
                      </label>
                      <button
                        onClick={() => setIsCreatingClient(!isCreatingClient)}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
                      >
                        {isCreatingClient ? "← Choose Client" : "+ Create Client"}
                      </button>
                    </div>

                    {isCreatingClient ? (
                      <form onSubmit={handleCreateClient} className="space-y-3 bg-white p-4 rounded-xl border border-gray-200 shadow-sm animate-scale-in">
                        <div>
                          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Company / Name</label>
                          <input
                            type="text"
                            required
                            value={newClientName}
                            onChange={e => setNewClientName(e.target.value)}
                            placeholder="e.g. Acme Corporation"
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">Industry (Optional)</label>
                          <input
                            type="text"
                            value={newClientIndustry}
                            onChange={e => setNewClientIndustry(e.target.value)}
                            placeholder="e.g. Software"
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                        {clientCreateError && (
                          <p className="text-[10px] text-rose-600 mt-1">⚠️ {clientCreateError}</p>
                        )}
                        <button
                          type="submit"
                          className="w-full bg-indigo-600 text-white font-semibold py-2 rounded-lg text-xs hover:bg-indigo-700 transition-colors shadow-sm active:scale-95"
                        >
                          Save New Client
                        </button>
                      </form>
                    ) : (
                      <select
                        value={selectedClientId}
                        onChange={(e) => setSelectedClientId(e.target.value)}
                        className="w-full bg-white border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium text-gray-700"
                      >
                        <option value="" disabled>Select client...</option>
                        {clients.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} {c.industry ? `(${c.industry})` : ""}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}
              </div>

              {/* Right Column: Briefing Card */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-3">
                  Client Briefing & Memory
                </label>
                {launcherMode === "sales" ? (
                  selectedClientId ? (
                    <ClientBriefingCard client={clientBriefing} loading={briefingLoading} />
                  ) : (
                    <div className="border-2 border-dashed border-gray-200 rounded-2xl p-8 text-center text-gray-400">
                      Select a client to load relationship memory profile.
                    </div>
                  )
                ) : (
                  <div className="bg-slate-50 border border-slate-150 rounded-2xl p-6 text-center text-slate-500">
                    <span className="block font-semibold mb-1 text-gray-800">Meeting Mode selected</span>
                    Internal team meeting mode does not use client relationship briefing memory.
                  </div>
                )}
              </div>
            </div>

            {/* Launch CTA */}
            <div className="border-t border-gray-150 pt-8 mt-6">
              <button
                onClick={handleLaunchSession}
                disabled={launchLoading || (launcherMode === "sales" && !selectedClientId)}
                className="w-full bg-indigo-600 text-white font-bold py-4 rounded-2xl shadow-lg hover:bg-indigo-700 hover:shadow-xl transition-smooth disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center active:scale-95"
              >
                {launchLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creating session...
                  </>
                ) : (
                  "🚀 Launch Live Session"
                )}
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // --- Render: Loading skeleton ----------------------------------------------

  const isTerminal = ["completed", "failed", "interrupted", "expired"].includes(sessionStatus);
  if ((connectionState === "idle" || connectionState === "connecting") && !isTerminal) {
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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-50 shadow-sm">
        <div className="mx-auto px-6 lg:px-12 xl:px-16 h-16 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-3 hover:opacity-85 transition-all"
          >
            <div className="relative w-9 h-9">
              <img src={logoImage} alt="TalkSense AI Logo" className="w-full h-full object-contain" />
            </div>
            <span className="font-bold text-xl tracking-tight">
              <span style={{ color: '#4F46E5' }}>TalkSense</span>
              <span style={{ color: '#14B8A6' }}> AI</span>
            </span>
          </button>
          <div className="flex gap-6 items-center text-sm font-medium">
            <button
              onClick={() => navigate('/')}
              className="text-gray-500 hover:text-indigo-600 transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => navigate('/upload')}
              className="text-gray-500 hover:text-indigo-600 transition-colors"
            >
              Analyze
            </button>
            <button
              onClick={() => navigate('/sessions')}
              className="text-gray-500 hover:text-indigo-600 transition-colors"
            >
              History
            </button>
          </div>
        </div>
      </nav>

      <main style={{ padding: "24px 16px", flex: 1 }} className="max-w-7xl mx-auto w-full">
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
          <MetricsPanel 
            metrics={metrics || null} 
            sessionStatus={sessionStatus} 
            lastSyncAt={lastSyncAt} 
          />
          <CoachingPanel tips={metrics?.coachingTips || []} />
          <AlertsPanel alerts={alerts || []} />
        </div>
      </div>
    </main>
    </div>
  );
}
