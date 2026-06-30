import { useState, useRef, useCallback } from "react";
import { AudioSourceManager } from "../audio/AudioSourceManager";
import { MicrophoneSource } from "../audio/MicrophoneSource";
import { SystemAudioSource } from "../audio/SystemAudioSource";
import { MixedAudioSource } from "../audio/MixedAudioSource";

/**
 * useAudioCapture
 *
 * A reusable, transport-agnostic hook for capturing audio and
 * delivering 250ms Int16 PCM chunks to the caller via a callback.
 *
 * The hook delegates the actual capture lifecycle to the AudioSourceManager,
 * preserving the exact same API signature for consuming components.
 *
 * Exposed API:
 *   start({ onAudioChunk }) -- begin capture; calls onAudioChunk(ArrayBuffer)
 *                              once per 250ms with Int16 PCM @ 16kHz mono.
 *   stop()                  -- halt capture.
 *   cleanup()               -- full teardown (call from useEffect return).
 *   isCapturing             -- boolean, true while recording is active.
 *   permissionError         -- string | null, non-null when capture fails.
 */
export function useAudioCapture() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionError, setPermissionError] = useState(null);

  const [manager] = useState(() => {
    const mgr = new AudioSourceManager();
    mgr.registerSource(new MicrophoneSource());
    mgr.registerSource(new SystemAudioSource());
    mgr.registerSource(new MixedAudioSource());
    return mgr;
  });
  
  const availableSources = manager.getAvailableSources();
  const [selectedSourceType, setSourceType] = useState('microphone');

  const isStartingRef = useRef(false);

  const start = useCallback(async ({ onAudioChunk } = {}) => {
    if (isCapturing || isStartingRef.current) {
      console.warn("[useAudioCapture] Already capturing or starting. Call stop() first.");
      return;
    }
    isStartingRef.current = true;
    setPermissionError(null);

    try {
      // Initialize the chosen source before starting
      await manager.initialize(selectedSourceType);
      
      // AudioSourceManager handles the complexity.
      await manager.start({
        onAudioChunk: (payload) => {
          if (onAudioChunk) onAudioChunk(payload.buffer);
        }
      });
      
      setIsCapturing(true);
      console.log("[useAudioCapture] Capture started via AudioSourceManager.");
    } catch (err) {
      if (err?.name === 'AudioSourceError') {
        setPermissionError(err.message);
        if (err.recommendedAction) {
          console.error(`[useAudioCapture] Action: ${err.recommendedAction}`);
        }
      } else {
        const errorMessages = {
          NotAllowedError:
            "Microphone access was denied. Click the camera icon in your address bar to allow microphone access, then try again.",
          NotFoundError:
            "No microphone found. Please connect a microphone and try again.",
          NotReadableError:
            "Microphone is in use by another application. Close other apps using the microphone and try again.",
          OverconstrainedError:
            "Your microphone does not support the required audio format. TalkSense requires 16kHz mono audio.",
          APIUnavailableError:
            "Microphone access requires a secure connection (HTTPS or localhost). Please use a supported environment.",
          AbortError:
            "Microphone access was interrupted by a hardware or browser error. Please refresh and try again.",
        };

        const message =
          errorMessages[err?.name] ??
          `Audio capture error: ${err?.message ?? "An unknown error occurred."}`;

        console.error(`[useAudioCapture] start() failed (${err?.name}):`, err);
        setPermissionError(message);
      }
      setIsCapturing(false);
    } finally {
      isStartingRef.current = false;
    }
  }, [isCapturing, manager, selectedSourceType]);

  const stop = useCallback(() => {
    if (!isCapturing) {
      console.warn("[useAudioCapture] Not currently capturing.");
      return;
    }
    console.log("[useAudioCapture] Stopping capture...");
    
    manager.stop();
    
    setIsCapturing(false);
    console.log("[useAudioCapture] Capture stopped.");
  }, [isCapturing, manager]);

  const cleanup = useCallback(async () => {
    console.log("[useAudioCapture] Running full cleanup...");
    
    await manager.destroy();
    
    setIsCapturing(false);
    setPermissionError(null);
    console.log("[useAudioCapture] Cleanup complete.");
  }, [manager]);

  return { 
    start, 
    stop, 
    cleanup, 
    isCapturing, 
    permissionError,
    availableSources,
    selectedSourceType,
    setSourceType
  };
}
