/**
 * AudioSource
 * 
 * Abstract base class for all TalkSense AI audio sources.
 * Defines the contract that all audio sources must implement to be compatible
 * with the Conversation Engine pipeline.
 */
export class AudioSource {
  /**
   * Initializes the audio source (e.g., requests permissions, captures streams).
   * @returns {Promise<void>}
   */
  async initialize() {
    throw new Error("AudioSource: initialize() must be implemented by subclass.");
  }

  /**
   * Starts capturing and processing audio, emitting PCM chunks via the callback.
   * @param {object} options
   * @param {Function} options.onAudioChunk - Callback receiving { buffer: ArrayBuffer, timestamp: number, sourceId: string }
   * @returns {Promise<void>}
   */
  // eslint-disable-next-line no-unused-vars
  async start(options) {
    throw new Error("AudioSource: start() must be implemented by subclass.");
  }

  /**
   * Stops the active audio capture and processing.
   * Keeps resources alive so that start() can be called again.
   * @returns {void}
   */
  stop() {
    throw new Error("AudioSource: stop() must be implemented by subclass.");
  }

  /**
   * Destroys the audio source, releasing all hardware and memory resources.
   * The instance cannot be reused after this is called.
   * @returns {void}
   */
  destroy() {
    throw new Error("AudioSource: destroy() must be implemented by subclass.");
  }

  /**
   * Returns metadata about the audio source.
   * @returns {{ id: string, displayName: string, description: string, icon: string }}
   */
  getMetadata() {
    throw new Error("AudioSource: getMetadata() must be implemented by subclass.");
  }

  /**
   * Returns the capabilities of the audio source.
   * @returns {{ microphone: boolean, systemAudio: boolean, mixing: boolean, fileInput: boolean }}
   */
  getCapabilities() {
    throw new Error("AudioSource: getCapabilities() must be implemented by subclass.");
  }

  /**
   * Checks if this source is currently available for use (runtime availability).
   * @returns {Promise<{ available: boolean, reason: string | null, recommendedAction: string | null }>}
   */
  async checkAvailability() {
    throw new Error("AudioSource: checkAvailability() must be implemented by subclass.");
  }

  /**
   * Returns the current runtime status of the audio source.
   * @returns {string} - 'idle', 'initializing', 'ready', 'recording', 'paused', 'stopped', 'error', 'destroyed'
   */
  getStatus() {
    throw new Error("AudioSource: getStatus() must be implemented by subclass.");
  }

  /**
   * Returns lightweight runtime health telemetry for the source.
   * @returns {{ status: string, lastFrameTimestamp: number, frameCount: number, droppedFrames: number }}
   */
  getHealth() {
    throw new Error("AudioSource: getHealth() must be implemented by subclass.");
  }
}
