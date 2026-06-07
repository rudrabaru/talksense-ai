import { useState, useRef, useCallback } from "react";

// --- Constants ---------------------------------------------------------------
const TARGET_SAMPLE_RATE  = 16000;   // Hz  -- backend requires 16kHz PCM
const CHUNK_INTERVAL_MS   = 250;     // ms  -- emit chunks every 250ms per API contract
const CHUNK_SAMPLES       = TARGET_SAMPLE_RATE * (CHUNK_INTERVAL_MS / 1000); // 4000 samples

// --- AudioWorklet processor (inline blob) ------------------------------------
// Defined as a string and loaded as a Blob URL to avoid:
//   1. Vite static-file path resolution issues with addModule() string paths.
//   2. Cross-origin restrictions when serving from localhost.
// The processor runs on the dedicated audio rendering thread (off the UI thread)
// which guarantees uninterrupted capturing regardless of React render cycles.
//
// Responsibilities:
//   * Mono downmix -- averages all input channels (handles stereo mics)
//   * 16kHz resampling -- stateful linear interpolation (phase-continuous across blocks)
//   * Float32 -> Int16 conversion -- clamp + scale for PCM 16-bit signed
//   * 250ms chunk accumulation -- emits exactly CHUNK_SAMPLES per message
//
// Performance design (HIGH IMPACT):
//   All intermediate buffers are pre-allocated in the constructor.
//   The hot-path process() call makes zero heap allocations during the
//   250ms accumulation window (~370 calls @ 48kHz input).
//
// Audio quality design (HIGH IMPACT):
//   The resampler carries its fractional phase (_nextInputTime) across
//   block boundaries, eliminating the ~344-375Hz harmonic buzz injected
//   by the previous block-local phase-reset approach.
const WORKLET_CODE = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    // sampleRate is the AudioContext rate -- may differ from 16000 if the
    // browser ignored the sampleRate hint in new AudioContext({ sampleRate }).
    this._inputRate    = sampleRate;
    this._targetRate   = options.processorOptions.targetRate;
    this._ratio        = this._inputRate / this._targetRate;
    this._chunkSamples = options.processorOptions.chunkSamples;

    // -- Pre-allocated intermediate buffers (HIGH IMPACT: GC pressure fix) ----
    // process() receives exactly 128 input frames per call (Web Audio spec).
    // Worst-case resampled output per block = ceil(128 / ratio).
    // Using 128 covers all realistic hardware rates >= 16kHz safely.
    this._monoBuffer      = new Float32Array(128); // downmix workspace
    this._resampledBuffer = new Float32Array(128); // resampled workspace

    // -- Fixed-size ring buffer (HIGH IMPACT: replaces dynamic _accumulator) --
    // Sized at 2x chunkSamples to absorb up to two full output chunks without
    // wrapping. _writeHead advances; _ringCount tracks valid unread samples.
    const ringSize  = this._chunkSamples * 2;
    this._ringBuf   = new Float32Array(ringSize);
    this._ringCount = 0;
    this._writeHead = 0;

    // -- Stateful resampler phase (HIGH IMPACT: audio quality fix) ------------
    // _nextInputTime: fractional input position of the next output sample.
    //   Persists across process() calls -- the key fix for block-boundary buzz.
    // _lastSample: final sample of the previous block, used for cross-boundary
    //   interpolation when _nextInputTime < 0.
    this._nextInputTime = 0.0;
    this._lastSample    = 0.0;

    // -- Output buffer pool (MEDIUM IMPACT) -----------------------------------
    // The main thread returns consumed ArrayBuffers via port.onmessage.
    // Reusing them avoids a new 8KB allocation on every 250ms emit.
    this._outBuf = null;
    this.port.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer &&
          ev.data.byteLength >= this._chunkSamples * 2) {
        this._outBuf = ev.data; // reclaim for reuse
      }
    };
  }

  process(inputs) {
    const input = inputs[0];
    // No audio data yet (e.g. mic not started) -- keep processor alive.
    if (!input || input.length === 0) return true;

    const numChannels = input.length;
    const numSamples  = input[0].length; // always 128 per Web Audio spec

    // -- 1. Mono downmix (LOW IMPACT: mono short-circuit) ---------------------
    //    Short-circuit for mono mics (most common case) -- avoids copy.
    //    For stereo, average all channels into the pre-allocated workspace.
    let mono;
    if (numChannels === 1) {
      mono = input[0]; // direct reference -- zero copy
    } else {
      mono = this._monoBuffer;
      for (let i = 0; i < numSamples; i++) {
        let sum = 0;
        for (let ch = 0; ch < numChannels; ch++) sum += input[ch][i];
        mono[i] = sum / numChannels;
      }
    }

    // -- 2. Stateful linear resampling (HIGH IMPACT: phase-continuous) --------
    //    _nextInputTime is the fractional input-frame position of the next
    //    output sample. It is maintained across process() calls so that the
    //    interpolation phase is continuous at block boundaries.
    //
    //    When _nextInputTime < 0, the output sample straddles the boundary
    //    between the previous block and this one. _lastSample provides the
    //    left neighbour for the lerp in that case.
    let outCount = 0;

    if (this._ratio === 1.0) {
      // Passthrough -- browser honoured the 16kHz sampleRate hint.
      this._resampledBuffer.set(mono, 0);
      outCount = numSamples;
      this._nextInputTime = 0.0; // ratio=1: phase always resets cleanly
    } else {
      let t = this._nextInputTime; // carry in fractional phase from last block
      while (t < numSamples) {
        let sample;
        if (t < 0) {
          // Cross-boundary interpolation:
          //   t is in [-ratio, 0). (1+t) and (-t) are both in (0,1] and sum to 1.
          sample = this._lastSample * (1.0 + t) + mono[0] * (-t);
        } else {
          const lo = Math.floor(t);
          const hi = Math.min(lo + 1, numSamples - 1);
          const f  = t - lo;
          sample = mono[lo] * (1.0 - f) + mono[hi] * f;
        }
        this._resampledBuffer[outCount++] = sample;
        t += this._ratio;
      }
      // Carry fractional phase forward into the next block's coordinate space.
      this._nextInputTime = t - numSamples;
    }

    // Save the last sample for cross-boundary interpolation next call.
    this._lastSample = mono[numSamples - 1];

    // -- 3. Write into ring buffer --------------------------------------------
    for (let i = 0; i < outCount; i++) {
      this._ringBuf[this._writeHead] = this._resampledBuffer[i];
      this._writeHead = (this._writeHead + 1) % this._ringBuf.length;
      this._ringCount++;
    }

    // -- 4. Emit 250ms chunks of Int16 PCM ------------------------------------
    while (this._ringCount >= this._chunkSamples) {
      // Oldest valid sample is _ringCount positions behind _writeHead.
      const readHead = (this._writeHead - this._ringCount + this._ringBuf.length)
                       % this._ringBuf.length;

      // Reuse a pooled buffer if one was returned by the main thread;
      // otherwise allocate a fresh one (happens once on the very first emit).
      const outBuffer = this._outBuf
        ? this._outBuf
        : new ArrayBuffer(this._chunkSamples * 2); // Int16 = 2 bytes/sample
      this._outBuf = null; // mark consumed

      const int16 = new Int16Array(outBuffer);
      for (let i = 0; i < this._chunkSamples; i++) {
        const s = Math.max(-1, Math.min(1,
          this._ringBuf[(readHead + i) % this._ringBuf.length]
        ));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      this._ringCount -= this._chunkSamples;

      // Transfer the buffer to the main thread (zero-copy via Transferable).
      this.port.postMessage(int16, [int16.buffer]);
    }

    return true; // returning false would destroy the processor
  }
}

