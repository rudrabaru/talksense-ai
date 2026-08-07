import { AudioSource } from './AudioSource';
import { AudioSourceError } from './AudioSourceError';

const TARGET_SAMPLE_RATE  = 16000;
const CHUNK_INTERVAL_MS   = 250;
const CHUNK_SAMPLES       = TARGET_SAMPLE_RATE * (CHUNK_INTERVAL_MS / 1000);

const WORKLET_CODE = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetRate = options.processorOptions.targetRate || 16000;
    this.chunkSamples = options.processorOptions.chunkSamples || 4000;
    
    this.buffer = new Float32Array(this.chunkSamples);
    this.bufferIndex = 0;
    
    this.port.onmessage = (event) => {
      // Re-use Int16Array buffers sent from the main thread
    };
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    
    const channelData = input[0]; 
    
    for (let i = 0; i < channelData.length; i++) {
      this.buffer[this.bufferIndex++] = channelData[i];
      
      if (this.bufferIndex >= this.chunkSamples) {
        this.emitChunk();
        this.bufferIndex = 0;
      }
    }
    
    return true;
  }

  emitChunk() {
    const int16Buffer = new Int16Array(this.chunkSamples);
    for (let i = 0; i < this.chunkSamples; i++) {
      let s = Math.max(-1, Math.min(1, this.buffer[i]));
      int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    this.port.postMessage(int16Buffer, [int16Buffer.buffer]);
  }
}

