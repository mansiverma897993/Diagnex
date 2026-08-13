"""Diagnex API - real inference, safety-gated.

Replaces the previous simulated backend, which derived "confidence" from
`len(filename)` and returned fixed clinical text containing specific lab values
no model had measured.

Design rules this file enforces:

* No fabrication. Every field is computed from model output.
* No answer survives an abstention. When the gate says RED, the answer is
  removed from the response body, not merely flagged - the client cannot render
  what it was never sent.
* No patient data at rest. De-identified pixels live in an in-memory session
  cache with a TTL so follow-up questions work; nothing touches disk.
* No silent degradation. If the model is not trained, endpoints return 503 with
  instructions rather than falling back to plausible-looking output.

    uvicorn backend.main:app --reload --port 8000     (from the repo root)
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend.app import report, taxonomy  # noqa: E402
from backend.app.engine import ArtifactsMissing, get_engine  # noqa: E402
from backend.app.imaging import UnreadableImage, read_upload  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("diagnex")

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
SESSION_TTL_SECONDS = 30 * 60
MAX_SESSIONS = 200

#: Follow-up questions offered per modality. Each is genuinely run through the
#: model and gated, so a suggestion can itself come back withheld.
SUGGESTED_QUESTIONS: dict[str, list[str]] = {
    "xray": ["is the chest normal?", "is there a pleural effusion?", "are the lungs clear?"],
    "ct": ["is there a mass?", "which organ is shown?", "is there any abnormality?"],
    "mri": ["is there an abnormality?", "which part of the body is this?", "is the brain normal?"],
    "ultrasound": ["is there an abnormality?", "which organ is shown?"],
    "pathology": ["is this tissue normal?", "what does the image show?"],
    "unknown": ["is there an abnormality?", "which organ is shown?"],
}

app = FastAPI(
    title="Diagnex Clinical VQA API",
    version="2.0.0",
    description="Safety-gated medical visual question answering. Screening aid, not a diagnosis.",
)

# The dev frontend runs on Vite's default ports. Tighten before any deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.environ.get(
            "DIAGNEX_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
        ).split(",")
        if o.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- session cache ---------------------------------------------------------


@dataclass
class Session:
    image: object
    filename: str
    modality: str
    created: float


class SessionStore:
    """In-memory, TTL-bounded store of de-identified images.

    Deliberately not a database. Follow-up questions need the pixels for a few
    minutes; nothing needs them after that, and writing medical images to disk
    would create a retention obligation the project explicitly forbids.
    """

    def __init__(self, ttl: float = SESSION_TTL_SECONDS, cap: int = MAX_SESSIONS):
        self._data: dict[str, Session] = {}
        self._ttl, self._cap = ttl, cap
        self._lock = threading.Lock()

    def _evict(self) -> None:
        now = time.time()
        for key in [k for k, v in self._data.items() if now - v.created > self._ttl]:
            self._data.pop(key, None)
        while len(self._data) > self._cap:
            oldest = min(self._data, key=lambda k: self._data[k].created)
            self._data.pop(oldest, None)

    def put(self, key: str, session: Session) -> None:
        with self._lock:
            self._data[key] = session
            self._evict()

    def get(self, key: str) -> Session | None:
        with self._lock:
            self._evict()
            return self._data.get(key)


sessions = SessionStore()

#: Rolling window of assessments, for the Safety Dashboard. Counts only.
_recent: deque = deque(maxlen=500)
_recent_lock = threading.Lock()


def _record_outcome(assessment) -> None:
    with _recent_lock:
        _recent.append(
            {
                "band": assessment.band.value,
                "abstain": assessment.abstain,
                "danger_zone": assessment.danger_zone,
                "error_code": assessment.likely_error.code,
                "confidence": assessment.confidence,
                "ts": time.time(),
            }
        )


# --- schemas ---------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="id returned by /api/upload")
    question: str = Field(..., min_length=1, max_length=500)


def _engine_or_503():
    try:
        engine = get_engine()
        engine.load()
        return engine
    except ArtifactsMissing as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "model_not_trained",
                "message": str(exc),
                "hint": "The API refuses to serve simulated results. Train the model first.",
            },
        ) from exc


# --- endpoints -------------------------------------------------------------


@app.get("/")
def root():
    return {
        "status": "active",
        "service": "Diagnex Clinical VQA API",
        "version": app.version,
        "disclaimer": report.DISCLAIMER,
    }


@app.get("/api/health")
def health():
    """Report whether real inference is available. Never guesses."""
    try:
        engine = get_engine()
        engine.load()
    except ArtifactsMissing as exc:
        return {"ready": False, "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("engine load failed")
        return {"ready": False, "reason": f"{type(exc).__name__}: {exc}"}

    import json

    metrics_path = REPO_ROOT / "ml" / "artifacts" / "vqa_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    return {
        "ready": True,
        "answer_vocabulary": len(engine.vocab),
        "temperature": engine.temperature,
        "thresholds": {"abstain": 0.60, "green": 0.85},
        "metrics": {
            k: metrics.get(k)
            for k in ("overall_accuracy", "closed_accuracy", "open_accuracy", "test_ece")
            if k in metrics
        },
    }


@app.get("/api/taxonomy")
def get_taxonomy():
    """The 12 error categories, for the Education Center."""
    return {
        "categories": [
            {
                "code": c.code,
                "group": c.group,
                "name": c.name,
                "plain_english": c.plain_english,
                "risk": c.risk.value,
                "example": c.example,
                "published_rate": c.published_rate,
                "provisional": not c.is_published,
            }
            for c in taxonomy.TAXONOMY
        ],
        "note": (
            "Eight categories and their prevalence figures come from the project's "
            "source research. Four are marked provisional: the research materials "
            "state the taxonomy has 12 categories but enumerate only 8."
        ),
    }


@app.get("/api/stats")
def stats():
    """Aggregate safety statistics for the dashboard. No image data."""
    with _recent_lock:
        items = list(_recent)
    if not items:
        return {"total": 0, "bands": {}, "error_types": {}, "abstention_rate": 0.0, "danger_zone_rate": 0.0}
    bands = Counter(i["band"] for i in items)
    errors = Counter(i["error_code"] for i in items)
    return {
        "total": len(items),
        "bands": dict(bands),
        "error_types": {
            code: {"count": n, "name": taxonomy.get(code).name, "risk": taxonomy.get(code).risk.value}
            for code, n in errors.most_common()
        },
        "abstention_rate": sum(i["abstain"] for i in items) / len(items),
        "danger_zone_rate": sum(i["danger_zone"] for i in items) / len(items),
        "mean_confidence": sum(i["confidence"] for i in items) / len(items),
    }


@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    category: str = Form("unknown"),
    question: Optional[str] = Form(None),
):
    engine = _engine_or_503()

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file exceeds {MAX_UPLOAD_BYTES // 2**20} MB limit")

    try:
        intake = read_upload(data)
    except UnreadableImage as exc:
        raise HTTPException(400, f"could not read the uploaded file: {exc}") from exc

    if intake.stripped_fields:
        logger.info("stripped %d identifying DICOM fields", len(intake.stripped_fields))

    asked = (question or "").strip() or "is there an abnormality?"
    try:
        analysis = engine.analyze(intake.image, asked)
    except Exception as exc:  # noqa: BLE001
        logger.exception("inference failed")
        raise HTTPException(500, f"inference failed: {type(exc).__name__}") from exc

    _record_outcome(analysis.assessment)

    session_id = f"api-{uuid.uuid4().hex[:12]}"
    sessions.put(
        session_id,
        Session(
            image=intake.image,
            filename=file.filename or "upload",
            modality=analysis.modality,
            created=time.time(),
        ),
    )

    # Suggested follow-ups are real predictions, each independently gated.
    qa: list[dict] = []
    for q in SUGGESTED_QUESTIONS.get(analysis.modality, SUGGESTED_QUESTIONS["unknown"]):
        if q.lower() == asked.lower():
            continue
        try:
            extra = engine.analyze(intake.image, q)
        except Exception:  # noqa: BLE001 - a failed suggestion must not fail the upload
            logger.warning("suggested question failed: %s", q, exc_info=True)
            continue
        qa.append(
            {
                "q": q,
                "a": (
                    f"{extra.answer} ({extra.confidence:.0%} confidence, {extra.assessment.band.value})"
                    if not extra.assessment.abstain
                    else f"Withheld - {extra.confidence:.0%} confidence is below the 60% safety "
                    f"threshold. {extra.assessment.message}"
                ),
                "status": extra.assessment.band.value,
                "confidence": round(extra.confidence * 100),
            }
        )

    body = analysis.to_dict()
    assessment = analysis.assessment
    return {
        "id": session_id,
        "session_id": session_id,
        "name": file.filename or "upload",
        "type": category or report.modality_label(analysis.modality),
        "size": f"{len(data) / 2**20:.1f} MB",
        # The frontend reads `confidence` as an integer percentage.
        "confidence": round(analysis.confidence * 100),
        "status": assessment.band.value,
        "answer": body["answer"],
        "withheld_answer": body.get("withheld_answer"),
        "diagnosis": report.compose(
            question=asked,
            answer=analysis.answer if not assessment.abstain else None,
            assessment=assessment,
            modality=analysis.modality,
            modality_confidence=analysis.modality_confidence,
            declared_modality=intake.declared_modality,
            alternatives=analysis.alternatives,
        ),
        "summary": report.summarise(
            question=asked,
            answer=analysis.answer,
            assessment=assessment,
            modality=analysis.modality,
        ),
        "qa": qa,
        "safety": body["safety"],
        "alternatives": body["alternatives"],
        "detected_modality": analysis.modality,
        "modality_confidence": round(analysis.modality_confidence, 4),
        "intake": intake.to_dict(),
        "question": asked,
        "disclaimer": report.DISCLAIMER,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Follow-up question about an already-uploaded image.

    Runs the real model against the stored pixels. The previous version replied
    from keyword matches without consulting the image at all.
    """
    engine = _engine_or_503()

    session = sessions.get(req.session_id)
    if session is None:
        raise HTTPException(
            404,
            "session expired or unknown - images are held for 30 minutes only, "
            "please upload the scan again",
        )

    try:
        analysis = engine.analyze(session.image, req.question.strip())
    except Exception as exc:  # noqa: BLE001
        logger.exception("chat inference failed")
        raise HTTPException(500, f"inference failed: {type(exc).__name__}") from exc

    _record_outcome(analysis.assessment)
    assessment = analysis.assessment

    if assessment.abstain:
        reply = (
            f"I am not confident enough to answer that. My best answer carries only "
            f"{analysis.confidence:.0%} confidence, below the 60% threshold this system "
            f"requires. {assessment.message} If this matters for a health decision, "
            f"please use 'Find Nearest Specialist' below."
        )
    else:
        reply = (
            f'Answer: "{analysis.answer}" ({analysis.confidence:.0%} confidence, '
            f"{assessment.band.value}). If this is wrong, the most likely reason is "
            f"{assessment.likely_error.name.lower()} - {assessment.likely_error.plain_english} "
            f"{report.DISCLAIMER}"
        )

    return {
        "reply": reply,
        "answer": None if assessment.abstain else analysis.answer,
        "confidence": round(analysis.confidence * 100),
        "status": assessment.band.value,
        "safety": assessment.to_dict(),
        "alternatives": [{"answer": a, "probability": round(p, 4)} for a, p in analysis.alternatives],
    }
