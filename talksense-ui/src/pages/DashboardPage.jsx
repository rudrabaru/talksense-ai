import React, { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSessionWebSocket } from "../hooks/useSessionWebSocket";
import { useAudioCapture } from "../hooks/useAudioCapture";
import {
  createSession,
  getSession,
  listClients,
  getClientBriefing,
  createClient,
} from "../services/api";
import ClientBriefingCard from "../components/ClientBriefingCard";
import SessionStatusBar from "../components/dashboard/SessionStatusBar";
import TranscriptPanel from "../components/dashboard/TranscriptPanel";
import ConversationSidebar from "../components/dashboard/ConversationSidebar";
import logoImage from "../assets/logo/logo.png";
// --- Constants ---------------------------------------------------------------
const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
const REST_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
  const hasExplicitlyEnded = useRef(false);
  const [audioStatus, setAudioStatus] = useState("idle"); // idle | connecting | streaming | error
  const [isEnding, setIsEnding] = useState(false);

  // --- Hooks -----------------------------------------------------------------
  const {
    start: startCapture,
    stop: stopCapture,
    cleanup: cleanupCapture,
    isCapturing,
    permissionError,
    availableSources,
    selectedSourceType,
    setSourceType
  } = useAudioCapture();

  const {
    transcript,
    metrics,
    alerts,
    sessionStatus,
    connectionState,
    error,
    lastSyncAt,
    audioUrl,
    reconnect,
  } = useSessionWebSocket(validatedSessionId);

  // --- Client memory / Launcher states ---------------------------------------
  const [launcherMode, setLauncherMode] = useState("meeting"); // "meeting" | "sales" | "interview"
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
      // eslint-disable-next-line
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
        industry: newClientIndustry.trim() || null,
      });
      setClients((prev) => [...prev, newClient]);
      setSelectedClientId(newClient.id);
      setNewClientName("");
      setNewClientIndustry("");
      setIsCreatingClient(false);
    } catch (err) {
      console.error("[DashboardPage] Failed to create client:", err);
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
        launcherMode === "sales" && selectedClientId ? selectedClientId : null,
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
  const [activeSessionMode, setActiveSessionMode] = useState(null);

  useEffect(() => {
    const initializeSession = async () => {
      if (!sessionId) return;
      try {
        const sessionData = await getSession(sessionId);
        setActiveSessionMode(sessionData?.mode || null);
        setValidatedSessionId(sessionId);
      } catch (err) {
        console.warn(
          `[DashboardPage] Session ${sessionId} invalid/expired.`,
          err,
        );
        setInitError(
          "Session not found or invalid. Please return to home or launch a new session.",
        );
      }
    };

    initializeSession();
  }, [sessionId]);

  // --- Watch session status to reset isEnding ---------------------------------
  useEffect(() => {
    if (["completed", "failed", "interrupted", "expired"].includes(sessionStatus)) {
      setIsEnding(false);
    }
  }, [sessionStatus]);

  // --- Cleanup audio capture on unmount --------------------------------------
  useEffect(() => {
    return () => {
      // Send "end" and let the backend close the socket to properly complete the session
      if (
        !hasExplicitlyEnded.current &&
        audioWsRef.current &&
        audioWsRef.current.readyState === WebSocket.OPEN
      ) {
        try {
          audioWsRef.current.send("end");
        } catch (e) {
          console.warn("[DashboardPage] Failed to send 'end' on unmount", e);
        }
      } 
      
      // We explicitly DO NOT call audioWsRef.current.close() here if it's OPEN.
      // The backend breaks its receive loop when it reads "end" and closes the TCP connection cleanly.
      // If the socket was CONNECTING, we must close it to abort the connection attempt.
      if (audioWsRef.current && audioWsRef.current.readyState === WebSocket.CONNECTING) {
         audioWsRef.current.close(1000, "Component unmounted while connecting");
      }
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

    // If we ALREADY have an open WebSocket, we just need to restart capture!
    if (
      audioWsRef.current &&
      audioWsRef.current.readyState === WebSocket.OPEN
    ) {
      console.log(
        "[DashboardPage] Audio WebSocket already open. Resuming capture.",
      );
      setAudioStatus("streaming");
      try {
        audioWsRef.current.send("resume");
      } catch (err) {
        console.warn("[DashboardPage] Failed to send 'resume' control message:", err);
      }
      try {
        startCapture({
          onAudioChunk: (buffer) => {
            if (
              audioWsRef.current &&
              audioWsRef.current.readyState === WebSocket.OPEN
            ) {
              audioWsRef.current.send(buffer);
            }
          },
        });
      } catch (err) {
        console.error("[DashboardPage] startCapture failed:", err);
        setAudioStatus("error");
      }
      return;
    }

    if (
      audioWsRef.current &&
      audioWsRef.current.readyState === WebSocket.CONNECTING
    ) {
      console.warn("[DashboardPage] Audio WebSocket is connecting.");
      return;
    }

    setAudioStatus("connecting");
    const wsToken = localStorage.getItem(`ws_token_${validatedSessionId}`);
    const ws = new WebSocket(`${WS_BASE_URL}/ws/audio/${validatedSessionId}?token=${wsToken || ''}`);
    audioWsRef.current = ws;

    ws.onopen = async () => {
      console.log("[DashboardPage] Audio WebSocket connected.");
      setAudioStatus("streaming");

      try {
        await startCapture({
          onAudioChunk: (buffer) => {
            // Guard: only send if the socket is still open.
            if (
              audioWsRef.current &&
              audioWsRef.current.readyState === WebSocket.OPEN
            ) {
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
      console.log(
        `[DashboardPage] Audio WebSocket closed (code: ${event.code}).`,
      );
      audioWsRef.current = null;
      stopCapture();
      setAudioStatus("idle");
    };

    ws.onerror = (event) => {
      console.error("[DashboardPage] Audio WebSocket error:", event);
      setAudioStatus("error");
    };
  }, [validatedSessionId, startCapture, stopCapture, navigate]);

  /**
   * Stops microphone capture but keeps the audio WebSocket open.
   * This allows the user to restart recording in the same session.
   */
  const stopMicrophone = useCallback(() => {
    // 1. Stop PCM capture to pause audio ingestion.
    stopCapture();

    // 2. Explicitly notify the backend of the pause to halt active duration timer
    if (audioWsRef.current && audioWsRef.current.readyState === WebSocket.OPEN) {
      try {
        audioWsRef.current.send("pause");
      } catch (err) {
        console.warn("[DashboardPage] Failed to send 'pause' control message:", err);
      }
    }

    // Do NOT close the WebSocket here so we can restart.
    setAudioStatus("idle");
  }, [stopCapture]);

  /**
   * Ends the entire session.
   * Tells the backend to finalize it, stops capture, 
   * and relies on the backend to close the WebSocket.
   */
  const endSession = useCallback(() => {
    if (hasExplicitlyEnded.current) return;
    hasExplicitlyEnded.current = true;
    setIsEnding(true);

    stopCapture();
    setAudioStatus("idle");

    if (audioWsRef.current && audioWsRef.current.readyState === WebSocket.OPEN) {
      try {
        audioWsRef.current.send("end");
      } catch (err) {
        console.error("[DashboardPage] Failed to send 'end' explicitly:", err);
      }
    }
  }, [stopCapture, sessionStatus]);

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
        <div
          style={{
            border: "2px solid #ef4444",
            padding: "16px",
            background: "#fef2f2",
            textAlign: "center",
            borderRadius: "8px",
          }}
        >
          <h3 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>
            Session Initialization Failed
          </h3>
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
              onClick={() => navigate("/")}
              className="flex items-center gap-3 hover:opacity-85 transition-all"
            >
              <div className="relative w-9 h-9">
                <img
                  src={logoImage}
                  alt="TalkSense AI Logo"
                  className="w-full h-full object-contain"
                />
              </div>
              <span className="font-bold text-xl tracking-tight">
                <span style={{ color: "#4F46E5" }}>TalkSense</span>
                <span style={{ color: "#14B8A6" }}> AI</span>
              </span>
            </button>
            <div className="flex gap-6 items-center text-sm font-medium">
              <button
                onClick={() => navigate("/")}
                className="text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Home
              </button>
              <button
                onClick={() => navigate("/upload")}
                className="text-gray-500 hover:text-indigo-600 transition-colors"
              >
                Analyze
              </button>
              <button
                onClick={() => navigate("/sessions")}
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
              Configure your workspace and review client memory before starting
              the live session.
            </p>

            <div className="grid md:grid-cols-2 gap-8 mb-8 items-start">
              {/* Left Column: Config */}
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-3">
                    Conversation Mode
                  </label>
                  <div className="grid grid-cols-3 gap-3">
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
                    <button
                      onClick={() => setLauncherMode("interview")}
                      className={`py-3 px-4 rounded-xl border-2 text-center font-semibold transition-smooth ${
                        launcherMode === "interview"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-700 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300 text-gray-700"
                      }`}
                    >
                      Interview
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
                        {isCreatingClient
                          ? "← Choose Client"
                          : "+ Create Client"}
                      </button>
                    </div>

                    {isCreatingClient ? (
                      <form
                        onSubmit={handleCreateClient}
                        className="space-y-3 bg-white p-4 rounded-xl border border-gray-200 shadow-sm animate-scale-in"
                      >
                        <div>
                          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                            Company / Name
                          </label>
                          <input
                            type="text"
                            required
                            value={newClientName}
                            onChange={(e) => setNewClientName(e.target.value)}
                            placeholder="e.g. Acme Corporation"
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                            Industry (Optional)
                          </label>
                          <input
                            type="text"
                            value={newClientIndustry}
                            onChange={(e) =>
                              setNewClientIndustry(e.target.value)
                            }
                            placeholder="e.g. Software"
                            className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                        {clientCreateError && (
                          <p className="text-[10px] text-rose-600 mt-1">
                            ⚠️ {clientCreateError}
                          </p>
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
                        <option value="" disabled>
                          Select client...
                        </option>
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
                    <ClientBriefingCard
                      client={clientBriefing}
                      loading={briefingLoading}
                    />
                  ) : (
                    <div className="border-2 border-dashed border-gray-200 rounded-2xl p-8 text-center text-gray-400">
                      Select a client to load relationship memory profile.
                    </div>
                  )
                ) : (
                  <div className="bg-slate-50 border border-slate-150 rounded-2xl p-6 text-center text-slate-500">
                    <span className="block font-semibold mb-1 text-gray-800">
                      {launcherMode === "meeting"
                        ? "Meeting Mode selected"
                        : "Interview Mode selected"}
                    </span>
                    {launcherMode === "meeting"
                      ? "Internal team meeting mode does not use client relationship briefing memory."
                      : "Interview mode focuses on candidate evaluation and does not use client relationship briefing memory."}
                  </div>
                )}
              </div>
            </div>

            {/* Audio Source Configuration */}
            <div className="mt-8 pt-6 border-t border-gray-150">
              <label className="block text-sm font-bold text-gray-900 mb-4">
                Audio Source
              </label>
              <div className="flex gap-4">
                {availableSources?.map((source) => (
                  <label
                    key={source.id}
                    className={`flex items-center gap-3 p-4 border rounded-xl cursor-pointer transition-all ${
                      selectedSourceType === source.id
                        ? "border-indigo-600 bg-indigo-50 ring-1 ring-indigo-600"
                        : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="radio"
                      name="audioSource"
                      value={source.id}
                      checked={selectedSourceType === source.id}
                      onChange={() => setSourceType(source.id)}
                      className="text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                    />
                    <div>
                      <div className="font-semibold text-gray-900 text-sm">{source.displayName}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{source.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Launch CTA */}
            <div className="border-t border-gray-150 pt-8 mt-6">
              <button
                onClick={handleLaunchSession}
                disabled={
                  launchLoading ||
                  (launcherMode === "sales" && !selectedClientId)
                }
                className="w-full bg-indigo-600 text-white font-bold py-4 rounded-2xl shadow-lg hover:bg-indigo-700 hover:shadow-xl transition-smooth disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center active:scale-95"
              >
                {launchLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
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

  const isTerminal = ["completed", "failed", "interrupted", "expired"].includes(
    sessionStatus,
  );
  if (
    (connectionState === "idle" || connectionState === "connecting") &&
    !isTerminal
  ) {
    return (
      <main
        className="dashboard-loading-skeleton"
        style={{ padding: "16px", fontFamily: "sans-serif" }}
        aria-busy="true"
        aria-label="Loading session dashboard"
      >
        <div
          style={{
            height: "48px",
            background: "#e2e8f0",
            borderRadius: "4px",
            marginBottom: "16px",
          }}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr",
            gap: "16px",
          }}
        >
          <div
            style={{
              height: "400px",
              background: "#e2e8f0",
              borderRadius: "4px",
            }}
          />
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                height: "192px",
                background: "#e2e8f0",
                borderRadius: "4px",
              }}
            />
            <div
              style={{
                height: "192px",
                background: "#e2e8f0",
                borderRadius: "4px",
              }}
            />
          </div>
        </div>
      </main>
    );
  }

  // --- Render: Main dashboard ------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Unified Global Header */}
      <header className="sticky top-0 z-50 flex items-center px-6 bg-white border-b border-gray-200 h-16 shadow-sm">
        {/* Branding */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-3 hover:opacity-85 transition-all mr-6 shrink-0"
        >
          <div className="relative w-8 h-8">
            <img
              src={logoImage}
              alt="TalkSense AI Logo"
              className="w-full h-full object-contain"
            />
          </div>
          <span className="font-bold text-lg tracking-tight whitespace-nowrap hidden sm:inline-block">
            <span style={{ color: "#4F46E5" }}>TalkSense</span>
            <span style={{ color: "#14B8A6" }}> AI</span>
          </span>
        </button>

        {/* Navigation */}
        <div className="flex gap-5 items-center text-sm font-medium mr-8 shrink-0">
          <button onClick={() => navigate("/")} className="text-gray-500 hover:text-indigo-600 transition-colors">Home</button>
          <button onClick={() => navigate("/upload")} className="text-gray-500 hover:text-indigo-600 transition-colors">Analyze</button>
          <button onClick={() => navigate("/sessions")} className="text-gray-500 hover:text-indigo-600 transition-colors">History</button>
        </div>

        {/* SessionStatusBar (Left aligned next to nav) */}
        <div className="shrink-0">
          <SessionStatusBar
            sessionStatus={sessionStatus || "unknown"}
            connectionState={connectionState || "disconnected"}
            lastSyncAt={lastSyncAt}
            mode={activeSessionMode}
          />
        </div>

        {/* Right Side: Timer, Recording, Controls */}
        <div className="ml-auto flex items-center gap-4 shrink-0 pl-4">
          {/* Timer */}
          {metrics?.active_duration_seconds != null && (
            <div className="text-sm font-medium text-slate-700 whitespace-nowrap font-mono bg-slate-100 px-2 py-1 rounded">
              {new Date(metrics.active_duration_seconds * 1000).toISOString().substr(14, 5)}
            </div>
          )}

          {/* Recording Indicator */}
          {isCapturing && (
            <div className="flex items-center gap-2 text-red-500 text-xs font-bold animate-pulse whitespace-nowrap uppercase tracking-widest bg-red-50 px-2 py-1 rounded">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              REC
            </div>
          )}

          {/* Mic Controls */}
          {!isCapturing && sessionStatus !== "completed" && !isEnding && (
            <button
              id="start-mic-btn"
              onClick={startMicrophone}
              disabled={audioStatus === "connecting" || !validatedSessionId}
              style={{
                padding: "8px 16px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "#fff",
                background: audioStatus === "connecting" ? "#94a3b8" : "linear-gradient(135deg, #7c3aed, #4f46e5)",
                border: "none",
                borderRadius: "8px",
                cursor: audioStatus === "connecting" ? "not-allowed" : "pointer",
                letterSpacing: "0.03em",
                whiteSpace: "nowrap"
              }}
              aria-label={`Start ${selectedSourceType.replace('_', ' ')} capture`}
            >
              {audioStatus === "connecting"
                ? "⏳ Connecting…"
                : selectedSourceType === "system_audio"
                  ? "🖥️ Start System Audio"
                  : selectedSourceType === "mixed"
                    ? "🎙+🖥️ Start Mixed Audio"
                    : "🎙 Start Microphone"}
            </button>
          )}
          
          {isCapturing && sessionStatus !== "completed" && !isEnding && (
            <button
              id="stop-mic-btn"
              onClick={stopMicrophone}
              style={{
                padding: "8px 16px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "#fff",
                background: "linear-gradient(135deg, #f59e0b, #d97706)",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                letterSpacing: "0.03em",
                whiteSpace: "nowrap"
              }}
              aria-label={`Stop ${selectedSourceType.replace('_', ' ')} capture`}
            >
              {selectedSourceType === "system_audio"
                ? "⏸ Pause System Audio"
                : selectedSourceType === "mixed"
                  ? "⏸ Pause Mixed Audio"
                  : "⏸ Pause Microphone"}
            </button>
          )}

          {/* End Session Button */}
          {(isEnding || sessionStatus !== "completed") && (
            <button
              id="end-session-btn"
              onClick={endSession}
              disabled={isEnding || sessionStatus === "completed"}
              style={{
                padding: "8px 16px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "#fff",
                background: (isEnding || sessionStatus === "completed") ? "#64748b" : "linear-gradient(135deg, #dc2626, #b91c1c)",
                border: "none",
                borderRadius: "8px",
                cursor: (isEnding || sessionStatus === "completed") ? "not-allowed" : "pointer",
                letterSpacing: "0.03em",
                whiteSpace: "nowrap",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
              aria-label="End Session"
            >
              {isEnding ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Ending...
                </>
              ) : (
                "⏹ End Session"
              )}
            </button>
          )}
          
          {sessionStatus === "completed" && !isEnding && (
            <button
              disabled
              style={{
                padding: "8px 16px",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "#fff",
                background: "#94a3b8",
                border: "none",
                borderRadius: "8px",
                cursor: "not-allowed",
                letterSpacing: "0.03em",
                whiteSpace: "nowrap"
              }}
            >
              Session Completed
            </button>
          )}
        </div>
      </header>

      <main
        style={{ padding: "16px", height: "calc(100vh - 64px)", display: "flex", flexDirection: "column" }}
        className="max-w-[1400px] mx-auto w-full overflow-x-auto"
      >
        {/* --- Connection banners --- */}
        {connectionState === "reconnecting" && (
          <div
            key="banner-reconnecting"
            role="status"
            aria-live="polite"
            style={{
              background: "#f59e0b",
              color: "white",
              padding: "8px",
              textAlign: "center",
              borderRadius: "4px",
              marginBottom: "12px",
            }}
          >
            Reconnecting to session...
          </div>
        )}

        {connectionState === "failed" && (
          <div
            key="banner-failed"
            role="alert"
            style={{
              border: "2px solid #ef4444",
              padding: "16px",
              margin: "16px 0",
              background: "#fef2f2",
              textAlign: "center",
              borderRadius: "8px",
            }}
          >
            <h3 style={{ margin: "0 0 8px 0", color: "#991b1b" }}>
              Connection Failed
            </h3>
            <p style={{ margin: "0 0 12px 0", color: "#7f1d1d" }}>
              {error || "Unable to connect to the session WebSocket."}
            </p>
            <button
              onClick={handleReconnect}
              style={{
                padding: "8px 16px",
                cursor: "pointer",
                background: "#ef4444",
                color: "white",
                border: "none",
                borderRadius: "4px",
                fontWeight: "bold",
              }}
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
            style={{
              border: "2px solid #f59e0b",
              padding: "12px",
              margin: "0 0 12px 0",
              background: "#fffbeb",
              textAlign: "center",
              borderRadius: "8px",
            }}
          >
            <p style={{ margin: "0", color: "#92400e" }}>{permissionError}</p>
          </div>
        )}

        {/* --- Dashboard panels --- */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4 flex-1 min-h-0">
          <div className="lg:col-span-2 min-w-0 flex flex-col min-h-0 h-full">
            {sessionStatus === "completed" && (
              <div className="mb-4 bg-white border border-gray-200 rounded-xl p-6 shadow-sm shrink-0">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M11 12v5a2 2 0 11-4 0v-5a2 2 0 114 0z" />
                  </svg>
                  Session Recording
                </h3>
                {audioUrl ? (
                  <audio controls className="w-full" src={`${REST_BASE_URL}${audioUrl}`} />
                ) : (
                  <div className="text-gray-500 italic text-sm">No audio recording available for this session.</div>
                )}
              </div>
            )}
            <TranscriptPanel transcript={transcript || []} />
          </div>
          <div className="flex flex-col min-w-0 min-h-0 h-full">
            <ConversationSidebar 
              tips={metrics?.coachingTips || []}
              alerts={alerts || []}
              metrics={metrics || null}
              sessionStatus={sessionStatus}
              lastSyncAt={lastSyncAt}
              mode={activeSessionMode}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
