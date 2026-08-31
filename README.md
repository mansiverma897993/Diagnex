# Diagnex : AI Medical Imaging & Radiologist VQA Portal

Upload an X-ray, CT, MRI,
ultrasound or pathology slide, ask a question in natural language, and get an
answer **together with an honest account of how much to trust it** or a
refusal, when the model should not be trusted.

> **Screening aid for educational use. Not a medical diagnosis, and not a
> substitute for examination by a qualified doctor.**

The premise, taken from the project's source research: medical VQA models are
*dangerously overconfident when wrong*, with **26.8% of errors** landing in a
"clinical danger zone" where the model is simultaneously incorrect and highly
confident. The point of this system is not to be right every time no published
medical VQA model is but to **know when it might be wrong, and say so**.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Node](https://img.shields.io/badge/Node-18%2B-339933?logo=nodedotjs&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.5.1-EE4C2C?logo=pytorch&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688?logo=fastapi&logoColor=white)
![CPU only](https://img.shields.io/badge/No%20GPU%20required-true-4CAF50)

---

## Features

- **Multi-modal intake** : X-ray, CT, MRI, ultrasound and histopathology slides,
  uploaded as PNG/JPEG/TIFF or native **DICOM**.
- **Natural-language VQA** : closed (yes/no) and open-ended questions answered
  over a 3,698-word medical answer vocabulary.
- **Honest uncertainty gate** : a traffic-light (GREEN / YELLOW / RED) that
  withholds answers rather than bluff, driven by *calibrated* confidence **and**
  a predicted failure mode.
- **Follow-up chat** : de-identified pixels live in a TTL-bounded in-memory
  session cache (30 min), so you can ask a series of questions about one scan.
- **Zero fabrication by design** : every report sentence is derived from model
  output. Withheld answers are removed from the API response body, not flagged.
- **De-identification at the boundary** : DICOM tags and EXIF are stripped
  before pixels reach any other code; nothing is written to disk.
- **Runs on CPU** : the vision transformer is frozen and executed once during
  feature extraction, so the whole system trains and serves on a laptop.

---

## Table of contents

- [How the safety gate works](#how-the-safety-gate-works)
- [What the model actually achieves](#what-the-model-actually-achieves)
- [Architecture](#architecture)
- [Run it locally](#run-it-locally)
- [API reference](#api-reference)
- [The 12-category error taxonomy](#the-12-category-error-taxonomy)
- [Honest limitations](#honest-limitations)
- [Ethics](#ethics)
- [Project layout](#project-layout)
- [Credits](#credits)

---

## How the safety gate works

Confidence alone is not sufficient, so **two signals** drive every decision:

1. **Calibrated confidence.** A raw softmax is systematically overconfident; a
   0.60 cut on uncalibrated scores would not mean what the research says it
   means. A temperature fitted on the validation split (see
   `ml/train/train_vqa.py`) brings the calibration error down to **0.083**.
2. **A 12-way error-type prediction** *if* this answer is wrong, how is it
   most likely wrong? which feeds an expected **Clinical Impact Score**.

The second signal is what separates this from a plain threshold:

```
confidence 0.92  →  passes the 0.60 gate
                 →  but likely failure mode is "abnormality detection failure"
                    (CRITICAL: the model says normal while a finding is present)
                 →  forced to RED, answer withheld
```

A 92%-confident answer gets withheld because the way it would fail is a missed
tumour. That is the whole idea.

| Band | When | Behaviour |
| :--- | :--- | :--- |
| 🟢 GREEN | ≥ 85% and no high-risk failure mode | Answer shown |
| 🟡 YELLOW | 60–85%, or GREEN downgraded by a high-risk failure mode | Answer shown, verify with a doctor |
| 🔴 RED | < 60%, or a likely CRITICAL failure mode | **Answer withheld**, doctor finder shown |

A withheld answer is *removed from the API response body*, not merely flagged
the client cannot render what it was never sent.

**Danger zone.** When the model is confident enough to pass the gate but its
expected Clinical Impact Score is severe, the result is flagged explicitly. This
is the confidently-wrong quadrant the research places 26.8% of errors in.

---

## What the model actually achieves

Measured on a held-out test split of **8,231 question–answer pairs**. These are
real numbers from `ml/artifacts/vqa_metrics.json`, reproducible with the
pipeline in [Run it locally](#run-it-locally).

| Metric | Result |
| :--- | ---: |
| Closed questions (yes/no) | **85.5%** |
| Open-ended questions | 41.5% |
| Overall | 62.8% |
| Calibration error (ECE) | **0.083** after temperature scaling |

Per dataset:

| Dataset | n | Overall | Closed | Open |
| :--- | ---: | ---: | ---: | ---: |
| SLAKE | 1,061 | **83.5%** | 88.5% | 80.9% |
| PathVQA | 6,719 | 60.9% | 86.8% | 34.9% |
| VQA-RAD | 451 | 41.9% | 63.3% | 15.0% |

### The abstention trade-off the reason this project exists

Withholding low-confidence answers is what converts a 62.8%-accurate model into
a system that is safe to put in front of a patient:

| Threshold | Answers | Accuracy when it answers | Errors removed |
| :--- | ---: | ---: | ---: |
| no gate | 100% | 62.8% | — |
| τ = 0.50 | 75.0% | 78.6% | 57.0% |
| **τ = 0.60** | **69.6%** | **81.9%** | **66.1%** |
| τ = 0.70 | 65.1% | 84.5% | 72.9% |
| τ = 0.85 | 56.7% | 89.0% | 83.2% |

At the published threshold of τ = 0.60 the system declines about three questions
in ten, and is right **81.9%** of the time on the rest a 19-point improvement
over answering everything.

---

## Architecture

### Inference (runtime)

The FastAPI backend is authoritative for safety decisions: it computes
calibrated confidence, predicts the failure mode, applies the traffic-light
policy, and only then composes the patient-facing report. The React UI never
sees an answer the gate refused.

```mermaid
flowchart TB
    subgraph UI["React UI · Vite  (src/)"]
        UP["Upload scan + question"]
        CH["Follow-up chat"]
        RES["Traffic-light results<br/>GREEN / YELLOW / RED"]
    end

    subgraph API["FastAPI backend  (backend/main.py)"]
        E1["POST /api/upload"]
        E2["POST /api/chat"]
        E3["GET /api/health"]
        SESS["TTL in-memory session cache<br/>(30 min, de-identified, capped)"]
    end

    subgraph INTAKE["Intake  (backend/app/imaging.py)"]
        DEID["De-identification<br/>DICOM tags + EXIF stripped"]
        DEC["Decode → bare RGB pixels"]
    end

    subgraph ENG["Inference engine  (backend/app/engine.py)"]
        VIT["BiomedCLIP ViT-B/16 · frozen<br/>1536-d image embedding"]
        TXT["BiomedCLIP text + TF-IDF n-grams<br/>512-d + sparse question embedding"]
        FUSE["Fusion head  [i ; t ; i×t]<br/>→ answer over 3,698-word vocab"]
        CAL["Temperature scaling<br/>calibrated confidence"]
        ERR["12-way error-type predictor<br/>→ Clinical Impact Score"]
        MOD["Zero-shot modality detection"]
    end

    subgraph SAFE["Safety gate  (backend/app/safety.py)"]
        GATE{"Traffic-light policy<br/>τ=0.60 abstain · 0.85 green"}
        RED["RED — answer withheld<br/>removed from response body"]
    end

    subgraph RPT["Reporting  (backend/app/report.py)"]
        COMP["Compose findings, summary,<br/>abstention reasons from<br/>model output only"]
    end

    UP --> E1
    CH --> E2
    E1 --> DEID --> DEC --> SESS
    E1 --> VIT
    E2 --> SESS --> VIT
    VIT --> FUSE
    TXT --> FUSE
    FUSE --> CAL
    CAL --> GATE
    CAL --> ERR --> GATE
    VIT --> MOD
    GATE -->|"GREEN / YELLOW"| COMP
    GATE -->|"RED · risk override"| RED
    GATE -->|"RED · low confidence"| RED
    COMP --> RES
    E3 -.->|"ready? artifacts present?"| ENG
```

Two design choices worth explaining:

- **`i × t`, not just `[i ; t]`.** Answer priors in medical VQA are strong enough
  that a concatenation-only head scores well while barely consulting the image.
  The multiplicative term forces image and question to agree.
- **TF-IDF alongside the CLIP text embedding.** Contrastive text encoders
  represent negation poorly "is there a mass" and "is there *no* mass" sit
  close together in CLIP space. Since negation is itself error category 4.1, the
  head needs a representation that separates them.

### Training pipeline

The expensive step runs exactly once: frozen BiomedCLIP embeddings are cached to
disk, after which training the small fusion head takes minutes on CPU.

```mermaid
flowchart LR
    subgraph DATA["ml/data"]
        D1["VQA-RAD"]
        D2["SLAKE"]
        D3["PathVQA"]
        BUILD["build_dataset.py<br/>download + unify → manifest.jsonl<br/>≈41,900 QA pairs · ≈5,244 images"]
    end
    D1 --> BUILD
    D2 --> BUILD
    D3 --> BUILD
    BUILD --> EXT["features/extract.py<br/>cache frozen BiomedCLIP embeddings<br/>1536-d image · 512-d + TF-IDF text"]
    EXT --> TRAIN["train/train_vqa.py<br/>train fusion head + fit temperature"]
    TRAIN --> ERRTR["eval/mine_errors.py<br/>mine errors · train 12-way predictor"]
    TRAIN --> ART["ml/artifacts/<br/>vqa_head.pt · tfidf.pkl<br/>error_predictor.pt · answer_vocab.json"]
    ERRTR --> ART
    ART --> SVC["Served by the FastAPI engine"]
```

Everything runs on CPU. The vision transformer executes once during feature
extraction and never again during training the trainable head is **≈6.6M
parameters** and fits in minutes, which is what makes a laptop viable.

---

## Run it locally

### Prerequisites

- **Python 3.10+** (3.10–3.12 recommended; CPU-only, no GPU or CUDA needed)
- **Node.js 18+** and npm
- ~6 GB free disk if you run the full ML pipeline (datasets + model weights)

> On Windows, some torch builds conflict with MKL's OpenMP at model-construction
> time (`0xC0000005`). The repo already sets `KMP_DUPLICATE_LIB_OK=TRUE` in
> `ml/features/extract.py` and `backend/app/engine.py`, and
> `ml/features/run_extract.py` restarts the extraction step until the cache is
> complete. The CPU-only torch wheels below avoid most of these issues.

### 1. Clone and install

```bash
git clone https://github.com/mansiverma897993/Diagnex.git
cd Diagnex
```

**Python dependencies** (into a virtual environment):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux
```

Then install the ML + backend requirements (the file already pins CPU-only
`+cpu` torch wheels for the no-GPU setup):

```bash
pip install -r ml/requirements.txt
```

Alternatively, if you use `uv`:

```bash
uv venv --python 3.11
uv pip install -r ml/requirements.txt --index-strategy unsafe-best-match
```

**Frontend dependencies:**

```bash
npm install
```

### 2. Build the dataset and train the model

Each step is resumable and safe to interrupt. The first step downloads the three
public datasets; the second is the slow one (frozen feature extraction, once);
the last two train the two heads.

```bash
python ml/data/build_dataset.py       # ≈41,900 QA pairs, ≈5,244 images
python ml/features/run_extract.py     # cache frozen embeddings (slow, once)
python ml/train/train_vqa.py          # train + calibrate the answer head
python ml/eval/mine_errors.py         # error corpus + 12-way error predictor
```

On completion, everything the server needs is in `ml/artifacts/`
(`vqa_head.pt`, `error_predictor.pt`, `tfidf.pkl`, `answer_vocab.json`).

> **Optional configuration.** By default the pipeline targets
> `D:\diagnex\data` and the Hugging Face cache lives in `D:\diagnex\.hf`. To use
> your own locations, set the environment variables first:
>
> ```powershell
> $env:DIAGNEX_DATA  = "D:\data\diagnex"
> $env:HF_HOME      = "D:\cache\hf"
> $env:DIAGNEX_ARTIFACTS = "D:\diagnex\Diagnex\ml\artifacts"
> ```

### 3. Run the backend

```bash
uvicorn backend.main:app --port 8000
```

The API refuses to serve simulated results. `GET /api/health` reports whether
real inference is available; until the pipeline above has run, every analysis
endpoint returns **503 with instructions** rather than a made-up answer.

### 4. Run the frontend

In a second terminal:

```bash
npm run dev
```

### Running the Python FastAPI Backend service

Open **http://localhost:5173**. Uploads and chat questions are sent to the
FastAPI backend at `http://localhost:8000` (override with
`VITE_DIAGNEX_API`). CORS is pre-configured for the Vite dev ports; tighten it
before any deployment via `DIAGNEX_CORS_ORIGINS`.

### Tests

```bash
python -m pytest tests/ -q
```

Unit tests cover the safety gate, error labelling rules and the inference
engine; the end-to-end tests are skipped automatically until the model is
trained.

---

## API reference

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/` | Service info + medical disclaimer |
| GET | `/api/health` | `ready: true/false` — never guesses |
| GET | `/api/taxonomy` | The 12 error categories, for the education centre |
| GET | `/api/stats` | Aggregate safety statistics (bands, abstention, danger zone) |
| POST | `/api/upload` | Upload a scan (+ optional question) → full analysis |
| POST | `/api/chat` | Follow-up question about an already-uploaded session |

All analysis endpoints return **503** with the model is untrained, **400** on an
unreadable image, **413** above the 40 MB limit, and **404** for an expired
chat session.

---

## The 12-category error taxonomy

| Code | Category | Risk | Published rate |
| :--- | :--- | :--- | ---: |
| 1.1 | Anatomical Misidentification | HIGH | 30.1% |
| 1.2 | Modality or Plane Confusion | MEDIUM | *provisional* |
| 1.3 | Spatial Reasoning Failure | HIGH | 2.9% |
| 2.1 | Granularity Mismatch | MEDIUM | 12.4% |
| 2.2 | Category Domain Confusion | HIGH | 19.0% |
| 2.3 | Attribute Description Error | MEDIUM | *provisional* |
| 3.1 | **Abnormality Detection Failure** | **CRITICAL** | 13.2% |
| 3.2 | False Positive Hallucination | HIGH | 14.2% |
| 3.3 | Counting Error | MEDIUM | 10.0% |
| 3.4 | Localisation Error | HIGH | *provisional* |
| 4.1 | Negation Comprehension Failure | HIGH | 0.5% |
| 4.2 | Question Misinterpretation | MEDIUM | *provisional* |

Eight categories and their prevalence figures are transcribed from the project's
source research. The research states the taxonomy has 12 categories but
enumerates only 8; **the remaining four are reconstructed from the numbering
gaps and are labelled provisional everywhere they appear** in the API, in the
UI and in reports. They are never presented as published findings.

### Where the error corpus comes from

The mentor's 1,975-error annotated dataset was not available, so the corpus is
generated instead: run the trained model over held-out data, take every wrong
prediction, and classify *how* it was wrong using deterministic, inspectable
rules (`ml/eval/error_rules.py`). This yields ~5,885 labelled errors.

Its quality is measured rather than assumed. SLAKE annotates every question with
a `content_type` assigned by its authors independently of this project, which
gives a check on the labeller:

| Dataset | Rule coverage | Independent agreement |
| :--- | ---: | ---: |
| SLAKE | 88% | 63.0% |
| VQA-RAD | 76% | — |
| PathVQA | 42% | — |

**The labeller is reliable on radiology and weak on histopathology free-text.**
PathVQA answers are long descriptive phrases that curated term lists match
poorly, and since PathVQA is 78% of the data it drags the aggregate down to ~47%
coverage. This is a real limitation, not a rounding detail see below.

---

## Honest limitations

- **This is not a diagnostic tool and never will be at this accuracy.** 62.8%
  overall, 41.9% on VQA-RAD. The safety gate is what makes it defensible, not
  the raw accuracy.
- **Open-ended accuracy is weak (41.5%).** The answer vocabulary covers only 83%
  of test answers; the remaining 17% are unreachable by construction and counted
  as wrong.
- **VQA-RAD is the weakest split (41.9%)** only ~1,620 training rows survive
  the image-grouped validation split, which is very little to learn from.
- **Error-corpus labelling covers ~47% of errors.** The rest receive a fallback
  label routed by question form, marked `rule_confident: false` and reported
  separately rather than hidden.
- **The error-type predictor scores ~62.9%** over 12 classes (chance ≈ 8.3%).
  Useful, not authoritative.
- **Our error distribution differs from the published aggregate**, mostly
  because our training mix is 78% PathVQA and the published aggregate is not.
  Comparison is done per dataset in `ml/eval/mine_errors.py`, which is the
  like-for-like view.
- **Four taxonomy categories are provisional** pending confirmation.

---

## Ethics

- Only public research datasets: **VQA-RAD**, **SLAKE**, **PathVQA**. No patient
  images.
- DICOM identifiers and EXIF are stripped at the intake boundary, before pixels
  reach any other code, so nothing downstream can persist an identifier.
- De-identified images live in a TTL-bounded in-memory cache so follow-up
  questions work; **nothing is written to disk**.
- Every screen and every report carries the medical disclaimer.
- The system refuses to start rather than serve simulated results.

---

## Project layout

```
backend/
  main.py                 FastAPI endpoints (upload, chat, health, stats)
  app/
    imaging.py            DICOM/image intake and de-identification
    engine.py             inference: frozen towers + trained heads
    taxonomy.py           12 categories, risk tiers, CIS weights
    safety.py             traffic-light gate, abstention, danger zone
    lexicon.py            curated medical term sets, answer normalisation
    report.py             patient-facing text, derived only from model output
ml/
  data/build_dataset.py   download + unify the three datasets
  features/extract.py     cache frozen BiomedCLIP embeddings
  features/run_extract.py restart-until-complete wrapper (Windows OpenMP fault)
  train/train_vqa.py      train + calibrate the answer head
  eval/error_rules.py     12-way rule-based error labeller
  eval/mine_errors.py     error corpus + error-type predictor
src/App.jsx               React UI
tests/                    safety, error-labelling, engine and E2E tests
```

---

## Credits

B.Tech final year project, Department of CSE, KIET Group of Institutions.
Mentor: Dr. Gaurav Dubey. Safety methodology error taxonomy, τ = 0.60
abstention threshold, Clinical Impact Score follows his published research.
