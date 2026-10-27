# DIAGNEX: Project Synopsis

## Overview

Diagnex is a research prototype for medical visual question answering. A user uploads a still image and asks a question; the model can answer or abstain using a traffic-light policy. Its responses are not medical diagnoses and require review by a qualified clinician.

## Implementation

- **Frontend:** React and Vite with image upload, chat, traffic-light result, and PDF report export.
- **Backend:** FastAPI endpoints for upload, follow-up questions, health, taxonomy, and aggregate counters. Supported still-image inputs include PNG, JPEG, TIFF, and DICOM. Session images are kept in a capped in-memory store for 30 minutes.
- **Model:** Frozen BiomedCLIP image and text encoders, TF-IDF question features, and a trained answer-classification fusion head. This is not the DenseNet + ViT + BioClinicalBERT CrossGate architecture proposed in the source material.
- **Data:** 41,908 question-answer pairs and 5,244 images from public VQA-RAD, SLAKE, and PathVQA datasets. The current split is image-disjoint within and across datasets.
- **Safety policy:** Temperature scaling, confidence thresholds, and an experimental 12-class error predictor trained from rule-derived labels. The predictor is not a validated clinical risk score. Red-zone answers are withheld from the API response.

The saved model artifacts are loaded at startup; normal backend use does not retrain the model. No database is needed for the anonymous, short-lived local prototype. Accounts, saved reports, or clinical audit records would require a database and a patient-data handling design.

## Held-out evaluation

| Measure | Result |
| --- | ---: |
| Overall accuracy | 62.3% on 8,220 questions |
| Yes/no accuracy | 85.7% |
| Open-ended accuracy | 40.3% |
| SLAKE / PathVQA / VQA-RAD | 83.7% / 59.9% / 46.6% |
| Expected calibration error | 0.073 |
| Confidence-only policy at 0.60 | Answers 66.4%; 84.2% accuracy on answered questions |
| Full traffic-light policy | Answers 43.7%; 83.7% accuracy on answered questions; 585 incorrect answers shown |

The published CrossGate results in the attached material are claims about a different model and cannot be attributed to this implementation. This benchmark evaluation does not establish safety or accuracy on real patients, new hospitals, full imaging studies, or arbitrary questions. Before clinical use, Diagnex needs independent radiologist-labelled testing, false-negative analysis, domain-shift testing, and product security and regulatory review.

For reproducibility and known limitations, see [PROJECT_STATUS.md](PROJECT_STATUS.md) and [README.md](README.md).

**B.Tech Final-Year Project · Department of CSE · KIET Group of Institutions · Mentor: Dr. Gaurav Dubey**
