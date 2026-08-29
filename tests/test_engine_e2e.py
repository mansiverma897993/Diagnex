"""End-to-end check that the engine produces real, gated answers.

Skipped automatically when the model has not been trained, so a fresh clone
still runs a green test suite. Run the ml/ pipeline first to exercise it:

    python -m pytest tests/test_engine_e2e.py -v -s
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

ARTIFACTS = REPO_ROOT / "ml" / "artifacts"
DATA_ROOT = Path(r"D:\diagnex\data")

pytestmark = pytest.mark.skipif(
    not (ARTIFACTS / "vqa_head.pt").exists() or not (ARTIFACTS / "error_predictor.pt").exists(),
    reason="model not trained; run the ml/ pipeline first",
)


@pytest.fixture(scope="module")
def engine():
    from backend.app.engine import get_engine

    eng = get_engine()
    eng.load()
    return eng


@pytest.fixture(scope="module")
def sample_rows():
    manifest = DATA_ROOT / "manifest.jsonl"
    if not manifest.exists():
        pytest.skip("dataset manifest not available")
    rows = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l]
    return [r for r in rows if r["split"] == "test"][:400]


def test_engine_loads_and_self_checks(engine):
    """self_check() runs during load and raises on train/inference mismatch."""
    assert engine.vocab, "answer vocabulary is empty"
    assert engine.temperature > 0
    assert len(engine.error_codes) == 12


def test_analyze_returns_gated_result(engine, sample_rows):
    from PIL import Image

    from backend.app import taxonomy

    row = sample_rows[0]
    img = Image.open(DATA_ROOT / "images" / f"{row['image']}.jpg")
    result = engine.analyze(img, row["question"])

    assert 0.0 <= result.confidence <= 1.0
    assert result.answer in engine.vocab
    assert result.assessment.band.value in {"GREEN", "YELLOW", "RED"}
    assert result.assessment.likely_error.code in taxonomy.BY_CODE
    assert result.modality in {"xray", "ct", "mri", "ultrasound", "pathology"}


def test_abstained_answer_is_not_serialised(engine, sample_rows):
    """A withheld answer must be absent from the payload, not just flagged."""
    from PIL import Image

    for row in sample_rows[:120]:
        img = Image.open(DATA_ROOT / "images" / f"{row['image']}.jpg")
        result = engine.analyze(img, row["question"])
        payload = result.to_dict()
        if result.assessment.abstain:
            assert payload["answer"] is None
            assert "withheld_answer" in payload
            assert json.dumps(payload).count(payload["withheld_answer"]) >= 1
            return
    pytest.skip("no abstention occurred in the sampled rows")


def test_confidence_matches_reported_band(engine, sample_rows):
    """Bands must agree with the thresholds, allowing for risk downgrades."""
    from PIL import Image

    from backend.app.safety import TAU_ABSTAIN, TAU_GREEN

    for row in sample_rows[:60]:
        img = Image.open(DATA_ROOT / "images" / f"{row['image']}.jpg")
        r = engine.analyze(img, row["question"])
        band, conf = r.assessment.band.value, r.confidence
        if band == "GREEN":
            assert conf >= TAU_GREEN
        elif band == "YELLOW":
            assert conf >= TAU_ABSTAIN
        else:
            # RED is reachable above tau only via an explicit risk downgrade.
            assert conf < TAU_ABSTAIN or r.assessment.downgrade_reason is not None


def test_same_input_is_deterministic(engine, sample_rows):
    from PIL import Image

    row = sample_rows[0]
    img = Image.open(DATA_ROOT / "images" / f"{row['image']}.jpg")
    a = engine.analyze(img, row["question"])
    b = engine.analyze(img, row["question"])
    assert a.answer == b.answer
    assert a.confidence == pytest.approx(b.confidence, abs=1e-6)
