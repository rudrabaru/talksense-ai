# TalkSense AI — Speaker Attribution Benchmark Report

> Generated: 2026-06-26 22:05:29
> Thresholds: F1 >= 0.75, Accuracy >= 80.0%, SCDR >= 70.0%

## Overall Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Average Macro F1 | **0.8141** | 0.75 | PASS |
| Average Accuracy | **84.5%** | 80.0% | PASS |
| Average SCDR | **55.2%** | 70.0% | FAIL |
| Samples Tested | 10 | - | - |
| Total Audio | 969s (16.1 min) | - | - |

> **NOT PRODUCTION READY**

---

## Per-Category Metrics

| Category | Samples | Avg F1 | Avg Accuracy | Avg SCDR | Status |
|----------|---------|--------|-------------|----------|--------|
| 2_speaker | 4 | 0.8328 | 86.4% | 61.7% | FAIL |
| 3_speaker | 2 | 0.9155 | 96.5% | 80.0% | PASS |
| long_form | 2 | 0.9239 | 93.9% | 50.9% | FAIL |
| noisy | 2 | 0.5656 | 59.0% | 21.6% | FAIL |

---

## Per-Sample Metrics

| Sample | Category | Duration | Spk Expected | Spk Detected | F1 | SCDR | Acc | Status |
|--------|----------|----------|-------------|-------------|------|------|------|--------|
| meeting_short | 2_speaker | 32s | 2 | 2 | 0.667 | 33% | 75% | FAIL |
| sales_ambiguous | 2_speaker | 53s | 2 | 2 | 0.903 | 64% | 90% | FAIL |
| sales_good | 2_speaker | 78s | 2 | 2 | 1.000 | 100% | 100% | PASS |
| sales_meeting | 2_speaker | 54s | 2 | 2 | 0.762 | 50% | 80% | FAIL |
| business_meeting | 3_speaker | 70s | 7 | 6 | 0.831 | 60% | 93% | FAIL |
| meeting_clear | 3_speaker | 48s | 3 | 3 | 1.000 | 100% | 100% | PASS |
| business_english_long | long_form | 205s | 2 | 2 | 0.878 | 60% | 90% | FAIL |
| pitch_competition_long | long_form | 349s | 4 | 4 | 0.970 | 42% | 98% | FAIL |
| meeting_messy | noisy | 39s | 3 | 3 | 0.631 | 33% | 62% | FAIL |
| sales_bad | noisy | 42s | 2 | 2 | 0.500 | 10% | 56% | FAIL |