registerProcessor('pcm-processor', PCMProcessor);
`;

/** Build a Blob URL from the worklet source string. Called once per AudioContext. */
function _createWorkletBlobUrl() {
  const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
  return URL.createObjectURL(blob);
}

// --- Hook --------------------------------------------------------------------
/**
 * useAudioCapture
 *
 * A reusable, transport-agnostic hook for capturing microphone audio and
 * delivering 250ms Int16 PCM chunks to the caller via a callback.
 *
 * The hook has NO knowledge of WebSocket, sessions, or networking.
 * All transport decisions belong to the consuming component.
 *
 * Exposed API:
 *   start({ onAudioChunk }) -- begin capture; calls onAudioChunk(ArrayBuffer)
 *                              once per 250ms with Int16 PCM @ 16kHz mono.
 *   stop()                  -- halt capture and release the microphone.
 *   cleanup()               -- full teardown (call from useEffect return).
 *   isCapturing             -- boolean, true while recording is active.
 *   permissionError         -- string | null, non-null when getUserMedia fails.
 *
 * Usage example:
 *   const { start, stop, cleanup, isCapturing, permissionError } = useAudioCapture();
 *
 *   useEffect(() => () => { cleanup(); }, [cleanup]);
 *
 *   const handleStart = () =>
 *     start({ onAudioChunk: (buf) => websocket.send(buf) });
 */
export function useAudioCapture() {

  // --- State ------------------------------------------------------------------
  const [isCapturing,     setIsCapturing]     = useState(false);
  const [permissionError, setPermissionError] = useState(null);

  // --- Refs (survive re-renders without triggering them) ----------------------
  const streamRef       = useRef(null);  // MediaStream from getUserMedia
  const audioContextRef = useRef(null);  // AudioContext (owns sample rate)
  const sourceNodeRef   = useRef(null);  // MediaStreamAudioSourceNode
  const workletNodeRef  = useRef(null);  // AudioWorkletNode (PCM processor)
  const workletBlobUrl  = useRef(null);  // Blob URL for worklet module (revoke on cleanup)
  const pcmBufferRef    = useRef([]);    // Internal Int16Array backlog (no-callback path)
  const onAudioChunkRef = useRef(null);  // Caller's callback: (ArrayBuffer) => void
  // FIX 2: Mutex guard -- prevents concurrent start() calls during the async
  // initialisation window before isCapturing becomes true.
  const isStartingRef   = useRef(false);

  // --- Internal: release mic hardware -----------------------------------------
  const _releaseMicTracks = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        // Only call stop() on tracks that are still live -- avoids a benign
        // but noisy DOMException if stop() is called on an already-ended track.
        if (track.readyState === "live") {
          track.stop();
        }
      });
      streamRef.current = null;
    }
  }, []);

  // --- Internal: disconnect audio graph nodes ----------------------------------
  const _disconnectAudioGraph = useCallback(() => {
    // Disconnect in reverse signal-flow order: worklet first, then source.
    if (workletNodeRef.current) {
      workletNodeRef.current.port.onmessage = null; // stop receiving PCM messages
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    onAudioChunkRef.current = null;  // unregister consumer -- no chunks emitted after stop
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    // Revoke the Blob URL to free memory; a new one is created on next start().
    if (workletBlobUrl.current) {
      URL.revokeObjectURL(workletBlobUrl.current);
      workletBlobUrl.current = null;
    }
    // Drain the PCM queue so stale chunks do not bleed into the next session.
    pcmBufferRef.current = [];
  }, []);

  // --- Internal: close AudioContext --------------------------------------------
  const _closeAudioContext = useCallback(async () => {
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      await audioContextRef.current.close();
    }
    audioContextRef.current = null;
  }, []);

  // (FIX 4: removed _closeWebSocket and _clearChunkTimer -- these referenced
  //  wsRef and chunkIntervalRef which were never defined in this hook, causing
  //  a latent crash risk. WebSocket lifecycle belongs to the consuming component.)

  // --- start({ onAudioChunk }) -------------------------------------------------
  /**
   * Request microphone access and begin audio capture.
   *
   * Each 250ms, the hook converts captured audio to Int16 PCM at 16kHz
   * and calls onAudioChunk(ArrayBuffer). The caller is responsible for
   * all transport (WebSocket.send, MediaRecorder, etc.).
   *
   * Handles all getUserMedia failure modes:
   *   NotAllowedError      -- user dismissed or blocked the permission prompt
   *   NotFoundError        -- no microphone device found on this machine
   *   NotReadableError     -- mic is in use by another application (OS lock)
   *   OverconstrainedError -- requested audio constraints cannot be satisfied
   *   AbortError / other   -- hardware fault or unexpected browser error
   *
   * @param {object}   options
   * @param {Function} [options.onAudioChunk] -- called with each chunk as an
   *   ArrayBuffer (Int16, 16kHz, mono). Suitable for WebSocket.send() directly.
   *   If omitted, chunks queue internally (max 10s) until a callback is set.
   */
  const start = useCallback(async ({ onAudioChunk } = {}) => {
    // FIX 2: Mutex guard -- isCapturing is only set true at the END of the async
    // init sequence, so a fast double-click (or StrictMode double-invoke) would
    // pass the isCapturing check and start two concurrent initialisations.
    // isStartingRef is set synchronously, closing that window.
    if (isCapturing || isStartingRef.current) {
      console.warn("[useAudioCapture] Already capturing or starting. Call stop() first.");
      return;
    }
    isStartingRef.current = true;

    // Register the callback before anything else so the very first chunk
    // delivered by the worklet is not missed.
    onAudioChunkRef.current = typeof onAudioChunk === 'function' ? onAudioChunk : null;

    // Reset any previous error
    setPermissionError(null);

    try {
      // -- Step 1: API availability guard ------------------------------------
      //    navigator.mediaDevices is undefined on: plain HTTP (non-localhost),
      //    sandboxed iframes without allow="microphone", and very old browsers.
      if (!navigator.mediaDevices?.getUserMedia) {
        throw Object.assign(
          new Error("getUserMedia is not available in this browser or context. Use HTTPS or localhost."),
          { name: "APIUnavailableError" }
        );
      }

      // -- Step 2: Request microphone permission -----------------------------
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount:     1,                   // mono -- backend requires mono
          sampleRate:       TARGET_SAMPLE_RATE,  // hint: 16kHz (browser may ignore)
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl:  true,
        },
      });
      streamRef.current = stream;

      const track    = stream.getAudioTracks()[0];
      const settings = track?.getSettings() ?? {};
      console.log(
        `[useAudioCapture] Microphone access granted. ` +
        `Device: "${track?.label || "unknown"}" | ` +
        `Sample rate: ${settings.sampleRate ?? "unknown"}Hz | ` +
        `Channels: ${settings.channelCount ?? "unknown"}`
      );

      // -- Step 3: Create AudioContext at target sample rate -----------------
      //    FIX 1: Close any existing AudioContext before creating a new one.
      //    Without this, calling stop() then start() leaves the old context open.
      //    Browsers cap active contexts at 6-8; exceeding the cap causes
      //    subsequent AudioContext() calls to silently fail or throw.
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        await audioContextRef.current.close();
        audioContextRef.current = null;
      }

      //    We pass sampleRate: 16000 as a hint. Chrome/Firefox honour it on
      //    most hardware. Safari and some mobile browsers may ignore it --
      //    the PCMProcessor handles that with its internal ratio resampler.
      const audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
      audioContextRef.current = audioContext;

      // Browsers auto-suspend AudioContext until a user gesture. start() is
      // always called from a button click, so this resume is typically a no-op,
      // but guard against race conditions in fast double-click scenarios.
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }
      console.log(
        `[useAudioCapture] AudioContext ready. ` +
        `Actual sample rate: ${audioContext.sampleRate}Hz ` +
        `(requested: ${TARGET_SAMPLE_RATE}Hz, ` +
        `resampling ${audioContext.sampleRate !== TARGET_SAMPLE_RATE ? "ACTIVE" : "not needed"})`
      );

      // -- Step 4: Register and connect AudioWorklet -------------------------
      //    FIX 3: Validate AudioWorklet API availability before calling addModule.
      //    audioContext.audioWorklet is undefined in insecure contexts (plain HTTP)
      //    and in certain sandboxed iframes, producing an opaque TypeError without
      //    this guard. We map it to the same APIUnavailableError path.
      if (!audioContext.audioWorklet) {
        throw Object.assign(
          new Error("AudioWorklet is not available in this browser or context. Use HTTPS or localhost."),
          { name: "APIUnavailableError" }
        );
      }

      //    The processor code is compiled from an inline Blob URL to avoid
      //    Vite path issues and MIME-type restrictions on module imports.
      const blobUrl = _createWorkletBlobUrl();
      workletBlobUrl.current = blobUrl;

      await audioContext.audioWorklet.addModule(blobUrl);

      const workletNode = new AudioWorkletNode(audioContext, 'pcm-processor', {
        // Pass constants into the worklet constructor via processorOptions.
        processorOptions: {
          targetRate:   TARGET_SAMPLE_RATE,
          chunkSamples: CHUNK_SAMPLES,
        },
        // Request a single output channel regardless of mic channel count.
        // The processor handles the downmix internally from inputs[0].
        numberOfOutputs: 0, // no audio output -- capture only
      });
      workletNodeRef.current = workletNode;

      // Receive completed 250ms Int16Array PCM chunks from the worklet thread.
      // Deliver each chunk to the caller via onAudioChunk(ArrayBuffer).
      // If no callback is registered, queue chunks internally (max 10s backlog).
      // After delivering, return the empty buffer to the worklet pool.
      workletNode.port.onmessage = (event) => {
        const int16Chunk = event.data;         // Int16Array, 4000 samples @ 16kHz
        const buffer     = int16Chunk.buffer;  // underlying ArrayBuffer (Transferred)

        if (onAudioChunkRef.current) {
          // Callback path -- deliver to caller.
          // The caller must consume the ArrayBuffer synchronously (e.g. ws.send).
          // After delivery, return the empty buffer to the worklet pool so it can
          // be reused on the next emit, avoiding a new 8KB allocation.
          onAudioChunkRef.current(buffer);
          if (workletNodeRef.current) {
            workletNodeRef.current.port.postMessage(buffer, [buffer]);
          }
        } else {
          // No-callback path -- queue internally for later consumption.
          // Cap at 40 chunks (10s) to prevent unbounded memory growth.
          pcmBufferRef.current.push(int16Chunk);
          if (pcmBufferRef.current.length > 40) {
            pcmBufferRef.current.shift();
            console.warn("[useAudioCapture] PCM buffer exceeded 10s -- dropping oldest chunk.");
          }
        }
      };

      // -- Step 5: Connect audio graph ---------------------------------------
      //    Signal flow: mic -> source node -> worklet processor (-> discarded)
      //    The worklet outputs nothing to speakers; it only posts PCM to main.
      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = sourceNode;
      sourceNode.connect(workletNode);

      // -- Step 6: Mark capture as active ------------------------------------
      setIsCapturing(true);
      console.log("[useAudioCapture] Capture started. onAudioChunk:", !!onAudioChunkRef.current ? "registered" : "none (buffering)");

    } catch (err) {
      // -- Map all known DOMException types to user-readable messages --------
      const errorMessages = {
        // User clicked "Block" or "Deny" on the browser permission prompt.
        NotAllowedError:
          "Microphone access was denied. Click the camera icon in your address bar to allow microphone access, then try again.",

        // No microphone device is connected or detectable.
        NotFoundError:
          "No microphone found. Please connect a microphone and try again.",

        // Mic exists but is locked by another app (e.g., a Zoom call, Teams).
        NotReadableError:
          "Microphone is in use by another application. Close other apps using the microphone and try again.",

        // The exact audio constraints (e.g., sampleRate: 16000) could not be satisfied.
        OverconstrainedError:
          "Your microphone does not support the required audio format. TalkSense requires 16kHz mono audio.",

        // getUserMedia or AudioWorklet not available (plain HTTP, sandboxed iframe, old browser).
        APIUnavailableError:
          "Microphone access requires a secure connection (HTTPS or localhost). Please use a supported environment.",

        // Hardware fault, driver crash, or unexpected browser error.
        AbortError:
          "Microphone access was interrupted by a hardware or browser error. Please refresh and try again.",
      };

      const message =
        errorMessages[err?.name] ??
        `Microphone error: ${err?.message ?? "An unknown error occurred."}`;

      console.error(`[useAudioCapture] start() failed (${err?.name}):`, err);
      setPermissionError(message);

      // Tear down any partial resources allocated before the failure
      _disconnectAudioGraph();
      _releaseMicTracks();
      await _closeAudioContext();
    } finally {
      // FIX 2: Always release the mutex, whether init succeeded or failed.
      isStartingRef.current = false;
    }
  }, [isCapturing, _disconnectAudioGraph, _releaseMicTracks, _closeAudioContext]);

  // --- stop() -----------------------------------------------------------------
  /**
   * Halt active audio capture, release the microphone, and unregister the
   * onAudioChunk callback. Does NOT close the AudioContext -- call cleanup()
   * for full teardown.
   */
  const stop = useCallback(() => {
    if (!isCapturing) {
      console.warn("[useAudioCapture] Not currently capturing.");
      return;
    }

    console.log("[useAudioCapture] Stopping capture...");

    _disconnectAudioGraph();
    _releaseMicTracks();

    setIsCapturing(false);
    console.log("[useAudioCapture] Capture stopped.");
  }, [isCapturing, _disconnectAudioGraph, _releaseMicTracks]);

  // --- cleanup() --------------------------------------------------------------
  /**
   * Full resource teardown. Intended for use as a useEffect return value:
   *   useEffect(() => () => { cleanup(); }, [cleanup]);
   *
   * Stops capture, disconnects the audio graph, and closes the AudioContext.
   * Does NOT touch any WebSocket or session state -- those belong to the caller.
   */
  const cleanup = useCallback(async () => {
    console.log("[useAudioCapture] Running full cleanup...");

    _disconnectAudioGraph();
    _releaseMicTracks();
    await _closeAudioContext();

    setIsCapturing(false);
    setPermissionError(null);

    console.log("[useAudioCapture] Cleanup complete.");
  }, [_disconnectAudioGraph, _releaseMicTracks, _closeAudioContext]);

  // --- Exposed API ------------------------------------------------------------
  return {
    start,
    stop,
    cleanup,
    isCapturing,
    permissionError,
  };
}
