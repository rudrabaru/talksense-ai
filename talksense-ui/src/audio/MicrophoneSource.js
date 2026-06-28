import { AudioSource } from './AudioSource';

const TARGET_SAMPLE_RATE  = 16000;
const CHUNK_INTERVAL_MS   = 250;
const CHUNK_SAMPLES       = TARGET_SAMPLE_RATE * (CHUNK_INTERVAL_MS / 1000);

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

export class MicrophoneSource extends AudioSource {
  constructor() {
    super();
    this.stream = null;
    this.audioContext = null;
    this.sourceNode = null;
    this.workletNode = null;
    this.workletBlobUrl = null;
    this.onAudioChunk = null;
    this.pcmBuffer = [];
  }

  async initialize() {
    // API availability guard
    if (!navigator.mediaDevices?.getUserMedia) {
      throw Object.assign(
        new Error("getUserMedia is not available in this browser or context. Use HTTPS or localhost."),
        { name: "APIUnavailableError" }
      );
    }
    // For microphone, we can just defer actual capture to start() to prevent early permission prompts.
  }

  async start({ onAudioChunk }) {
    this.onAudioChunk = typeof onAudioChunk === 'function' ? onAudioChunk : null;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: TARGET_SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      if (this.audioContext && this.audioContext.state !== "closed") {
        await this.audioContext.close();
      }

      this.audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });

      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      if (!this.audioContext.audioWorklet) {
        throw Object.assign(
          new Error("AudioWorklet is not available in this browser or context. Use HTTPS or localhost."),
          { name: "APIUnavailableError" }
        );
      }

      this.workletBlobUrl = _createWorkletBlobUrl();
      await this.audioContext.audioWorklet.addModule(this.workletBlobUrl);

      this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor', {
        processorOptions: {
          targetRate: TARGET_SAMPLE_RATE,
          chunkSamples: CHUNK_SAMPLES,
        },
        numberOfOutputs: 0, 
      });

      this.workletNode.port.onmessage = (event) => {
        const int16Chunk = event.data;
        const buffer = int16Chunk.buffer;

        if (this.onAudioChunk) {
          this.onAudioChunk(buffer);
          if (this.workletNode) {
            this.workletNode.port.postMessage(buffer, [buffer]);
          }
        } else {
          this.pcmBuffer.push(int16Chunk);
          if (this.pcmBuffer.length > 40) {
            this.pcmBuffer.shift();
            console.warn("[MicrophoneSource] PCM buffer exceeded 10s -- dropping oldest chunk.");
          }
        }
      };

      this.sourceNode = this.audioContext.createMediaStreamSource(this.stream);
      this.sourceNode.connect(this.workletNode);

    } catch (err) {
      this._disconnectAudioGraph();
      this._releaseMicTracks();
      await this._closeAudioContext();
      throw err; // Caller handles DOMExceptions
    }
  }

  stop() {
    this._disconnectAudioGraph();
    this._releaseMicTracks();
  }

  async destroy() {
    this.stop();
    await this._closeAudioContext();
  }

  _releaseMicTracks() {
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
