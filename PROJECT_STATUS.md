# Diagnex implementation status

Updated 27 October 2026. This is a research prototype, not a radiologist or a clinically validated diagnostic device.

## Source material checked

- `DiagnexAI.pdf`: an eight-page pitch for an image question answering MVP, a traffic-light response, and doctor escalation. It proposes CrossGate-VQA or Gemini Flash but does not supply a trained model.
- The linked Colab notebook: executable CrossGate code and saved output cells. Its later training, transfer, ablation, and bootstrap cells have no execution outputs in the shared notebook. It references a `best_model_combined.pt` checkpoint in a separate Drive folder that was not shared.
- The linked Drive file: a one-page research-phase summary, not a checkpoint.
- The pasted paper introduction and image abstract: research claims that have not been reproduced by this repository. The notebook's executed evaluation cell reports 67.37% on its filtered test set, which differs from the 72.51% claim in the abstract. Those results use a different model and test construction from the backend here.

## What runs today

| Area | Current implementation |
| --- | --- |
| Web frontend | Existing React UI, unchanged by this work. |
| API | FastAPI upload, follow-up questions, health, taxonomy, and aggregate counters. |
| Image intake | PNG/JPEG/TIFF and DICOM still-image decoding with metadata stripped from the pixel object. Multi-frame DICOM uses one middle frame. |
| Data | VQA-RAD, SLAKE, and PathVQA: 41,908 QA rows over 5,244 content-addressed images. |
| Answer model | Frozen BiomedCLIP image/text encoders, TF-IDF question features, and a trained answer-classification head. This is **not** the DenseNet + ViT + BioClinicalBERT CrossGate model. |
| Safety | Temperature scaling, abstention, and a 12-class error predictor trained from rule-derived labels. Its risk estimates are experimental, not clinically validated. |
| Storage | Images are held in a capped in-memory session store for 30 minutes; model artifacts and public benchmark data are stored on disk. |

The tracked `vqa_model.pkl` is a legacy file and is not loaded by the FastAPI inference engine.

## Evaluation protocol

The previous local metrics used the Hugging Face VQA-RAD question split, which placed 183 identical images in both train and test. Those metrics are superseded. `ml/data/build_dataset.py` now repartitions VQA-RAD by image and resolves duplicated images in the other datasets. The rebuilt manifest has zero image overlap between train, validation, and test, including across datasets. Training uses the training split; model selection and temperature scaling use validation; the test split is reserved for final reporting. The error predictor now selects its checkpoint using a separate image-held-out subset of validation errors and measures test accuracy once.

The installed model's held-out results are in `ml/artifacts/vqa_metrics.json` and `ml/artifacts/error_metrics.json`:

| Measure | Result |
| --- | ---: |
| Overall answer accuracy | 62.3% on 8,220 questions |
| Yes/no accuracy | 85.7% |
| Open-ended accuracy | 40.3% |
| VQA-RAD / SLAKE / PathVQA | 46.6% / 83.7% / 59.9% |
| Test expected calibration error | 0.073 |
| Error predictor accuracy against rule-derived labels | 59.3% |
| Full traffic-light policy | Answers 43.7%; 83.7% accuracy on answered questions; 585 wrong answers shown |

Accuracy on public VQA benchmarks does not establish accuracy on real patients, new hospitals, full CT/MRI studies, or arbitrary questions. The rule-derived error labels match a specific rule for 44.9% of errors; the risk score is particularly uncertain.

## Remaining work for clinical or product use

1. Obtain an independently labelled, representative clinical evaluation set and radiologist review. Measure false negatives and subgroup performance, not only overall accuracy.
2. Train and validate CrossGate separately if that exact architecture is required. The local machine has a CPU-only PyTorch installation; the notebook's 206.7-million-parameter model was run on an A100 GPU. A compatible checkpoint is not currently available to this backend.
3. Validate DICOM modality and full study processing, out-of-distribution rejection, calibration by domain, and the error taxonomy. The current medical-image gate and error labels are heuristic.
4. For a real patient service, design authentication, access control, audit logs, retention/deletion, encryption, deployment security, and regulatory review. The current prototype does not implement these product controls.

## Database decision

No database is needed for the anonymous, short-lived local MVP: the session cache intentionally expires and has no account history. A database becomes necessary for login, saved reports, payment, clinic workflows, or audit records. Those features also need a deliberate patient-data handling design before storing scans or identifiers.

## Run without retraining

The new artifacts are installed in `ml/artifacts`. Start the backend with `backend/start_backend.cmd` or `python -m uvicorn backend.main:app --port 8000` from the repository root. The API loads saved weights; it does not train on startup. A portable copy of the six generated files is at `D:\diagnex\Diagnex_model_artifacts_2026-10-27.zip`. The frozen BiomedCLIP base model must also be downloaded or restored from the Hugging Face cache on a new machine; no retraining is needed. Model artifacts and the cache are ignored by Git.
