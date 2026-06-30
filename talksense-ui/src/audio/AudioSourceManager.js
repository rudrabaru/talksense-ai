

/**
 * AudioSourceManager
 * 
 * Manages the active audio source for the Conversation Engine pipeline.
 * Extensible for future sources like SystemAudioSource or MixedAudioSource.
 */
export class AudioSourceManager {
  constructor() {
    this.activeSource = null;
    this.sources = {}; // Map of id -> AudioSource instance
    this.currentSourceType = null;
  }

  /**
   * Registers a new audio source with the manager.
   * @param {AudioSource} source 
   */
  registerSource(source) {
    if (typeof source.getMetadata !== 'function') {
      throw new Error("AudioSourceManager: source must implement getMetadata()");
    }
    const meta = source.getMetadata();
    this.sources[meta.id] = source;

    // Default to the first registered source if none is selected
    if (!this.currentSourceType) {
      this.currentSourceType = meta.id;
    }
  }

  /**
   * Returns a list of metadata for all registered sources.
   * @returns {Array<{ id: string, displayName: string, description: string, icon: string }>}
   */
  getAvailableSources() {
    return Object.values(this.sources).map(source => source.getMetadata());
  }

  /**
   * Returns the capabilities of a specific registered source.
   * @param {string} sourceId 
   * @returns {{ microphone: boolean, systemAudio: boolean, mixing: boolean, fileInput: boolean }}
   */
  getSourceCapabilities(sourceId) {
    const source = this.sources[sourceId];
    if (!source) throw new Error(`AudioSourceManager: Source '${sourceId}' not found.`);
    return source.getCapabilities();
  }

  /**
   * Initializes the specified audio source type.
   * @param {string} sourceType - 'microphone' (default)
   */
  async initialize(sourceType = null) {
    if (sourceType) {
      this.currentSourceType = sourceType;
    }
    if (!this.currentSourceType) {
      throw new Error("AudioSourceManager: No source registered or selected.");
    }
    this.activeSource = this.sources[this.currentSourceType];
    if (!this.activeSource) {
      throw new Error(`AudioSourceManager: Unsupported source type '${this.currentSourceType}'`);
    }
    await this.activeSource.initialize();
  }

  /**
   * Starts the active audio source.
   * @param {object} options
   * @param {Function} options.onAudioChunk
   */
  async start(options) {
    if (!this.activeSource) {
      await this.initialize(this.currentSourceType);
    }
    await this.activeSource.start(options);
  }

  /**
   * Stops the active audio source.
   */
  stop() {
    if (this.activeSource) {
      this.activeSource.stop();
    }
  }

  /**
   * Returns the runtime status of the active source.
   * @returns {string}
   */
  getActiveSourceStatus() {
    return this.activeSource ? this.activeSource.getStatus() : 'idle';
  }

  /**
   * Returns the runtime health of the active source.
   * @returns {{ status: string, lastFrameTimestamp: number, frameCount: number, droppedFrames: number }|null}
   */
  getActiveSourceHealth() {
    return this.activeSource ? this.activeSource.getHealth() : null;
  }

  /**
   * Cleans up all managed audio sources.
   */
  async destroy() {
    for (const key in this.sources) {
      if (this.sources[key]) {
        await this.sources[key].destroy();
      }
    }
    this.activeSource = null;
  }
}
