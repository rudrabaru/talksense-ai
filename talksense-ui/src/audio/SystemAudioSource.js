import { AudioSource } from './AudioSource';
import { AudioSourceError } from './AudioSourceError';

const TARGET_SAMPLE_RATE  = 16000;
const CHUNK_INTERVAL_MS   = 250;
const CHUNK_SAMPLES       = TARGET_SAMPLE_RATE * (CHUNK_INTERVAL_MS / 1000);

// We reuse the exact same PCM processor logic as MicrophoneSource
const WORKLET_CODE = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this._inputRate    = sampleRate;
    this._targetRate   = options.processorOptions.targetRate;
    this._ratio        = this._inputRate / this._targetRate;
    this._chunkSamples = options.processorOptions.chunkSamples;

    this._monoBuffer      = new Float32Array(128); 
    this._resampledBuffer = new Float32Array(128); 

    const ringSize  = this._chunkSamples * 2;
    this._ringBuf   = new Float32Array(ringSize);
    this._ringCount = 0;
    this._writeHead = 0;

    this._nextInputTime = 0.0;
    this._lastSample    = 0.0;

    this._outBuf = null;
    this.port.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer &&
          ev.data.byteLength >= this._chunkSamples * 2) {
        this._outBuf = ev.data; 
      }
    };
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const numChannels = input.length;
    const numSamples  = input[0].length; 

    let mono;
    if (numChannels === 1) {
      mono = input[0]; 
    } else {
      mono = this._monoBuffer;
      for (let i = 0; i < numSamples; i++) {
        let sum = 0;
        for (let ch = 0; ch < numChannels; ch++) sum += input[ch][i];
        mono[i] = sum / numChannels;
      }
    }

    let outCount = 0;

    if (this._ratio === 1.0) {
      this._resampledBuffer.set(mono, 0);
      outCount = numSamples;
      this._nextInputTime = 0.0; 
    } else {
      let t = this._nextInputTime; 
      while (t < numSamples) {
        let sample;
        if (t < 0) {
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
      this._nextInputTime = t - numSamples;
    }

    this._lastSample = mono[numSamples - 1];

    for (let i = 0; i < outCount; i++) {
      this._ringBuf[this._writeHead] = this._resampledBuffer[i];
      this._writeHead = (this._writeHead + 1) % this._ringBuf.length;
      this._ringCount++;
    }

    while (this._ringCount >= this._chunkSamples) {
      const readHead = (this._writeHead - this._ringCount + this._ringBuf.length)
                       % this._ringBuf.length;

      const outBuffer = this._outBuf
        ? this._outBuf
        : new ArrayBuffer(this._chunkSamples * 2); 
      this._outBuf = null; 

      const int16 = new Int16Array(outBuffer);
      for (let i = 0; i < this._chunkSamples; i++) {
        const s = Math.max(-1, Math.min(1,
          this._ringBuf[(readHead + i) % this._ringBuf.length]
        ));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      this._ringCount -= this._chunkSamples;

      this.port.postMessage(int16, [int16.buffer]);
    }

    return true; 
  }
}

registerProcessor('pcm-processor', PCMProcessor);
`;

function _createWorkletBlobUrl() {
  const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
  return URL.createObjectURL(blob);
}

export class SystemAudioSource extends AudioSource {
  constructor() {
    super();
    this.stream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.workletBlobUrl = null;
    this.onAudioChunk = null;
    this.pcmBuffer = [];

    this._status = 'idle';
    this._health = {
      status: 'idle',
      lastFrameTimestamp: 0,
      frameCount: 0,
      droppedFrames: 0
    };
  }

  async checkAvailability() {
    const isSupported = typeof navigator?.mediaDevices?.getDisplayMedia === 'function';
    return {
      available: isSupported,
      reason: isSupported ? null : 'getDisplayMedia is not supported by this browser.',
      recommendedAction: isSupported ? null : 'Use Chrome or Edge to capture system audio.'
    };
  }

  getMetadata() {
    return {
      id: 'system_audio',
      displayName: 'System Audio',
      description: 'Capture audio from a browser tab or the system.',
      icon: 'monitor'
    };
  }

  getCapabilities() {
    return {
      microphone: false,
      systemAudio: true,
      mixing: false,
      fileInput: false
    };
  }

  getStatus() {
    return this._status;
  }

  getHealth() {
    return { ...this._health, status: this._status };
  }

  _setStatus(newStatus) {
    this._status = newStatus;
  }

  async initialize() {
    this._setStatus('initializing');
    const { available, reason, recommendedAction } = await this.checkAvailability();
    if (!available) {
      this._setStatus('error');
      throw new AudioSourceError('UNSUPPORTED_BROWSER', reason, false, recommendedAction);
    }
    this._setStatus('ready');
  }

  async start({ onAudioChunk }) {
    this.onAudioChunk = typeof onAudioChunk === 'function' ? onAudioChunk : null;

    try {
      // Chrome requires requesting video alongside audio.
      this.stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true
      });

      // Immediately discard the video track. We only want audio.
      const videoTracks = this.stream.getVideoTracks();
      videoTracks.forEach(track => track.stop());

      // Ensure we actually got an audio track (user might not have checked the 'Share Audio' box)
      const audioTracks = this.stream.getAudioTracks();
      if (audioTracks.length === 0) {
        // Stop the stream entirely since it's useless to us
        this._releaseTracks();
        throw Object.assign(
          new Error("No audio track was shared. Did you forget to check 'Share Audio'?"),
          { name: "AudioTrackMissingError" }
        );
      }

      // If the user stops sharing via the browser UI bar, we need to handle that.
      audioTracks[0].onended = () => {
        this.stop();
      };

      if (this.audioContext && this.audioContext.state !== "closed") {
        await this.audioContext.close();
      }

      this.audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });

      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      if (!this.audioContext.audioWorklet) {
        throw new AudioSourceError(
          'UNSUPPORTED_BROWSER',
          "AudioWorklet is not available in this browser or context.",
          false,
          "Use a secure context (HTTPS) or localhost."
        );
      }

      this.workletBlobUrl = _createWorkletBlobUrl();
      await this.audioContext.audioWorklet.addModule(this.workletBlobUrl);

      this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor', {
        processorOptions: {
          targetRate: TARGET_SAMPLE_RATE,
          chunkSamples: CHUNK_SAMPLES,
        },
        numberOfOutputs: 1, 
      });

      this.workletNode.port.onmessage = (event) => {
        const int16Chunk = event.data;
        const buffer = int16Chunk.buffer;
        
        const timestamp = Date.now();
        this._health.lastFrameTimestamp = timestamp;
        this._health.frameCount++;

        if (this.onAudioChunk) {
          this.onAudioChunk({ buffer, timestamp, sourceId: 'system_audio' });
          if (this.workletNode) {
            this.workletNode.port.postMessage(buffer, [buffer]);
          }
        } else {
          this.pcmBuffer.push(int16Chunk);
          if (this.pcmBuffer.length > 40) {
            this.pcmBuffer.shift();
            this._health.droppedFrames++;
            console.warn("[SystemAudioSource] PCM buffer exceeded 10s -- dropping oldest chunk.");
          }
        }
      };

      this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
      this.sourceNode.connect(this.workletNode);

      // --- MINIMAL ARCHITECTURAL FIX: Prevent branch pruning ---
      const silenceGain = this.audioContext.createGain();
      silenceGain.gain.value = 0.0001;
      this.workletNode.connect(silenceGain);
      silenceGain.connect(this.audioContext.destination);
      // ---------------------------------------------------------

      this._setStatus('recording');

    } catch (err) {
      this._setStatus('error');
      this._disconnectAudioGraph();
      this._releaseTracks();
      await this._closeAudioContext();
      
      if (err instanceof AudioSourceError) {
        throw err;
      }
      
      let code = 'UNKNOWN_ERROR';
      let message = err.message || 'Failed to capture system audio.';
      let recoverable = false;
      let recommendedAction = 'Try sharing a specific tab and ensure "Share Audio" is checked.';

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        code = 'PERMISSION_DENIED';
        message = 'Screen share permission was denied or cancelled.';
        recommendedAction = 'Please grant permission to capture your screen/tab.';
      } else if (err.name === 'AudioTrackMissingError') {
        code = 'NO_AUDIO_TRACK';
        message = err.message;
        recoverable = true;
        recommendedAction = 'Make sure to check the "Share tab audio" or "Share system audio" checkbox in the browser prompt.';
      } else if (err.name === 'NotSupportedError') {
        code = 'UNSUPPORTED_BROWSER';
        message = 'System audio capture is not supported by your browser environment.';
        recommendedAction = 'Please use a modern browser (Chrome, Edge) on a desktop OS.';
      }

      throw new AudioSourceError(code, message, recoverable, recommendedAction);
    }
  }

  stop() {
    this._disconnectAudioGraph();
    this._releaseTracks();
    this._setStatus('stopped');
  }

  async destroy() {
    this.stop();
    await this._closeAudioContext();
    this._setStatus('destroyed');
  }

  _releaseTracks() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => {
        if (track.readyState === "live") {
          track.stop();
        }
      });
      this.stream = null;
    }
  }

  _disconnectAudioGraph() {
    if (this.workletNode) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    this.onAudioChunk = null;
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.workletBlobUrl) {
      URL.revokeObjectURL(this.workletBlobUrl);
      this.workletBlobUrl = null;
    }
    this.pcmBuffer = [];
  }

  async _closeAudioContext() {
    if (this.audioContext && this.audioContext.state !== "closed") {
      await this.audioContext.close();
    }
    this.audioContext = null;
  }
}
