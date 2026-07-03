# TalkSense AI — Speaker Attribution Benchmark Report

> Generated: 2026-07-03 15:21:30
> Thresholds: F1 >= 0.75, Accuracy >= 80.0%, SCDR >= 70.0%

## Overall Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Average Macro F1 | **0.9248** | 0.75 | PASS |
| Average Accuracy | **91.3%** | 80.0% | PASS |
| Average SCDR | **48.4%** | 70.0% | FAIL |
| Samples Tested | 10 | - | - |
| Total Audio | 969s (16.1 min) | - | - |

> **NOT PRODUCTION READY**

---

## Per-Category Metrics

| Category | Samples | Avg F1 | Avg Accuracy | Avg SCDR | Status |
|----------|---------|--------|-------------|----------|--------|
| 2_speaker | 4 | 0.9405 | 95.0% | 57.2% | FAIL |
| 3_speaker | 2 | 0.9629 | 95.0% | 66.7% | FAIL |
| long_form | 2 | 0.9469 | 96.5% | 39.1% | FAIL |
| noisy | 2 | 0.8334 | 75.0% | 21.6% | FAIL |

---

## Per-Sample Metrics

| Sample | Category | Duration | Spk Expected | Spk Detected | F1 | SCDR | Acc | Status |
|--------|----------|----------|-------------|-------------|------|------|------|--------|
| meeting_short | 2_speaker | 32s | 2 | 2 | 1.000 | 33% | 100% | FAIL |
| sales_ambiguous | 2_speaker | 53s | 2 | 2 | 0.762 | 46% | 80% | FAIL |
| sales_good | 2_speaker | 78s | 2 | 2 | 1.000 | 100% | 100% | PASS |
| sales_meeting | 2_speaker | 54s | 2 | 2 | 1.000 | 50% | 100% | FAIL |
| business_meeting | 3_speaker | 70s | 7 | 6 | 0.926 | 50% | 90% | FAIL |
| meeting_clear | 3_speaker | 48s | 3 | 3 | 1.000 | 83% | 100% | PASS |
| business_english_long | long_form | 205s | 2 | 2 | 0.894 | 20% | 93% | FAIL |
| pitch_competition_long | long_form | 349s | 4 | 4 | 1.000 | 58% | 100% | FAIL |
| meeting_messy | noisy | 39s | 3 | 3 | 1.000 | 33% | 100% | FAIL |
| sales_bad | noisy | 42s | 2 | 2 | 0.667 | 10% | 50% | FAIL |
