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
   * @param {Function} options.onAudioChunk - Callback receiving Int16Array or ArrayBuffer PCM chunks
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
}
