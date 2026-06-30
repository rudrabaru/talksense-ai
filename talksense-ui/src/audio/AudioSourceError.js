/**
 * Standardized error model for all TalkSense AI AudioSources.
 */
export class AudioSourceError extends Error {
  /**
   * @param {string} code - e.g., 'PERMISSION_DENIED', 'HARDWARE_MISSING', 'UNSUPPORTED_BROWSER'
   * @param {string} message - Developer/user readable message
   * @param {boolean} recoverable - Whether the system can recover (e.g. by retrying)
   * @param {string} recommendedAction - What the user or system should do
   */
  constructor(code, message, recoverable, recommendedAction) {
    super(message);
    this.name = 'AudioSourceError';
    this.code = code;
    this.recoverable = recoverable;
    this.recommendedAction = recommendedAction;
  }
}
