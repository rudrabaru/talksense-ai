import sys

with open('talksense-ui/src/pages/DashboardPage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we target the real navbar, not the skeleton UI
search_region = content.find('// --- Render: Main dashboard')
if search_region == -1:
    print('Failed to find main render block')
    sys.exit(1)

start_marker = '{/* Navbar */}'
end_marker = '{/* --- Dashboard panels --- */}'

start_idx = content.find(start_marker, search_region)
end_idx = content.find(end_marker, search_region)

if start_idx == -1 or end_idx == -1:
    print('Failed to find markers')
    sys.exit(1)

new_content = """{/* Unified Global Header */}
      <header className="sticky top-0 z-50 flex items-center px-6 bg-white border-b border-gray-200 h-16 shadow-sm min-w-max">
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
          {metrics?.duration_seconds != null && (
            <div className="text-sm font-medium text-slate-700 whitespace-nowrap font-mono bg-slate-100 px-2 py-1 rounded">
              {new Date(metrics.duration_seconds * 1000).toISOString().substr(14, 5)}
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
                background: (isEnding || sessionStatus === "completed") ? "#94a3b8" : "linear-gradient(135deg, #dc2626, #b91c1c)",
                border: "none",
                borderRadius: "8px",
                cursor: (isEnding || sessionStatus === "completed") ? "not-allowed" : "pointer",
                letterSpacing: "0.03em",
                whiteSpace: "nowrap"
              }}
              aria-label="End Session"
            >
              {isEnding ? "Ending..." : "⏹ End Session"}
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

        """

final_content = content[:start_idx] + new_content + content[end_idx:]
with open('talksense-ui/src/pages/DashboardPage.jsx', 'w', encoding='utf-8') as f:
    f.write(final_content)
