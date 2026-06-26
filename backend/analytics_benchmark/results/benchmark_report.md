# Analytics Benchmark Report

## Overall Summary
- **Total Datasets Evaluated:** 50
### Aggregate Metrics
| Module | Precision | Recall | F1 Score |
|--------|-----------|--------|----------|
| Action_items | 1.000 | 0.320 | 0.485 |
| Decisions | 1.000 | 1.000 | 1.000 |
| Objections | 0.850 | 1.000 | 0.919 |
| Buying_signals | 1.000 | 1.000 | 1.000 |
| Commitments | 0.857 | 0.766 | 0.809 |
| Sentiment | 1.000 | 1.000 | 1.000 |

## Failure Analysis
### Top Recurring False Positives (Incorrect Extractions)
- **6x**: *"Not planning to switch this quarter."*
- **3x**: *"Let's review the sprint."*
- **3x**: *"I will deploy the auth service."*

### Top Recurring False Negatives (Missed by Engine)
- **7x**: *"handle the API integration"*
- **7x**: *"I am going to handle"*
- **5x**: *"follow up with the design team"*
- **5x**: *"confirm the requirements"*
- **4x**: *"We will release"*

## Detailed Results
### Dataset: `interview_01`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `interview_02`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We decided to write a design doc, which resolved it.* | Expected: *decided to write a design doc*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `interview_03`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `interview_04`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We decided to write a design doc, which resolved it.* | Expected: *decided to write a design doc*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `interview_05`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We decided to write a design doc, which resolved it.* | Expected: *decided to write a design doc*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `interview_06`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `interview_07`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `interview_08`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `interview_09`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We decided to write a design doc, which resolved it.* | Expected: *decided to write a design doc*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `interview_10`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `meeting_01`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_02`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's not delay the bug fix any further.* | Expected: *not delay the bug fix*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_03`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's not delay the bug fix any further.* | Expected: *not delay the bug fix*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_04`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's not delay the bug fix any further.* | Expected: *not delay the bug fix*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_05`
#### Action_items
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will deploy the auth service.* | Expected: *deploy the auth service by Friday*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Great, let's lock the database schema changes.* | Expected: *lock the database schema changes*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.5 (P: 0.333, R: 1.0)
- **TP:** 1, **FP:** 2, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We need to deploy the new auth service by Friday.* | Expected: *I will deploy the auth service*
- **Errors:**
  - 🔴 **FP:** Predicted *Let's review the sprint.* (Rule: Unknown)
  - 🔴 **FP:** Predicted *I will deploy the auth service.* (Rule: Pattern: i will)
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `meeting_06`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_07`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_08`
#### Action_items
- **F1:** 0.5 (P: 1.0, R: 0.333)
- **TP:** 1, **FP:** 0, **FN:** 2
- **True Positives (Matches):**
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *assign the tickets*
- **Errors:**
  - 🟡 **FN:** Missed *follow up with the design team*
  - 🟡 **FN:** Missed *confirm the requirements*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's go with the blue theme.* | Expected: *go with the blue theme*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *First, I'll follow up with the design team.* | Expected: *I'll follow up*
  - Predicted: *I can confirm the requirements with the client.* | Expected: *I can confirm*
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *I will assign*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *3* | Expected: *3*

### Dataset: `meeting_09`
#### Action_items
- **F1:** 0.5 (P: 1.0, R: 0.333)
- **TP:** 1, **FP:** 0, **FN:** 2
- **True Positives (Matches):**
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *assign the tickets*
- **Errors:**
  - 🟡 **FN:** Missed *follow up with the design team*
  - 🟡 **FN:** Missed *confirm the requirements*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's go with the blue theme.* | Expected: *go with the blue theme*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *First, I'll follow up with the design team.* | Expected: *I'll follow up*
  - Predicted: *I can confirm the requirements with the client.* | Expected: *I can confirm*
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *I will assign*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *3* | Expected: *3*

### Dataset: `meeting_10`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's not delay the bug fix any further.* | Expected: *not delay the bug fix*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_11`
#### Action_items
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will deploy the auth service.* | Expected: *deploy the auth service by Friday*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Great, let's lock the database schema changes.* | Expected: *lock the database schema changes*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.5 (P: 0.333, R: 1.0)
- **TP:** 1, **FP:** 2, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We need to deploy the new auth service by Friday.* | Expected: *I will deploy the auth service*
- **Errors:**
  - 🔴 **FP:** Predicted *Let's review the sprint.* (Rule: Unknown)
  - 🔴 **FP:** Predicted *I will deploy the auth service.* (Rule: Pattern: i will)
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `meeting_12`
#### Action_items
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will deploy the auth service.* | Expected: *deploy the auth service by Friday*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Great, let's lock the database schema changes.* | Expected: *lock the database schema changes*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.5 (P: 0.333, R: 1.0)
- **TP:** 1, **FP:** 2, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *We need to deploy the new auth service by Friday.* | Expected: *I will deploy the auth service*
- **Errors:**
  - 🔴 **FP:** Predicted *Let's review the sprint.* (Rule: Unknown)
  - 🔴 **FP:** Predicted *I will deploy the auth service.* (Rule: Pattern: i will)
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `meeting_13`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_14`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_15`
#### Action_items
- **F1:** 0.5 (P: 1.0, R: 0.333)
- **TP:** 1, **FP:** 0, **FN:** 2
- **True Positives (Matches):**
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *assign the tickets*
- **Errors:**
  - 🟡 **FN:** Missed *follow up with the design team*
  - 🟡 **FN:** Missed *confirm the requirements*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's go with the blue theme.* | Expected: *go with the blue theme*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *First, I'll follow up with the design team.* | Expected: *I'll follow up*
  - Predicted: *I can confirm the requirements with the client.* | Expected: *I can confirm*
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *I will assign*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *3* | Expected: *3*

