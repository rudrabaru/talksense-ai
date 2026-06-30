import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AudioSourceManager } from '../audio/AudioSourceManager';
import { SystemAudioSource } from '../audio/SystemAudioSource';
import { MicrophoneSource } from '../audio/MicrophoneSource';
import { PCMValidator } from '../audio/PCMValidator';

export default function SystemAudioTester() {
  const [manager] = useState(() => {
    const mgr = new AudioSourceManager();
    mgr.registerSource(new SystemAudioSource());
    mgr.registerSource(new MicrophoneSource());
    return mgr;
  });

  const [validator] = useState(() => new PCMValidator());

  const [sourceType, setSourceType] = useState('system_audio');
  const [status, setStatus] = useState('idle');
  const [health, setHealth] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  
  // Live PCM Telemetry
  const [liveChunk, setLiveChunk] = useState(null);
  const [sessionMetrics, setSessionMetrics] = useState(null);

  const monitorIntervalRef = useRef(null);

  const onAudioChunk = useCallback((payload) => {
    // payload: { buffer, timestamp, sourceId }
    const chunkMetrics = validator.analyzeChunk(payload.buffer, payload.timestamp);
    setLiveChunk(chunkMetrics);
  }, [validator]);

  const updateStats = useCallback(() => {
    setStatus(manager.getActiveSourceStatus());
    setHealth(manager.getActiveSourceHealth());
    setSessionMetrics(validator.getSessionMetrics());
  }, [manager, validator]);

  const startCapture = async () => {
    setErrorMsg(null);
    validator.reset();
    setLiveChunk(null);
    setSessionMetrics(null);

    try {
      await manager.initialize(sourceType);
      await manager.start({ onAudioChunk });
      
      setIsCapturing(true);
      monitorIntervalRef.current = setInterval(updateStats, 200);
    } catch (err) {
      console.error(err);
      setErrorMsg(`${err.code || 'ERROR'}: ${err.message}\nAction: ${err.recommendedAction}`);
    } finally {
      updateStats();
    }
  };

  const stopCapture = () => {
    manager.stop();
    setIsCapturing(false);
    setLiveChunk(null);
    if (monitorIntervalRef.current) {
      clearInterval(monitorIntervalRef.current);
      monitorIntervalRef.current = null;
    }
    updateStats();
  };

  useEffect(() => {
    return () => {
      manager.destroy();
      if (monitorIntervalRef.current) clearInterval(monitorIntervalRef.current);
    };
  }, [manager]);

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      <h1>System Audio Source Tester</h1>
      <p style={{ color: '#666' }}>
        This is a developer-only panel to validate capturing system/tab audio in isolation.
        No data is sent to the backend or Conversation Engine.
      </p>

      {errorMsg && (
        <div style={{ padding: '1rem', background: '#fee', color: '#c00', borderRadius: '4px', marginBottom: '1rem', whiteSpace: 'pre-wrap' }}>
          <strong>Error:</strong><br />{errorMsg}
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'center' }}>
        <select 
          value={sourceType} 
          onChange={(e) => setSourceType(e.target.value)}
          disabled={isCapturing}
          style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="system_audio">System Audio</option>
          <option value="microphone">Microphone</option>
        </select>
        <button 
          onClick={startCapture} 
          disabled={isCapturing}
          style={{ padding: '0.5rem 1rem', background: isCapturing ? '#ccc' : '#0066cc', color: 'white', border: 'none', borderRadius: '4px', cursor: isCapturing ? 'not-allowed' : 'pointer' }}
        >
          Start Capture
        </button>
        <button 
          onClick={stopCapture} 
          disabled={!isCapturing}
          style={{ padding: '0.5rem 1rem', background: !isCapturing ? '#ccc' : '#cc0000', color: 'white', border: 'none', borderRadius: '4px', cursor: !isCapturing ? 'not-allowed' : 'pointer' }}
        >
          Stop Capture
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div style={{ background: '#f5f5f5', padding: '1.5rem', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Runtime Status</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, lineHeight: '1.6' }}>
            <li><strong>Current Source:</strong> {sourceType}</li>
            <li><strong>Status:</strong> {status}</li>
            <li><strong>Audio Activity:</strong> 
              <div style={{ display: 'inline-block', width: '100px', height: '10px', background: '#ddd', marginLeft: '10px', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ width: `${Math.min(100, (liveChunk?.rms || 0) / 100)}%`, height: '100%', background: liveChunk?.isClipped ? '#f44336' : '#4caf50', transition: 'width 0.1s' }}></div>
              </div>
            </li>
            <li><strong>Frame Count:</strong> {health?.frameCount || 0}</li>
            <li><strong>Dropped Frames:</strong> {health?.droppedFrames || 0}</li>
            <li><strong>Sample Rate:</strong> 16000 Hz Mono Int16</li>
          </ul>
        </div>

        <div style={{ background: '#e3f2fd', padding: '1.5rem', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>Live PCM Telemetry (250ms Chunk)</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, lineHeight: '1.6' }}>
            <li><strong>Bytes:</strong> {liveChunk?.bytes || 0} (Samples: {liveChunk?.samples || 0})</li>
            <li><strong>RMS:</strong> {liveChunk?.rms?.toFixed(2) || 0} {liveChunk?.isSilent ? '(SILENT)' : ''}</li>
            <li><strong>Peak Amplitude:</strong> {liveChunk?.peakAmplitude || 0} / 32768</li>
            <li><strong>Clipping:</strong> {liveChunk?.isClipped ? <span style={{color: 'red', fontWeight: 'bold'}}>YES</span> : 'No'}</li>
            <li><strong>Timing Delta:</strong> {liveChunk?.timingDelta || 0} ms</li>
            <li><strong>Timing Drift:</strong> {liveChunk?.timingDrift || 0} ms</li>
          </ul>
        </div>
      </div>

      <div style={{ background: '#fff3e0', padding: '1.5rem', borderRadius: '8px', marginTop: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>Session Analytics</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, lineHeight: '1.6', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <li><strong>Total Chunks:</strong> {sessionMetrics?.totalChunks || 0}</li>
          <li><strong>Avg Duration:</strong> {sessionMetrics?.avgChunkDurationMs || 0} ms</li>
          <li><strong>Max Timing Drift:</strong> {sessionMetrics?.maxTimingDriftMs || 0} ms</li>
          <li><strong>Clipping Rate:</strong> {sessionMetrics?.clippingPercentage || 0}%</li>
          <li><strong>Silence Rate:</strong> {sessionMetrics?.silencePercentage || 0}%</li>
          <li><strong>Global Peak:</strong> {sessionMetrics?.globalPeak || 0}</li>
        </ul>
      </div>
    </div>
  );
}
