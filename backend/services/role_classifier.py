import json
import logging

from db import crud
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── V1 Heuristic Classifier ──────────────────────────────────────────────────

SALES_INDICATORS = [
    "thanks for joining",
    "let me show you",
    "our platform",
    "our product",
    "our solution",
    "demo",
    "pricing plans",
    "implementation",
    "onboarding",
    "customers use",
    "we provide",
    "let me explain",
]

CUSTOMER_INDICATORS = [
    "budget",
    "pricing",
    "how much",
    "interested",
    "can it",
    "does it",
    "we currently",
    "our team",
    "our process",
    "concern",
    "problem",
    "challenge",
]


async def classify_roles(session_id: str) -> dict[str, str]:
    """
    V1 heuristic role classifier. Retained as fallback for v2.
    Classify speakers as 'sales_rep' or 'customer' using simple keyword matching.
    """
    logger.info(
        "role_classifier — session %s: starting v1 classification", session_id[:8]
    )

    async with AsyncSessionLocal() as db:
        segments = await crud.get_all_transcript_segments(db, session_id)

    if not segments:
        logger.warning(
            "role_classifier — session %s: no segments found", session_id[:8]
        )
        return {}

    speaker_scores = {}

    for seg in segments:
        speaker = seg.speaker_id or "Unknown"
        if speaker == "Unknown":
            continue

        text = (seg.text or "").lower()

        if speaker not in speaker_scores:
            speaker_scores[speaker] = {"sales": 0, "customer": 0}

        for kw in SALES_INDICATORS:
            if kw in text:
                speaker_scores[speaker]["sales"] += 1

        for kw in CUSTOMER_INDICATORS:
            if kw in text:
                speaker_scores[speaker]["customer"] += 1

    if not speaker_scores:
        return {}

    sorted_speakers = sorted(
        speaker_scores.keys(),
        key=lambda s: (speaker_scores[s]["sales"], -speaker_scores[s]["customer"]),
        reverse=True,
    )

    sales_rep = sorted_speakers[0] if sorted_speakers else None

    roles = {}
    for spk in speaker_scores.keys():
        if spk == sales_rep:
            roles[spk] = "sales_rep"
        else:
            roles[spk] = "customer"

    logger.info(
        "role_classifier — session %s: v1 classified roles -> %s", session_id[:8], roles
    )
    return roles


# ── V2 LLM Classifier (Gemini Flash) ─────────────────────────────────────────

ROLE_CLASSIFICATION_PROMPT = (
    "You are an expert conversation analyst for a sales intelligence platform "
    "called TalkSense AI.\n"
    "\n"
    "You are given a transcript of a conversation between two speakers. "
    "Your task is to determine which speaker is the **Sales Representative** "
    "and which is the **Customer**.\n"
    "\n"
    "## Speaker Transcripts\n"
    "\n"
    "{speaker_transcripts}\n"
    "\n"
    "## Instructions\n"
    "\n"
    "1. Analyze the conversational patterns, language, and intent of each speaker.\n"
    "2. The Sales Representative typically:\n"
    "   - Presents products, features, or solutions\n"
    "   - Asks discovery/qualification questions\n"
    "   - Handles objections\n"
    "   - Proposes next steps or follow-ups\n"
    '   - Uses company-specific language ("our platform", "we offer")\n'
    "\n"
    "3. The Customer typically:\n"
    "   - Asks questions about the product/service\n"
    "   - Raises concerns or objections\n"
    "   - Describes their current situation or pain points\n"
    "   - Discusses budget, timeline, or decision-making process\n"
    "   - Evaluates the offering\n"
    "\n"
    "4. If the conversation is ambiguous or does not clearly fit a sales context, "
    "make your best judgment based on who is presenting/offering vs who is "
    "evaluating/asking.\n"
    "\n"
    "## Output Format\n"
    "\n"
    "Return a JSON object with exactly this structure:\n"
    "{{\n"
    '  "roles": {{\n'
    '    "<speaker_name>": "sales_rep",\n'
    '    "<speaker_name>": "customer"\n'
    "  }},\n"
    '  "confidence": <float between 0.0 and 1.0>,\n'
    '  "reasoning": {{\n'
    '    "<speaker_name>": "<brief explanation>",\n'
    '    "<speaker_name>": "<brief explanation>"\n'
    "  }}\n"
    "}}\n"
    "\n"
    "Return ONLY the JSON object, no other text.\n"
)