### Dataset: `meeting_16`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's not delay the bug fix any further.* | Expected: *not delay the bug fix*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_17`
#### Action_items
- **F1:** 0.5 (P: 1.0, R: 0.333)
- **TP:** 1, **FP:** 0, **FN:** 2
- **True Positives (Matches):**
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *assign the tickets*
- **Errors:**
  - 🟡 **FN:** Missed *follow up with the design team*
  - 🟡 **FN:** Missed *confirm the requirements*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's go with the blue theme.* | Expected: *go with the blue theme*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *First, I'll follow up with the design team.* | Expected: *I'll follow up*
  - Predicted: *I can confirm the requirements with the client.* | Expected: *I can confirm*
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *I will assign*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *3* | Expected: *3*

### Dataset: `meeting_18`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_19`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *handle the API integration*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Okay, then we decided to let you handle it.* | Expected: *decided to let you handle it*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *I am going to handle*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `meeting_20`
#### Action_items
- **F1:** 0.5 (P: 1.0, R: 0.333)
- **TP:** 1, **FP:** 0, **FN:** 2
- **True Positives (Matches):**
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *assign the tickets*
- **Errors:**
  - 🟡 **FN:** Missed *follow up with the design team*
  - 🟡 **FN:** Missed *confirm the requirements*
#### Decisions
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Let's go with the blue theme.* | Expected: *go with the blue theme*
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *First, I'll follow up with the design team.* | Expected: *I'll follow up*
  - Predicted: *I can confirm the requirements with the client.* | Expected: *I can confirm*
  - Predicted: *I will assign the tickets to the backend team.* | Expected: *I will assign*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *3* | Expected: *3*

### Dataset: `sales_01`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I'm not the decision maker.* | Expected: *not the decision maker*
  - Predicted: *I need to run it by colleagues.* | Expected: *run it by colleagues*
  - Predicted: *Also, it seems a bit expensive right now.* | Expected: *expensive*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_02`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_03`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_04`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_05`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I'm not the decision maker.* | Expected: *not the decision maker*
  - Predicted: *I need to run it by colleagues.* | Expected: *run it by colleagues*
  - Predicted: *Also, it seems a bit expensive right now.* | Expected: *expensive*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_06`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_07`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *right now it doesn't solve our problem.* | Expected: *doesn't solve our problem*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *We will release*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_08`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_09`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_10`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_11`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Buying_signals
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Makes sense.* | Expected: *makes sense*
  - Predicted: *And it fits the budget.* | Expected: *fits the budget*
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I will send the proposal by Monday.* | Expected: *will send the proposal*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *2* | Expected: *2*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_12`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *right now it doesn't solve our problem.* | Expected: *doesn't solve our problem*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *We will release*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_13`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_14`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I'm not the decision maker.* | Expected: *not the decision maker*
  - Predicted: *I need to run it by colleagues.* | Expected: *run it by colleagues*
  - Predicted: *Also, it seems a bit expensive right now.* | Expected: *expensive*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_15`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *right now it doesn't solve our problem.* | Expected: *doesn't solve our problem*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *We will release*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_16`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_17`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_18`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *I'm not the decision maker.* | Expected: *not the decision maker*
  - Predicted: *I need to run it by colleagues.* | Expected: *run it by colleagues*
  - Predicted: *Also, it seems a bit expensive right now.* | Expected: *expensive*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 3, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

### Dataset: `sales_19`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 1, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *right now it doesn't solve our problem.* | Expected: *doesn't solve our problem*
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 1
- **Errors:**
  - 🟡 **FN:** Missed *We will release*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*

### Dataset: `sales_20`
#### Action_items
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Decisions
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Objections
- **F1:** 0.857 (P: 0.75, R: 1.0)
- **TP:** 3, **FP:** 1, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Honestly, we are just exploring.* | Expected: *just exploring*
  - Predicted: *Not planning to switch this quarter.* | Expected: *not planning to switch*
  - Predicted: *Should I circle back later this year?* | Expected: *later this year*
- **Errors:**
  - 🔴 **FP:** Predicted *Not planning to switch this quarter.* (Rule: OBJECTION_KEYWORDS)
#### Buying_signals
- **F1:** 0.0 (P: 0.0, R: 0.0)
- **TP:** 0, **FP:** 0, **FN:** 0
#### Commitments
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 2, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *Should I circle back later this year?* | Expected: *circle back*
  - Predicted: *Yes please do that.* | Expected: *yes please do that*
#### Sentiment
- **F1:** 1.0 (P: 1.0, R: 1.0)
- **TP:** 4, **FP:** 0, **FN:** 0
- **True Positives (Matches):**
  - Predicted: *1* | Expected: *1*
  - Predicted: *1* | Expected: *1*
  - Predicted: *2* | Expected: *2*

