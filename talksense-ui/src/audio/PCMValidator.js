/**
 * PCMValidator
 * 
 * A client-side DSP utility to analyze 16-bit Int16Array PCM buffers in real time.
 * Computes RMS, Peak Amplitude, Clipping, and Timing Drift.
 */
export class PCMValidator {
  constructor() {
    this.totalChunks = 0;
    this.totalSamples = 0;
    this.clippingEvents = 0;
    
    this.lastTimestamp = null;
    this.maxTimingDrift = 0;
    this.timingSum = 0;

    this.silenceThreshold = 50; // RMS value below this is considered "silence"
    this.silenceFrames = 0;

    this.peakAmplitudeGlobal = 0;
  }

  /**
   * Analyzes a single Int16 PCM chunk and updates aggregate metrics.
   * @param {ArrayBuffer} buffer - The raw Int16 PCM chunk.
   * @param {number} timestamp - The exact timestamp the chunk was emitted.
   * @returns {object} - Live telemetry for this specific chunk.
   */
  analyzeChunk(buffer, timestamp) {
    const int16 = new Int16Array(buffer);
    const numSamples = int16.length;

    let sumSquares = 0;
    let peakAmplitude = 0;
    let isClipped = false;

    // 1. Amplitude Analysis
    for (let i = 0; i < numSamples; i++) {
      const val = int16[i];
      const absVal = Math.abs(val);
      
      sumSquares += val * val;
      
      if (absVal > peakAmplitude) {
        peakAmplitude = absVal;
      }

      // Detect clipping (saturation at max Int16 limits)
      if (val >= 32767 || val <= -32768) {
        isClipped = true;
      }
    }

    const rms = Math.sqrt(sumSquares / numSamples);
    
    // 2. Global Updates
    if (isClipped) this.clippingEvents++;
    if (peakAmplitude > this.peakAmplitudeGlobal) this.peakAmplitudeGlobal = peakAmplitude;
    if (rms < this.silenceThreshold) this.silenceFrames++;
    
    this.totalChunks++;
    this.totalSamples += numSamples;

    // 3. Timing Analysis (Expected: exactly 250ms per chunk for 16kHz/4000 samples)
    let timingDelta = 0;
    let timingDrift = 0;
    if (this.lastTimestamp) {
      timingDelta = timestamp - this.lastTimestamp;
      // Absolute deviation from expected 250ms
      timingDrift = Math.abs(250 - timingDelta); 
      if (timingDrift > this.maxTimingDrift) {
        this.maxTimingDrift = timingDrift;
      }
      this.timingSum += timingDelta;
    }
    this.lastTimestamp = timestamp;

    return {
      samples: numSamples,
      bytes: buffer.byteLength,
      peakAmplitude,
      rms,
      isClipped,
      isSilent: rms < this.silenceThreshold,
      timingDelta,
      timingDrift
    };
  }

  /**
   * Returns cumulative session telemetry.
   */
  getSessionMetrics() {
    return {
      totalChunks: this.totalChunks,
      totalSamples: this.totalSamples,
      clippingEvents: this.clippingEvents,
      clippingPercentage: this.totalChunks ? ((this.clippingEvents / this.totalChunks) * 100).toFixed(2) : 0,
      silencePercentage: this.totalChunks ? ((this.silenceFrames / this.totalChunks) * 100).toFixed(2) : 0,
      globalPeak: this.peakAmplitudeGlobal,
      maxTimingDriftMs: this.maxTimingDrift,
      avgChunkDurationMs: this.totalChunks > 1 ? (this.timingSum / (this.totalChunks - 1)).toFixed(2) : 0
    };
  }

  reset() {
    this.totalChunks = 0;
    this.totalSamples = 0;
    this.clippingEvents = 0;
    this.lastTimestamp = null;
    this.maxTimingDrift = 0;
    this.timingSum = 0;
    this.silenceFrames = 0;
    this.peakAmplitudeGlobal = 0;
  }
}
