def analyze_meeting(nlp_input):
    action_items = []
    decisions = []
    blockers = []
    risk_flags = []
    speaker_counts = {}

    total_sentiment = 0
    segment_count = 0

    for segment in nlp_input.get("segments", []):
        speaker = segment.get("speaker", "unknown")
        text = segment.get("text", "")
        sentiment = segment.get("sentiment", 0.0)
        keywords = segment.get("keywords", [])

        # Speaker dominance
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

        total_sentiment += sentiment
        segment_count += 1

        # 1️⃣ Action items detection
        if "action_item" in keywords or "action_items" in keywords or "ownership" in keywords:
            action_items.append(text)

        # 2️⃣ Decision detection
        if "decision_made" in keywords or "priority_set" in keywords:
            decisions.append(text)

        # 3️⃣ Blocker detection
        if "blocker" in keywords or "blocked" in keywords or "dependency" in keywords:
            blockers.append(text)

        # 4️⃣ Risk flags
        if "timeline_risk" in keywords or "risk" in keywords or "concern" in keywords:
            risk_flags.append("timeline_risk")

    # Remove duplicates
    action_items = list(set(action_items))
    decisions = list(set(decisions))
    blockers = list(set(blockers))
    risk_flags = list(set(risk_flags))

    # 5️⃣ Speaker dominance classification
    dominance = {}
    max_speaker_count = max(speaker_counts.values()) if speaker_counts else 0

    for speaker, count in speaker_counts.items():
        if count == max_speaker_count:
            dominance[speaker] = "high"
        elif count >= max_speaker_count / 2:
            dominance[speaker] = "medium"
        else:
            dominance[speaker] = "low"

    # 6️⃣ Meeting quality assessment
    avg_sentiment = total_sentiment / segment_count if segment_count else 0

    if decisions and action_items and avg_sentiment >= 0:
        meeting_quality = "good"
    elif decisions or action_items:
        meeting_quality = "mixed"
    else:
        meeting_quality = "poor"

    return {
        "action_items": action_items,
        "decisions": decisions,
        "blockers": blockers,
        "risk_flags": risk_flags,
        "speaker_dominance": dominance,
        "meeting_quality": meeting_quality
    }
def analyze_sales(nlp_input):
    objections = []
    sentiment_dip = False
    follow_up_action = None

    # Iterate over conversation segments
    for segment in nlp_input.get("segments", []):
        keywords = segment.get("keywords", [])
        sentiment = segment.get("sentiment", 0.0)
        text = segment.get("text", "")

        # 1️⃣ Objection detection
        if "price_objection" in keywords:
            objections.append("pricing")

        # 2️⃣ Sentiment dip detection
        if sentiment <= -0.3:
            sentiment_dip = True

        # 3️⃣ Follow-up / next steps detection
        if "follow_up" in keywords or "next_steps" in keywords:
            follow_up_action = text

    # Remove duplicate objections
    objections = list(set(objections))

    # 4️⃣ Call score calculation (simple & explainable)
    score = 1.0

    if objections:
        score -= 0.2

    if sentiment_dip:
        score -= 0.2

    if follow_up_action:
        score += 0.2

    # Clamp score between 0 and 1
    score = max(0.0, min(score, 1.0))

    return {
        "objections": objections,
        "sentiment_dip": sentiment_dip,
        "call_score": round(score, 2),
        "follow_up": follow_up_action
    }
