import logging

logger = logging.getLogger(__name__)


async def analyze_objection_handling(db, session_id: str) -> None:
    """
    Analyzes how the sales rep handled customer objections.
    Calculates objection linkages, response delays, and handling scores.
    """
    try:
        from db import crud

        # 1. Fetch transcript segments
        segments = await crud.get_all_transcript_segments(db, session_id)
        if not segments:
            return

        # 2. Fetch metrics to get objections, speaker roles, and buying signals
        metrics = await crud.get_latest_session_metrics(db, session_id)
        objections_metric = next(
            (m for m in metrics if m.metric_name == "objections"), None
        )
        roles_metric = next(
            (m for m in metrics if m.metric_name == "speaker_roles"), None
        )
        buying_signals_metric = next(
            (m for m in metrics if m.metric_name == "buying_signals"), None
        )

        if not objections_metric or not objections_metric.metric_value:
            return

        roles = (
            roles_metric.metric_value
            if roles_metric and roles_metric.metric_value
            else {}
        )
        if not isinstance(roles, dict):
            roles = {}
        sales_rep_speaker = next(
            (k for k, v in roles.items() if v == "sales_rep"), None
        )
        customer_speaker = next((k for k, v in roles.items() if v == "customer"), None)

        if not sales_rep_speaker:
            logger.warning(
                "objection_handler: No sales rep identified for session %s",
                session_id[:8],
            )
            return

        objections = objections_metric.metric_value
        if not isinstance(objections, list):
            objections = []
        objection_handling_results = []

        buying_signals = (
            buying_signals_metric.metric_value
            if buying_signals_metric and buying_signals_metric.metric_value
            else []
        )
        if not isinstance(buying_signals, list):
            buying_signals = []

        for obj in objections:
            obj_text = obj.get("text", obj) if isinstance(obj, dict) else obj
            category = (
                obj.get("category", "Pricing") if isinstance(obj, dict) else "Pricing"
            )
            keyword = obj.get("keyword", "") if isinstance(obj, dict) else ""

            # Find the segment where this objection was spoken
            obj_segment = next((s for s in segments if obj_text in s.text), None)

            if not obj_segment:
                continue

            # Customer speaker check
            if customer_speaker and obj_segment.speaker_id != customer_speaker:
                continue

            # Find the next segment spoken by the sales rep
            response_segment = None
            for s in segments:
                if (
                    s.start_time >= obj_segment.end_time
                    and s.speaker_id == sales_rep_speaker
                ):
                    response_segment = s
                    break

            if not response_segment:
                # Ignored: No sales response
                objection_handling_results.append(
                    {
                        "objection_text": obj_text,
                        "category": category,
                        "customer_speaker": obj_segment.speaker_id,
                        "sales_rep": sales_rep_speaker,
                        "response_text": None,
                        "response_delay_seconds": None,
                        "status": "ignored",
                        "score": 0.0,
                    }
                )
                continue

            delay = round(response_segment.start_time - obj_segment.end_time, 1)
            resp_text = response_segment.text

            # Scoring Rules
            # Ignored: Delay > 30s
            if delay > 30.0:
                status = "ignored"
                score = 0.0
            else:
                # Check for Resolved: customer buying signal occurs after this response
                has_subsequent_buying_signal = False
                for bs in buying_signals:
                    bs_text = bs.get("text", bs) if isinstance(bs, dict) else bs
                    bs_seg = next(
                        (
                            s
                            for s in segments
                            if bs_text in s.text and s.speaker_id == customer_speaker
                        ),
                        None,
                    )
                    if (
                        bs_seg
                        and bs_seg.start_time > response_segment.end_time
                        and (bs_seg.start_time - response_segment.end_time) <= 60.0
                    ):
                        has_subsequent_buying_signal = True
                        break

                if has_subsequent_buying_signal:
                    status = "resolved"
                    score = 1.0
                else:
                    words = resp_text.split()
                    if len(words) > 10 and (
                        keyword in resp_text.lower()
                        or "price" in resp_text.lower()
                        or "plan" in resp_text.lower()
                        or "offer" in resp_text.lower()
                        or "value" in resp_text.lower()
                        or "cost" in resp_text.lower()
                        or "timeline" in resp_text.lower()
                    ):
                        # Addressed: > 10 words, discusses topic explicitly
                        status = "addressed"
                        score = 0.8
                    else:
                        # Acknowledged
                        status = "acknowledged"
                        score = 0.5

            objection_handling_results.append(
                {
                    "objection_text": obj_text,
                    "category": category,
                    "customer_speaker": obj_segment.speaker_id,
                    "sales_rep": sales_rep_speaker,
                    "response_text": resp_text,
                    "response_delay_seconds": delay,
                    "status": status,
                    "score": score,
                }
            )

        # Save results
        if objection_handling_results:
            await crud.save_session_metrics_batch(
                db,
                session_id,
                [
                    {
                        "metric_name": "objection_handling",
                        "metric_value": objection_handling_results,
                    }
                ],
            )
            logger.info(
                "objection_handler: processed %d objections for %s",
                len(objection_handling_results),
                session_id[:8],
            )

    except Exception as exc:
        logger.error("objection_handler error for session %s: %s", session_id[:8], exc)