async def classify_roles_v2(session_id: str) -> dict | None:
    """
    V2 LLM-based role classifier using Gemini Flash.

    Returns:
        {
            "roles": {"Speaker 1": "sales_rep", "Speaker 2": "customer"},
            "confidence": 0.0-1.0,
            "reasoning": {"Speaker 1": "...", "Speaker 2": "..."}
        }
        or None if the LLM call fails.
    """
    logger.info(
        "role_classifier — session %s: starting v2 (Gemini) classification",
        session_id[:8],
    )

    try:
        from core.config import get_settings

        settings = get_settings()

        if not settings.gemini_api_key:
            logger.warning(
                "role_classifier — session %s: GEMINI_API_KEY not configured, skipping v2",  # noqa: E501
                session_id[:8],
            )
            return None

        # 1. Fetch transcript segments
        async with AsyncSessionLocal() as db:
            segments = await crud.get_all_transcript_segments(db, session_id)

        if not segments:
            logger.warning(
                "role_classifier — session %s: no segments for v2", session_id[:8]
            )
            return None

        # 2. Group text by speaker
        speaker_texts: dict[str, list[str]] = {}
        for seg in segments:
            speaker = seg.speaker_id or "Unknown"
            if speaker == "Unknown":
                continue
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            if seg.text and seg.text.strip():
                speaker_texts[speaker].append(seg.text.strip())

        if len(speaker_texts) < 2:
            logger.warning(
                "role_classifier — session %s: fewer than 2 speakers for v2",
                session_id[:8],
            )
            return None

        # 3. Build prompt with speaker transcripts
        transcript_parts = []
        for speaker, texts in sorted(speaker_texts.items()):
            # Take up to 30 segments per speaker to keep prompt manageable
            sample = texts[:30]
            joined = "\n".join(f'  "{t}"' for t in sample)
            transcript_parts.append(f"### {speaker}\n{joined}")

        speaker_transcripts = "\n\n".join(transcript_parts)
        prompt = ROLE_CLASSIFICATION_PROMPT.format(
            speaker_transcripts=speaker_transcripts
        )

        # 4. Call Gemini Flash
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
        )

        raw_text = response.text.strip()
        logger.info(
            "role_classifier — session %s: Gemini raw response: %s",
            session_id[:8],
            raw_text[:200],
        )

        # 5. Parse JSON response
        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [line for line in lines if not line.strip().startswith("```")]
            raw_text = "\n".join(lines)

        result = json.loads(raw_text)

        # Validate structure
        if "roles" not in result:
            logger.error(
                "role_classifier — session %s: v2 response missing 'roles' key",
                session_id[:8],
            )
            return None

        # Ensure confidence is present
        if "confidence" not in result:
            result["confidence"] = 0.5

        if "reasoning" not in result:
            result["reasoning"] = {}

        # Clamp confidence
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

        logger.info(
            "role_classifier — session %s: v2 classified roles -> %s (confidence=%.2f)",
            session_id[:8],
            result["roles"],
            result["confidence"],
        )
        return result

    except json.JSONDecodeError as e:
        logger.error(
            "role_classifier — session %s: v2 JSON parse error: %s", session_id[:8], e
        )
        return None
    except Exception as e:
        logger.error(
            "role_classifier — session %s: v2 Gemini call failed: %s", session_id[:8], e
        )
        return None
