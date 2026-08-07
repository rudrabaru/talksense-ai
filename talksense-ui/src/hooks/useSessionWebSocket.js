import { useState, useRef, useCallback, useEffect } from "react";

// --- Constants ---------------------------------------------------------------
const WS_BASE_URL      = "ws://localhost:8000"; // Backend WebSocket base
const REST_BASE_URL    = "http://localhost:8000"; // Backend REST base (for sync)
const MAX_RETRIES      = 5;                      // Max reconnection attempts per channel
const BACKOFF_BASE_MS  = 1000;                   // Base delay for exponential backoff (ms)
const BACKOFF_MAX_MS   = 30000;                  // Maximum backoff ceiling (ms)
const MAX_ALERTS       = 50;                     // Max alerts retained in state

// --- Alert severity ordering --------------------------------------------------
// Used to sort alerts: Critical (0) > Warning (1) > Info (2)
const ALERT_SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 };

// --- Channel identifiers ------------------------------------------------------
// Must match the backend WebSocket routes defined in API_CONTRACT.md.
const CHANNELS = ["transcript", "metrics", "alerts", "status"];

// --- Connection States --------------------------------------------------------
// Single source of truth for high-level hook connection states and channel statuses.
const CONNECTION_STATES = {
  IDLE: "idle",
  CONNECTING: "connecting",
  CONNECTED: "connected",
  DEGRADED: "degraded",
  RECONNECTING: "reconnecting",
  FAILED: "failed"
};

// --- Dynamic Initializer Helper -----------------------------------------------
const createChannelMap = (initialValue) => {
  return CHANNELS.reduce((acc, ch) => {
    acc[ch] = initialValue;
    return acc;
  }, {});
};

// --- Hook --------------------------------------------------------------------
/**
 * useSessionWebSocket
 *
 * A reusable hook for managing the four outbound WebSocket channels for a
 * TalkSense AI session. Transport-agnostic: it knows nothing about audio
 * capture or UI layout.
 *
 * Channels (per API_CONTRACT.md):
 *   /ws/transcript/{session_id} -- push: new transcript segment on each utterance
 *   /ws/metrics/{session_id}    -- push: latest metrics snapshot (server may drop stale frames)
 *   /ws/alerts/{session_id}     -- push: alert events, never dropped by server
 *   /ws/status/{session_id}     -- push: session lifecycle status changes
 *
 * Reconnection strategy:
 *   Exponential backoff per channel. On successful reconnect, fetches
 *   GET /dashboard/{session_id} to reconcile missed state.
 *
 * Exposed API:
 *   transcript    -- TranscriptSegment[], deduplicated, ordered by start time
 *   metrics       -- MetricsSnapshot | null, replaced on each update (no accumulation)
 *   alerts        -- AlertEvent[], sorted by severity then timestamp (newest first within level)
 *   sessionStatus -- string: current lifecycle state (active, completed, failed, etc.)
 *   connectionState -- 'connecting' | 'connected' | 'reconnecting' | 'degraded' | 'failed' | 'idle'
 *   error         -- string | null, user-facing network or protocol error
 *   lastSyncAt    -- Date | null, timestamp of last successful REST dashboard sync
 *   reconnect()   -- manually retrigger all channel connections after a 'failed' state
 */
