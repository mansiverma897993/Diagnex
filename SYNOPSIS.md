# DIAGNEX

> B.Tech, Computer Science and Engineering | KIET Group of Institutions
> Mansi Verma | Mentor: Dr. Gaurav Dubey

## Abstract
Radiologists face increasing image-review workloads, while medical visual question-answering models can return confident but incorrect answers. Diagnex is a research prototype that accepts a medical still image and a natural-language question, predicts an answer, and may withhold it through a traffic-light uncertainty policy. The aim is to study whether calibrated confidence and abstention can make benchmark responses more transparent. It is an educational and research aid, not a diagnostic system or a substitute for a radiologist.

## Objectives
- Build an image-question interface with upload, follow-up chat, and a downloadable report.
- Train a medical visual question-answering model on public data using image-disjoint train, validation, and test splits.
- Calibrate answer confidence, withhold selected uncertain outputs, and measure the accuracy-coverage trade-off.

## Methodology
1. Prepare 41,908 question-answer pairs over 5,244 images from VQA-RAD, SLAKE, and PathVQA; remove duplicate-image leakage across splits.
2. Encode images and questions with frozen BiomedCLIP, add TF-IDF question features, and train a fusion classifier over 3,693 answer classes.
3. Fit temperature scaling on validation data. At inference, combine calibrated confidence with an experimental 12-class error predictor to assign GREEN, YELLOW, or RED; RED answers are omitted from the API response.
4. Evaluate on a held-out image-disjoint test set and report overall, question-type, dataset, calibration, and selective-answer results.

## Implementation
React and Vite provide the existing interface; FastAPI and PyTorch serve the saved model and safety policy. PNG, JPEG, TIFF, and DICOM still images are accepted. Temporary sessions expire after 30 minutes. The backend loads saved weights without retraining. A database is unnecessary for the anonymous local prototype; accounts or persistent clinical records would require one and a patient-data protection design.

## Held-out results
| Measure | Result |
| --- | ---: |
| Overall answer accuracy | 62.3% (8,220 questions) |
| Yes/no; open-ended accuracy | 85.7%; 40.3% |
| SLAKE; PathVQA; VQA-RAD accuracy | 83.7%; 59.9%; 46.6% |
| Expected calibration error | 0.073 |
| Full traffic-light policy | 43.7% answered; 83.7% correct among answers |

## Scope and next steps
The current backend uses BiomedCLIP fusion, not the CrossGate architecture described in the proposal. On this benchmark, the traffic-light policy still displayed 585 incorrect answers. Results do not establish performance on real patients, full imaging studies, or new hospitals. Clinical use would require radiologist-labelled external validation, false-negative and domain-shift analysis, security controls, and regulatory review.

Source of results: local image-disjoint evaluation in ml/artifacts/vqa_metrics.json and ml/artifacts/error_metrics.json; see PROJECT_STATUS.md for details.
