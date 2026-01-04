import json
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "keywords.json")

# Default Fallback (Critical Safety)
DEFAULT_KEYWORDS = {
    "meeting": {
        "decisions": ["we will", "let's", "agreed", "decided", "finalize"],
        "actions": ["please", "can you", "need to", "will handle"]
    },
    "sales": {
        "objections": {
            "Pricing": ["price", "cost"]
        },
        "buying_signals": ["sounds good", "interested"]
    },
    "nlp_enrichment": {
        "action_item": ["action item"],
        "decision_made": ["decision"]
    }
}

def load_keywords():
    """
    Loads keywords from JSON config file.
    Returns default dictionary if file is missing or invalid.
    """
    if not os.path.exists(CONFIG_PATH):
        logger.warning(f"Config file not found at {CONFIG_PATH}. Using defaults.")
        return DEFAULT_KEYWORDS

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info("Keywords configuration loaded successfully.")
            return data
    except Exception as e:
        logger.error(f"Failed to load keyword config: {e}. Using defaults.")
        return DEFAULT_KEYWORDS

# Singleton-like access
KEYWORDS_CONFIG = load_keywords()

