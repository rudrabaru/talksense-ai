import { MicrophoneSource } from './MicrophoneSource';

/**
 * AudioSourceManager
 * 
 * Manages the active audio source for the Conversation Engine pipeline.
 * Extensible for future sources like SystemAudioSource or MixedAudioSource.
 */
export class AudioSourceManager {
  constructor() {
    this.activeSource = null;
    this.sources = {
      microphone: new MicrophoneSource(),
      // system: new SystemAudioSource(), // Phase 2
      // mixed: new MixedAudioSource(),   // Phase 2
      // file: new FileAudioSource(),     // Phase 2
    };
    this.currentSourceType = 'microphone';
  }

  /**
   * Initializes the specified audio source type.
   * @param {string} sourceType - 'microphone' (default)
   */
  async initialize(sourceType = 'microphone') {
    this.currentSourceType = sourceType;
    this.activeSource = this.sources[sourceType];
    if (!this.activeSource) {
      throw new Error(`AudioSourceManager: Unsupported source type '${sourceType}'`);
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
      await this.initialize('microphone');
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