registerProcessor('pcm-processor', PCMProcessor);
`;

let _cachedWorkletBlobUrl = null;
function _createWorkletBlobUrl() {
  if (!_cachedWorkletBlobUrl) {
    const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
    _cachedWorkletBlobUrl = URL.createObjectURL(blob);
  }
  return _cachedWorkletBlobUrl;
}

export class MixedAudioSource extends AudioSource {
  constructor() {
    super();
    this.micStream = null;
    this.sysStream = null;
    this.audioContext = null;
    this.micNode = null;
    this.sysNode = null;
    this.compressorNode = null;
    this.workletNode = null;
    this.onAudioChunk = null;
    
    this._status = 'idle';
    this._health = {
      frameCount: 0,
      droppedFrames: 0,
      lastFrameTimestamp: 0,
    };
  }

  getMetadata() {
    return {
      id: 'mixed_audio',
      displayName: 'Microphone + System Audio (Meeting Mode)',
      description: 'Capture local microphone and remote meeting participants simultaneously.',
      icon: 'users'
    };
  }

  getCapabilities() {
    return {
      microphone: true,
      systemAudio: true,
      mixing: true,
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
    this._setStatus('ready');
  }

  async start({ onAudioChunk }) {
    this.onAudioChunk = typeof onAudioChunk === 'function' ? onAudioChunk : null;

    try {
      // 1. Capture Microphone (Hardware AEC is critical here)
      this.micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true, // Absolutely mandatory to prevent echo of system audio
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // 2. Capture System Audio (Remote Participants)
      this.sysStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true
      });

      // Drop video track from screen share without terminating the OS session
      const videoTracks = this.sysStream.getVideoTracks();
      videoTracks.forEach(track => { track.enabled = false; });

      const audioTracks = this.sysStream.getAudioTracks();
      if (audioTracks.length === 0) {
        this._releaseTracks();
        throw Object.assign(
          new Error("No audio track was shared. Did you forget to check 'Share Audio'?"),
          { name: "AudioTrackMissingError" }
        );
      }

      // Handle user stopping screen share gracefully
      audioTracks[0].onended = () => {
        this.stop();
      };

      // 3. Create Shared AudioContext
      this.audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      // 4. Setup Graph Mixing Nodes
      this.micNode = this.audioContext.createMediaStreamSource(this.micStream);
      
      // Chromium bug 933677: force Web Audio API to pull from getDisplayMedia
      this._systemAudioSink = new Audio();
      this._systemAudioSink.srcObject = this.sysStream;
      this._systemAudioSink.muted = true;
      this._systemAudioSink.playsInline = true;
      try {
        await this._systemAudioSink.play();
      } catch (err) {
        console.warn("Failed to activate desktop audio stream:", err);
      }
      
      this.sysNode = this.audioContext.createMediaStreamSource(this.sysStream);

      // Dynamics Compressor to prevent clipping when both parties speak loudly
      this.compressorNode = this.audioContext.createDynamicsCompressor();
      this.compressorNode.threshold.value = -24;
      this.compressorNode.knee.value = 30;
      this.compressorNode.ratio.value = 12;
      this.compressorNode.attack.value = 0.003;
      this.compressorNode.release.value = 0.25;

      this.micNode.connect(this.compressorNode);
      this.sysNode.connect(this.compressorNode);

      // 5. Setup Worklet Node
      const workletBlobUrl = _createWorkletBlobUrl();
      await this.audioContext.audioWorklet.addModule(workletBlobUrl);

      this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor', {
        processorOptions: {
          targetRate: TARGET_SAMPLE_RATE,
          chunkSamples: CHUNK_SAMPLES,
        },
        numberOfOutputs: 1, 
      });

      this.compressorNode.connect(this.workletNode);

      // --- MINIMAL ARCHITECTURAL FIX: Prevent branch pruning ---
      // We must route the Worklet to the      // PHASE 16 FIX - Keep graph active but silent
      // Use 0.0001 instead of 0 because Chrome optimizes out exact 0 gain
      // nodes, causing the upstream AudioWorklet to receive zero-filled buffers.
      const silenceGain = this.audioContext.createGain();
      silenceGain.gain.value = 0.0001;
      this.workletNode.connect(silenceGain);
      silenceGain.connect(this.audioContext.destination);
      // ---------------------------------------------------------

      // 6. Handle Chunks
      this.workletNode.port.onmessage = (event) => {
        const int16Chunk = event.data;
        const buffer = int16Chunk.buffer;
        
        const timestamp = Date.now();
        this._health.lastFrameTimestamp = timestamp;
        this._health.frameCount++;

        if (this.onAudioChunk) {
          this.onAudioChunk({ buffer, timestamp, sourceId: 'mixed_audio' });
        }
      };

      this._setStatus('recording');

    } catch (err) {
      this._releaseTracks();
      this._setStatus('error');
      this._handleError(err);
    }
  }

  stop() {
    this._releaseTracks();

    if (this.workletNode) {
      this.workletNode.port.onmessage = null;

      this.workletNode.disconnect();

      this.workletNode = null;
    }
    if (this.micNode) {
      this.micNode.disconnect();
      this.micNode = null;
    }
    if (this.sysNode) {
      this.sysNode.disconnect();
      this.sysNode = null;
    }
    if (this._systemAudioSink) {
      this._systemAudioSink.pause();
      this._systemAudioSink.srcObject = null;
      this._systemAudioSink = null;
    }
    if (this.compressorNode) {
      this.compressorNode.disconnect();
      this.compressorNode = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
      this.audioContext = null;
    }

    this._setStatus('idle');
  }

  _releaseTracks() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(t => t.stop());
      this.micStream = null;
    }
    if (this.sysStream) {
      this.sysStream.getTracks().forEach(t => t.stop());
      this.sysStream = null;
    }
  }

  async destroy() {
    this.stop();
    this._setStatus('destroyed');
  }

  _handleError(err) {
    if (err.name === 'NotAllowedError') {
      throw new AudioSourceError(
        'PERMISSION_DENIED',
        'Permission denied for microphone or system audio.',
        true,
        'Please allow microphone and screen share access in your browser settings.'
      );
    }
    if (err.name === 'AudioTrackMissingError') {
      throw new AudioSourceError(
        'NO_AUDIO_TRACK',
        err.message,
        true,
        'Make sure to check the "Share tab audio" or "Share system audio" checkbox in the browser prompt.'
      );
    }
    throw new AudioSourceError('UNKNOWN_ERROR', err.message);
  }
}