export function useSessionWebSocket(sessionId) {

  // --- State ------------------------------------------------------------------
  const [transcript, setTranscript] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [connectionState, setConnectionState] = useState(CONNECTION_STATES.IDLE);
  const [error, setError] = useState(null);
  const [lastSyncAt, setLastSyncAt] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);

  // --- Refs (survive re-renders without triggering them) ----------------------

  // isMountedRef: guards asynchronous state updates after unmount to prevent leaks and React warnings.
  const isMountedRef = useRef(true);

  // sockets: keyed by channel name, holds the active WebSocket instance.
  const socketsRef = useRef(createChannelMap(null));

  // retryCount: per-channel reconnection attempt counter.
  const retryCountRef = useRef(createChannelMap(0));

  // retryTimers: per-channel setTimeout handles for backoff scheduling.
  const retryTimersRef = useRef(createChannelMap(null));

  // isClosingRef: set true when the hook initiates a deliberate close.
  const isClosingRef = useRef(false);

  // needsReconciliationRef: set true on unexpected closure or manual reconnect to trigger REST sync on next connect.
  const needsReconciliationRef = useRef(true);

  // connectRef: holds reference to connect function to avoid TDZ circular warning in closures.
  const connectRef = useRef(null);

  // sessionIdRef: mirrors the sessionId prop in a ref to prevent stale closures.
  const sessionIdRef = useRef(sessionId);

  // sessionStatusRef: mirrors the sessionStatus state to prevent stale closures in WS callback.
  const sessionStatusRef = useRef(sessionStatus);
  useEffect(() => {
    sessionStatusRef.current = sessionStatus;
  }, [sessionStatus]);

  // channelStatusRef: tracking per-channel statuses for unified connectionState computation.
  const channelStatusRef = useRef(createChannelMap(CONNECTION_STATES.IDLE));

  // --- Lifecycle Guard: mount/unmount isMountedRef ---------------------------
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Helper to safely perform state transitions only if the component is currently mounted.
  const safeSetState = useCallback((setter, value) => {
    if (isMountedRef.current) {
      // [DEBUG-LIFECYCLE] log every sessionStatus state update
      if (setter === setSessionStatus) {
        console.warn(`[DEBUG-LIFECYCLE] safeSetState(setSessionStatus, "${value}") called at t=${performance.now().toFixed(1)}ms`, new Error().stack?.split('\n')[2]?.trim());
      }
      setter(value);
    }
  }, []);

  // --- Internal utilities ----------------------------------------------------

  /**
   * _buildWsUrl(channel, sid)
   * Constructs the full WebSocket URL for a given channel and session ID.
   */
  const _buildWsUrl = useCallback((channel, sid) => {
    const wsToken = localStorage.getItem(`ws_token_${sid}`);
    return `${WS_BASE_URL}/ws/${channel}/${sid}?token=${wsToken || ''}`;
  }, []);

  /**
   * _computeConnectionState()
   * Derives the unified connectionState from channelStatusRef values.
   * Worst-case wins: failed > reconnecting > connecting > connected > idle.
   */
  const _computeConnectionState = useCallback(() => {
    const statuses = Object.values(channelStatusRef.current);
    if (statuses.some((s) => s === CONNECTION_STATES.FAILED))       return CONNECTION_STATES.FAILED;
    if (statuses.some((s) => s === CONNECTION_STATES.RECONNECTING)) return CONNECTION_STATES.RECONNECTING;
    if (statuses.some((s) => s === CONNECTION_STATES.CONNECTING))   return CONNECTION_STATES.CONNECTING;
    if (statuses.every((s) => s === CONNECTION_STATES.CONNECTED))   return CONNECTION_STATES.CONNECTED;
    return CONNECTION_STATES.IDLE;
  }, []);

  /**
   * _sortAlerts(alertArray)
   * Returns a new array sorted by severity level (critical first) then
   * by descending timestamp (newest alert of same level first).
   */
  const _sortAlerts = useCallback((alertArray) => {
    return [...alertArray].sort((a, b) => {
      const levelDiff =
        (ALERT_SEVERITY_ORDER[a.level] ?? 99) -
        (ALERT_SEVERITY_ORDER[b.level] ?? 99);
      if (levelDiff !== 0) return levelDiff;
      return b.timestamp - a.timestamp; // newest first within same level
    });
  }, []);

  /**
   * _isTerminalStatus(status)
   * Returns true if the session lifecycle state requires connection teardown.
   */
  const _isTerminalStatus = useCallback((status) => {
    return ["completed", "failed", "expired", "interrupted"].includes(status);
  }, []);

  // --- _validateTranscriptSegment() -- INTERNAL ----------------------------
  /**
   * Returns true if a parsed transcript segment contains all required fields
   * with the correct types. Used to gate state updates and discard malformed
   * payloads without crashing the message handler.
   *
   * Required fields (per API_CONTRACT.md /ws/transcript):
   *   speaker (string, non-empty)
   *   text    (string, non-empty)
   *   start   (finite number)
   *   end     (finite number, >= start)
   */
  const _validateTranscriptSegment = useCallback((seg) => {
    return (
      seg !== null &&
      typeof seg === "object" &&
      typeof seg.speaker === "string" && seg.speaker.trim().length > 0 &&
      typeof seg.text   === "string" && seg.text.trim().length   > 0 &&
      typeof seg.start  === "number" && Number.isFinite(seg.start) &&
      typeof seg.end    === "number" && Number.isFinite(seg.end)   &&
      seg.end >= seg.start
    );
  }, []);

  /**
   * _unwrapEnvelope(raw, expectedChannel)
   *
   * Parses a raw WebSocket message string and extracts the inner payload.
   *
   * The backend wraps every outbound message in an envelope:
   *   { "type": "<channel>", "payload": {...}, "ts": <unix_ms> }
   *
   * This helper:
   *   1. JSON-parses the raw string.
   *   2. Validates that the outer object has the expected "type" value.
   *   3. Returns envelope.payload when the envelope is well-formed.
   *   4. Falls back to returning the parsed root object when no "type" key is
   *      present — preserving backward compatibility with any un-enveloped
   *      messages during testing or transition.
   *
   * Returns null on JSON parse failure or envelope shape mismatch (wrong type).
   * The caller is responsible for logging and early-returning on null.
   */
  const _unwrapEnvelope = useCallback((raw, expectedChannel) => {
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (parseErr) {
      console.warn(
        `[useSessionWebSocket] ${expectedChannel}: failed to parse message:`,
        raw, parseErr
      );
      return null;
    }

    // If the message lacks a "type" key it is a raw (legacy/test) payload.
    // Return it directly so all downstream validation still runs.
    if (parsed === null || typeof parsed !== "object" || !("type" in parsed)) {
      return parsed;
    }

    // Envelope shape: { type, payload, ts }
    if (parsed.type !== expectedChannel) {
      console.warn(
        `[useSessionWebSocket] ${expectedChannel}: envelope type mismatch ` +
        `(expected "${expectedChannel}", got "${parsed.type}") — discarding.`
      );
      return null;
    }

    if (parsed.payload === undefined || parsed.payload === null || typeof parsed.payload !== "object") {
      console.warn(
        `[useSessionWebSocket] ${expectedChannel}: envelope.payload is absent or not an object — discarding.`,
        parsed
      );
      return null;
    }

    return parsed.payload;
  }, []);

  /**
   * reconcileState(sid)
   * Fetches the complete session state from the REST API to merge and reconcile.
   */
  const reconcileState = useCallback((sid) => {
    if (!sid) return;
    console.log(`[useSessionWebSocket] Triggering REST reconciliation for session: ${sid}`);

    fetch(`${REST_BASE_URL}/dashboard/${sid}`)
      .then((res) => {
        if (res.status === 404) {
          throw new Error("Session not found");
        }
        if (!res.ok) {
          throw new Error(`Failed to fetch dashboard: ${res.statusText}`);
        }
        return res.json();
      })
      .then((data) => {
        if (!isMountedRef.current) return;

        // Reset retry counters for all channels
        CHANNELS.forEach((ch) => {
          retryCountRef.current[ch] = 0;
        });

        // Merge transcripts
        safeSetState(setTranscript, (prev) => {
          // If session is completed, we want a full replace to ensure offline diarization 
          // (Phase 67) segments overwrite the live segments entirely.
          if (data.status === "completed") {
            return (data.transcript_segments || []).sort((a, b) => a.start - b.start);
          }

          const incomingMap = new Map();
          (data.transcript_segments || []).forEach((seg) => {
            incomingMap.set(seg.start, seg);
          });

          const updatedPrev = prev.map((s) => {
            if (incomingMap.has(s.start)) {
              const incomingSeg = incomingMap.get(s.start);
              incomingMap.delete(s.start);
              return incomingSeg;
            }
            return s;
          });

          const brandNew = Array.from(incomingMap.values());
          return [...updatedPrev, ...brandNew].sort((a, b) => a.start - b.start);
        });

        // Replace metrics
        if (data.health_score !== undefined || data.sentiment !== undefined) {
          const restMetrics = {
            health_score: data.health_score,
            sentiment: data.sentiment,
            speaking_ratio: data.speaking_ratio,
            participation: data.participation,
            filler_count: data.filler_count,
            objections: data.objections || [],
            buying_signals: data.buying_signals || [],
            interruptions: data.interruptions ?? 0,
            speaker_switches: data.speaker_switches ?? 0,
            action_items: data.action_items || [],
            decisions: data.decisions || [],
            objection_timeline: data.objection_timeline || [],
            buying_signal_timeline: data.buying_signal_timeline || [],
            filler_penalty: data.filler_penalty ?? 0,
            pause_penalty: data.pause_penalty ?? 0,
            duration_seconds: data.elapsed_seconds ?? data.duration_seconds,
            speakerAttributionStatus: data.speaker_attribution_status ?? null,
            speakerAttribution: data.speaker_attribution ?? null,
            speakerRoles: data.speaker_roles ?? null,
            objectionHandling: data.objection_handling ?? [],
            talkRatioSummary: data.talk_ratio_summary ?? null,
            talkTimeline: data.talk_timeline ?? null,
            analyticsHealth: data.analytics_health ?? null,
            coachingTips: data.coaching_tips || [],
            postSessionAi: data.post_session_ai ?? null,
            last_updated: data.last_updated ?? 0,
          };
          safeSetState(setMetrics, (prev) => {
            const currentTimestamp = prev?.last_updated ?? 0;
            const incomingTimestamp = restMetrics.last_updated;

            if (currentTimestamp && incomingTimestamp <= currentTimestamp) {
              console.log("[useSessionWebSocket] Stale REST payload received. Hydrating missing state only.");
              return {
                ...prev,
                speakerAttributionStatus: prev?.speakerAttributionStatus ?? restMetrics.speakerAttributionStatus,
                speakerAttribution: prev?.speakerAttribution ?? restMetrics.speakerAttribution,
                speakerRoles: prev?.speakerRoles ?? restMetrics.speakerRoles,
                objectionHandling: prev?.objectionHandling ?? restMetrics.objectionHandling,
                talkRatioSummary: prev?.talkRatioSummary ?? restMetrics.talkRatioSummary,
                talkTimeline: prev?.talkTimeline ?? restMetrics.talkTimeline,
                analyticsHealth: prev?.analyticsHealth ?? restMetrics.analyticsHealth,
                postSessionAi: prev?.postSessionAi ?? restMetrics.postSessionAi,
              };
            }
            console.log("[useSessionWebSocket] Fresh REST payload received. Performing full replace.");
            return restMetrics;
          });
        }

        // Merge alerts
        safeSetState(setAlerts, (prev) => {
          const existingKeys = new Set(
            prev.map((a) => `${a.level}|${a.message}|${a.timestamp}`)
          );
          const newAlerts = (data.active_alerts || []).filter(
            (a) => !existingKeys.has(`${a.level}|${a.message}|${a.timestamp}`)
          );
          if (newAlerts.length === 0) return prev;
          return _sortAlerts([...prev, ...newAlerts]).slice(0, MAX_ALERTS);
        });

        // Restore session status from REST snapshot
        if (typeof data.status === "string" && data.status.trim().length > 0) {
          console.warn(`[DEBUG-LIFECYCLE] reconcileState: setSessionStatus("${data.status}") from REST at t=${performance.now().toFixed(1)}ms`);
          safeSetState(setSessionStatus, data.status);
          safeSetState(setAudioUrl, data.audio_url || null);
        }

        safeSetState(setLastSyncAt, new Date());
      })
      .catch((err) => {
        console.error("[useSessionWebSocket] Reconciliation fetch failed:", err);
        if (err.message === "Session not found") {
          safeSetState(setSessionStatus, "failed");
          safeSetState(setError, "Session not found on backend.");
        }
      });
  }, [_sortAlerts, safeSetState]);

  // --- disconnect() -- INTERNAL ----------------------------------------------
  /**
   * Deliberately closes all open WebSocket connections.
   * Sets isClosingRef = true BEFORE closing so that onclose handlers know the
   * closure was intentional and do NOT schedule reconnection attempts.
   *
   * Cancels all pending retry timers.
   * Does NOT reset state -- call cleanup() for full state reset.
   */
  const disconnect = useCallback(() => {
    console.warn(`[DEBUG-LIFECYCLE] disconnect() CALLED at t=${performance.now().toFixed(1)}ms`, new Error().stack?.split('\n')[2]?.trim());
    console.log("[useSessionWebSocket] Disconnecting all channels.");

    // Signal intentional close to onclose handlers.
    isClosingRef.current = true;

    // Cancel all pending retry timers so no reconnect fires after disconnect.
    CHANNELS.forEach((channel) => {
      if (retryTimersRef.current[channel] !== null) {
        clearTimeout(retryTimersRef.current[channel]);
        retryTimersRef.current[channel] = null;
      }
    });

    // Close each open socket. onclose will detach handlers and null the ref.
    CHANNELS.forEach((channel) => {
      const ws = socketsRef.current[channel];
      if (ws &&
          (ws.readyState === WebSocket.OPEN ||
           ws.readyState === WebSocket.CONNECTING)) {
        ws.close(1000, "Client disconnecting");
      }
      channelStatusRef.current[channel] = CONNECTION_STATES.IDLE;
    });

    safeSetState(setConnectionState, CONNECTION_STATES.IDLE);
  }, [safeSetState]);

  // --- connect() -- INTERNAL -------------------------------------------------
  /**
   * Opens all 4 WebSocket channels concurrently for the current sessionId.
   * Idempotent: skips any channel that already has an open or connecting socket.
   *
   * For each channel:
   *   1. Sets channelStatusRef[ch] = CONNECTING and recomputes unified state.
   *   2. Creates the WebSocket and stores it in socketsRef.
   *   3. onopen    -- marks channel CONNECTED, recomputes state.
   *   4. onclose   -- marks channel IDLE (if intentional) or triggers reconnect.
   *   5. onerror   -- logs; onclose will fire next and handles state.
   *   6. onmessage -- channel-specific routing (transcript: wired; others: Phase 4.2d).
   */
  const connect = useCallback(() => {
    const sid = sessionIdRef.current;
    if (!sid) {
      console.warn("[useSessionWebSocket] connect() called with no sessionId.");
      return;
    }

    // Clear the intentional-close flag before opening.
    isClosingRef.current = false;

    console.log(`[useSessionWebSocket] Opening ${CHANNELS.length} channels for session: ${sid}`);

    let stateChanged = false;

    CHANNELS.forEach((channel) => {
      // Skip if an open or connecting socket already exists for this channel.
      const existing = socketsRef.current[channel];
      if (existing &&
          (existing.readyState === WebSocket.OPEN ||
           existing.readyState === WebSocket.CONNECTING)) {
        console.log(`[useSessionWebSocket] Channel "${channel}" already open, skipping.`);
        return;
      }

      // Mark this channel as connecting (unified state synced after loop).
      channelStatusRef.current[channel] = CONNECTION_STATES.CONNECTING;
      stateChanged = true;

      const url = _buildWsUrl(channel, sid);
      const ws  = new WebSocket(url);
      socketsRef.current[channel] = ws;

      // --- onopen: channel is live ------------------------------------------
      ws.onopen = () => {
        if (!isMountedRef.current) return;
        if (socketsRef.current[channel] !== ws) {
          console.log(`[useSessionWebSocket] Stale socket opened for "${channel}", ignoring.`);
          return;
        }
        console.log(`[useSessionWebSocket] Channel "${channel}" connected.`);
        retryCountRef.current[channel] = 0; // reset backoff on clean open
        channelStatusRef.current[channel] = CONNECTION_STATES.CONNECTED;
        safeSetState(setConnectionState, _computeConnectionState());
        safeSetState(setError, null);

        if (needsReconciliationRef.current) {
          needsReconciliationRef.current = false;
          reconcileState(sid);
        }
      };

      // --- onclose: distinguish intentional from unexpected -----------------
      ws.onclose = (event) => {
        if (!isMountedRef.current) return;

        // Detach handlers so the dead socket cannot fire further callbacks.
        ws.onopen    = null;
        ws.onclose   = null;
        ws.onerror   = null;
        ws.onmessage = null;

        // [DEBUG-LIFECYCLE] Log every onclose for every channel
        console.warn(
          `[DEBUG-LIFECYCLE] onclose FIRED for channel="${channel}" code=${event.code} ` +
          `intentional=${isClosingRef.current} sessionStatusRef="${sessionStatusRef.current}" ` +
          `t=${performance.now().toFixed(1)}ms`
        );

        // If this socket is no longer the active one in the ref, it means
        // a new connection attempt has already taken over (e.g. StrictMode
        // remount). Ignore this close event to prevent rogue reconnect loops.
        if (socketsRef.current[channel] !== ws) {
          console.log(`[useSessionWebSocket] Stale socket closed for "${channel}", ignoring.`);
          return;
        }

        const intentional = isClosingRef.current;
        const isTerminalCode = event.code === 4004 || event.code === 4009;

        console.log(
          `[useSessionWebSocket] Channel "${channel}" closed ` +
          `(code: ${event.code}, intentional: ${intentional}).`
        );

        socketsRef.current[channel] = null;

        if (intentional || isTerminalCode || _isTerminalStatus(sessionStatusRef.current)) {
          if (isTerminalCode) {
            channelStatusRef.current[channel] = CONNECTION_STATES.FAILED;
            if (event.code === 4004) {
              safeSetState(setError, `Session not found on backend (4004).`);
              safeSetState(setSessionStatus, "failed");
            } else if (event.code === 4009) {
              console.warn(`[DEBUG-LIFECYCLE] onclose code=4009 on channel="${channel}" → setSessionStatus("completed") at t=${performance.now().toFixed(1)}ms`);
              safeSetState(setError, `Session has ended (4009).`);
              safeSetState(setSessionStatus, "completed");
            }
          } else {
            channelStatusRef.current[channel] = CONNECTION_STATES.IDLE;
          }
        } else {
          needsReconciliationRef.current = true;
          const attempt = retryCountRef.current[channel];
          if (attempt < MAX_RETRIES) {
            channelStatusRef.current[channel] = CONNECTION_STATES.RECONNECTING;
            const jitter = Math.random() * 1000; // random jitter up to 1 second
            const delay = Math.min(
              BACKOFF_BASE_MS * Math.pow(2, attempt) + jitter,
              BACKOFF_MAX_MS
            );
            console.log(
              `[useSessionWebSocket] Channel "${channel}" closed unexpectedly. ` +
              `Scheduling retry ${attempt + 1}/${MAX_RETRIES} in ${Math.round(delay)}ms.`
            );
            retryCountRef.current[channel] = attempt + 1;

            if (retryTimersRef.current[channel] !== null) {
              clearTimeout(retryTimersRef.current[channel]);
            }
            retryTimersRef.current[channel] = setTimeout(() => {
              retryTimersRef.current[channel] = null;
              if (connectRef.current) {
                connectRef.current();
              }
            }, delay);
          } else {
            channelStatusRef.current[channel] = CONNECTION_STATES.FAILED;
            safeSetState(setError, `Connection lost: Channel "${channel}" failed to reconnect after ${MAX_RETRIES} attempts.`);
            console.error(
              `[useSessionWebSocket] Channel "${channel}" reached max retries (${MAX_RETRIES}).`
            );
          }
        }
        safeSetState(setConnectionState, _computeConnectionState());
      };

      // --- onerror: log only; onclose always fires after ------------------
      ws.onerror = (event) => {
        if (socketsRef.current[channel] !== ws) return;
        console.error(`[useSessionWebSocket] Channel "${channel}" error:`, event);
      };

      // --- onmessage: channel-specific routing ------------------------------
      switch (channel) {

        case "transcript":
          ws.onmessage = (event) => {
            if (!isMountedRef.current) return;
            if (socketsRef.current[channel] !== ws) return;

            // Step 1: Unwrap backend envelope { type, payload, ts } → payload.
            // Falls back to the raw parsed object for un-enveloped messages.
            const seg = _unwrapEnvelope(event.data, "transcript");
            if (seg === null) return; // parse failure or type mismatch already logged

            // Step 2: Structural validation -- discard if any required field is absent or wrong type.
            if (!_validateTranscriptSegment(seg)) {
              console.warn(
                "[useSessionWebSocket] transcript: discarding malformed segment:",
                seg
              );
              return;
            }

            // Step 3: Deduplication + append via functional state update.
            // Composite key: speaker + start + end + text covers both identity
            // (speaker, start, end) and content (text) so partial re-sends
            // from reconnect sync do not create duplicate visible lines.
            safeSetState(setTranscript, (prev) => {
              // If segment_id is provided, try to update in place
              if (seg.segment_id) {
                const idx = prev.findIndex(s => s.segment_id === seg.segment_id);
                if (idx >= 0) {
                  const copy = [...prev];
                  copy[idx] = { ...copy[idx], ...seg };
                  return copy;
                }
              }

              // Fallback / legacy deduplication
              const key = `${seg.speaker}|${seg.start}|${seg.end}|${seg.text}`;
              const isDuplicate = prev.some(
                (s) => (`${s.speaker}|${s.start}|${s.end}|${s.text}` === key) || (seg.segment_id && s.segment_id === seg.segment_id)
              );
              if (isDuplicate) return prev;
              
              return [...prev, seg];
            });
          };
          break;

        // --- metrics: replace-only snapshot --------------------------------
        case "metrics":
          ws.onmessage = (event) => {
            if (!isMountedRef.current) return;
            if (socketsRef.current[channel] !== ws) return;

            // Unwrap backend envelope { type, payload, ts } → payload.
            let payload = _unwrapEnvelope(event.data, "metrics");
            if (payload === null) return; // parse failure or type mismatch already logged

            if (typeof payload !== "object") {
              console.warn("[useSessionWebSocket] metrics: payload is not an object, discarding.");
              safeSetState(setMetrics, null);
              return;
            }

            // Clamp health_score to [0, 100] if present -- all other fields
            // are passed through as-is. Prefer clamping over discarding so
            // the rest of the snapshot (sentiment, ratios, etc.) is not lost.
            if (typeof payload.health_score === "number") {
              payload = {
                ...payload,
                health_score: Math.max(0, Math.min(100, payload.health_score)),
              };
            }

            // Full replace -- never accumulate intermediate frames, but preserve
            // speakerAttributionStatus and speakerAttribution (diagnostics only
            // arrive via REST polling, never via the live metrics WebSocket).
            safeSetState(setMetrics, (prev) => {
              const incoming = payload;
              const incomingTimestamp = incoming.last_updated ?? 0;
              const currentTimestamp = prev?.last_updated ?? 0;

              if (currentTimestamp && incomingTimestamp <= currentTimestamp) {
                console.log("[useSessionWebSocket] WS metrics payload is older than current state. Ignoring.");
                return prev;
              }

              const speakerAttributionStatus =
                incoming.speaker_attribution_status ??
                incoming.speakerAttributionStatus ??
                prev?.speakerAttributionStatus ??
                null;
              const speakerAttribution =
                incoming.speakerAttribution ??
                incoming.speaker_attribution ??
                prev?.speakerAttribution ??
                null;
              const speakerRoles =
                incoming.speakerRoles ??
                incoming.speaker_roles ??
                prev?.speakerRoles ??
                null;
              const talkRatioSummary =
                incoming.talkRatioSummary ??
                incoming.talk_ratio_summary ??
                prev?.talkRatioSummary ??
                null;
              const talkTimeline =
                incoming.talkTimeline ??
                incoming.talk_timeline ??
                prev?.talkTimeline ??
                null;
              const analyticsHealth =
                incoming.analyticsHealth ??
                incoming.analytics_health ??
                prev?.analyticsHealth ??
                null;
              const coachingTips = 
                incoming.coachingTips ??
                incoming.coaching_tips ??
                prev?.coachingTips ??
                [];
              const postSessionAi =
                incoming.postSessionAi ??
                incoming.post_session_ai ??
                prev?.postSessionAi ??
                null;
              return {
                ...incoming,
                speakerAttributionStatus,
                speakerAttribution,
                speakerRoles,
                talkRatioSummary,
                talkTimeline,
                analyticsHealth,
                coachingTips,
                postSessionAi,
                last_updated: incomingTimestamp,
              };
            });
          };
          break;

        // --- alerts: append, sort by severity + timestamp, cap at MAX_ALERTS --
        case "alerts":
          ws.onmessage = (event) => {
            if (!isMountedRef.current) return;
            if (socketsRef.current[channel] !== ws) return;

            // Unwrap backend envelope { type, payload, ts } → payload.
            let alert = _unwrapEnvelope(event.data, "alerts");
            if (alert === null) return; // parse failure or type mismatch already logged

            if (typeof alert !== "object") {
              console.warn("[useSessionWebSocket] alerts: payload is not an object, discarding.");
              return;
            }

            // message is required -- discard if absent or blank.
            if (typeof alert.message !== "string" || alert.message.trim().length === 0) {
              console.warn("[useSessionWebSocket] alerts: missing message field, discarding.", alert);
              return;
            }

            // Normalise level -- default unknown levels to 'info' rather than discard.
            const VALID_LEVELS = ["critical", "warning", "info"];
            if (!VALID_LEVELS.includes(alert.level)) {
              console.warn(
                `[useSessionWebSocket] alerts: unknown level "${alert.level}", treating as "info".`
              );
              alert = { ...alert, level: "info" };
            }

            // Substitute missing timestamp with current time.
            if (typeof alert.timestamp !== "number" || !Number.isFinite(alert.timestamp)) {
              alert = { ...alert, timestamp: Date.now() / 1000 };
            }

            safeSetState(setAlerts, (prev) => {
              const merged = [...prev, alert];
              // Sort: critical (0) > warning (1) > info (2), newest first within level.
              const sorted = _sortAlerts(merged);
              // Cap at MAX_ALERTS -- lowest-priority entries are already at the tail.
              return sorted.length > MAX_ALERTS ? sorted.slice(0, MAX_ALERTS) : sorted;
            });
          };
          break;

        // --- status: update sessionStatus, trigger teardown on terminal state --
        case "status":
          ws.onmessage = (event) => {
            if (!isMountedRef.current) return;
            if (socketsRef.current[channel] !== ws) return;

            console.warn(`[DEBUG-LIFECYCLE] STATUS WS onmessage FIRED at t=${performance.now().toFixed(1)}ms — raw:`, event.data);

            // Unwrap backend envelope { type, payload, ts } → payload.
            const payload = _unwrapEnvelope(event.data, "status");
            if (payload === null) return; // parse failure or type mismatch already logged

            const status = payload?.status;

            // Discard if status is absent or not a non-empty string.
            if (typeof status !== "string" || status.trim().length === 0) {
              console.warn("[useSessionWebSocket] status: missing or empty status field, discarding.", payload);
              return;
            }

            // elapsed_seconds is intentionally NOT stored in hook state.
            // It is cosmetic and better owned by a timer in the consuming component.
            console.warn(`[DEBUG-LIFECYCLE] STATUS WS → setSessionStatus("${status}") at t=${performance.now().toFixed(1)}ms`);
            safeSetState(setSessionStatus, status);

            // Trigger clean teardown on terminal lifecycle transitions.
            // disconnect() sets isClosingRef = true, suppressing reconnect logic.
            if (_isTerminalStatus(status)) {
              console.warn(`[DEBUG-LIFECYCLE] STATUS WS → terminal "${status}" → calling disconnect() at t=${performance.now().toFixed(1)}ms`);
              console.log(`[useSessionWebSocket] Terminal status received: "${status}". Disconnecting.`);
              disconnect();
            }
          };
          break;

        default:
          ws.onmessage = null;
          break;
      }
    });

    // Batch connection state update: compute and set once for all newly connecting channels.
    if (stateChanged) {
      safeSetState(setConnectionState, _computeConnectionState());
    }
  }, [_buildWsUrl, _computeConnectionState, _unwrapEnvelope, _validateTranscriptSegment, _isTerminalStatus, _sortAlerts, safeSetState, disconnect, reconcileState]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);


  // --- cleanup() -- INTERNAL -------------------------------------------------
  /**
   * Full teardown: disconnects all channels and resets all state to initial values.
   * Intended for:
   *   - useEffect return (component unmount or sessionId change)
   *   - Explicit session end before starting a new session
   *
   * Resets transcript, metrics, alerts, and sessionStatus so stale data from
   * the previous session does not bleed into the next one.
   */
  const cleanup = useCallback(() => {
    console.log("[useSessionWebSocket] Running full cleanup.");

    disconnect();

    // Reset retry counters for all channels.
    CHANNELS.forEach((ch) => {
      retryCountRef.current[ch] = 0;
    });

    // Reset all data and meta state to initial values.
    safeSetState(setTranscript, []);
    safeSetState(setMetrics, null);
    safeSetState(setAlerts, []);
    safeSetState(setSessionStatus, null);
    safeSetState(setConnectionState, CONNECTION_STATES.IDLE);
    safeSetState(setError, null);
    safeSetState(setLastSyncAt, null);
    safeSetState(setAudioUrl, null);

    console.log("[useSessionWebSocket] Cleanup complete.");
  }, [disconnect, safeSetState]);

  // --- reconnect() -- PUBLIC --------------------------------------------------
  /**
   * Manually retrigger all four channel connections.
   * Intended for user-initiated recovery after connectionState === 'failed'.
   * Resets all retry counters, cancels pending backoff timers, then calls connect().
   */
  const reconnect = useCallback(() => {
    if (!sessionIdRef.current) {
      console.warn("[useSessionWebSocket] reconnect() called with no sessionId.");
      return;
    }

    if (_isTerminalStatus(sessionStatus)) {
      console.warn(`[useSessionWebSocket] reconnect() aborted: session is ${sessionStatus}.`);
      safeSetState(setError, `Cannot reconnect: session has already ${sessionStatus}.`);
      return;
    }

    console.log("[useSessionWebSocket] Manual reconnect triggered.");

    needsReconciliationRef.current = true;

    // Reset retry counters for all channels.
    CHANNELS.forEach((ch) => {
      retryCountRef.current[ch] = 0;
    });

    // Cancel any pending backoff timers.
    CHANNELS.forEach((ch) => {
      if (retryTimersRef.current[ch] !== null) {
        clearTimeout(retryTimersRef.current[ch]);
        retryTimersRef.current[ch] = null;
      }
    });

    safeSetState(setError, null);
    connect();
  }, [sessionStatus, _isTerminalStatus, safeSetState, connect]);

  // --- Lifecycle: open connections when sessionId is set ---------------------
  // Keyed on sessionId: tears down old connections before opening new ones when
  // the session changes (e.g. user starts a second session without full unmount).
  useEffect(() => {
    if (!sessionId) return;
    sessionIdRef.current = sessionId;
    needsReconciliationRef.current = true;
    reconcileState(sessionId);
    connect();
    return () => {
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, reconcileState]);

  // --- Auto-disconnect when session becomes terminal --------------------------
  useEffect(() => {
    if (_isTerminalStatus(sessionStatus)) {
      console.log(`[useSessionWebSocket] Session status is terminal ("${sessionStatus}"). Disconnecting.`);
      disconnect();
    }
  }, [sessionStatus, _isTerminalStatus, disconnect]);

  // --- Auto-Refresh Polling for Post-Session Analysis -------------------------
  useEffect(() => {
    const shouldPoll =
      sessionStatus === "completed" &&
      (
        metrics?.speakerAttributionStatus == null ||
        metrics?.speakerAttributionStatus === "pending" ||
        metrics?.speakerAttributionStatus === "processing" ||
        !metrics?.postSessionAi
      );

    if (!shouldPoll) return;

    console.log(`[useSessionWebSocket] Post-session analysis pending. Starting auto-refresh polling.`);

    const intervalId = setInterval(() => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      reconcileState(sid);
    }, 5000);

    return () => {
      console.log("[useSessionWebSocket] Stopping auto-refresh polling.");
      clearInterval(intervalId);
    };
  }, [sessionStatus, metrics?.speakerAttributionStatus, metrics?.postSessionAi, reconcileState]);

  // --- Exposed API ------------------------------------------------------------
  return {
    // Data state
    transcript,
    metrics,
    alerts,
    sessionStatus,

    // Connection meta
    connectionState,
    error,
    lastSyncAt,
    audioUrl,

    // Actions
    reconnect,
    reconcile: useCallback(() => reconcileState(sessionId), [sessionId, reconcileState]),
  };
}
