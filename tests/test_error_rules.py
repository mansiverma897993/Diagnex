"""Tests for the 12-way error labeller and the medical lexicon.

Rule ordering is load-bearing: a missed tumour must never be labelled as a
merely vague answer, because the two carry different Clinical Impact Scores and
therefore different safety bands.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import lexicon, taxonomy  # noqa: E402
from ml.eval.error_rules import label_error  # noqa: E402


def code(question: str, gold: str, pred: str) -> str:
    return label_error(question, gold, pred).code


# --- the safety-critical pair ----------------------------------------------


def test_missed_abnormality_is_critical_category():
    assert code("is there a mass in the lung?", "yes", "no") == "3.1"


def test_missed_abnormality_open_ended():
    assert code("what abnormality is seen?", "pneumonia", "normal") == "3.1"


def test_hallucinated_finding():
    assert code("are the lungs normal appearing?", "no", "yes") == "3.2"


def test_hallucination_open_ended():
    assert code("what is seen?", "normal", "pneumothorax") == "3.2"


def test_missed_abnormality_outranks_granularity():
    """Both rules could fire; the critical one must win."""
    assert code("what abnormality is present?", "large pleural effusion", "normal") == "3.1"


# --- remaining categories --------------------------------------------------


@pytest.mark.parametrize(
    "question,gold,pred,expected",
    [
        ("is there NO fracture?", "yes", "no", "4.1"),
        ("how many kidneys are visible?", "two", "three", "3.3"),
        ("which side is the lesion on?", "left", "right", "1.3"),
        ("what modality is used to take this image?", "MRI", "CT", "1.2"),
        ("what plane is this image in?", "axial", "coronal", "1.2"),
        ("what is the main organ in the image?", "liver", "kidney", "1.1"),
        ("what disease is shown?", "pneumonia", "stomach", "2.2"),
        ("what color is the stain?", "purple", "pink", "2.3"),
        ("which organ is enlarged?", "spleen", "yes", "4.2"),
    ],
)
def test_category_assignment(question, gold, pred, expected):
    assert code(question, gold, pred) == expected


def test_negation_beats_plain_yes_no_flip():
    """Without the negation cue the same flip is a detection error, not 4.1."""
    assert code("is there no fracture?", "yes", "no") == "4.1"
    assert code("is there a fracture?", "yes", "no") == "3.1"


def test_vague_answer_is_granularity_not_anatomy_mixup():
    assert code("what does the image show?", "left lower lobe", "lobe") == "2.1"


def test_every_error_gets_a_valid_code():
    """The labeller must be total - no error may fall through unclassified."""
    odd_cases = [
        ("what is this?", "zzz", "qqq"),
        ("", "yes", "no"),
        ("describe", "12345", "!!!"),
    ]
    for q, g, p in odd_cases:
        assert label_error(q, g, p).code in taxonomy.BY_CODE


def test_residual_labels_are_marked_unconfident():
    label = label_error("what is this?", "zzz", "qqq")
    assert not label.confident, "fallback labels must be distinguishable from rule matches"


def test_rule_matches_are_marked_confident():
    assert label_error("is there a mass?", "yes", "no").confident


# --- lexicon ---------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [("  Yes. ", "yes"), ("NO!", "no"), ("the liver", "liver"),
     ("Present", "yes"), ("absent", "no"), ("Lung, Spinal Cord", "lung spinal cord")],
)
def test_answer_normalisation(raw, expected):
    assert lexicon.normalize_answer(raw) == expected


def test_closed_detection():
    assert lexicon.is_closed("Yes")
    assert lexicon.is_closed("negative")
    assert not lexicon.is_closed("left lower lobe")


@pytest.mark.parametrize(
    "text,expected",
    [("left lower lobe", "left"), ("right", "right"),
     ("bilateral effusion", "bilateral"), ("left and right", "bilateral"), ("liver", None)],
)
def test_laterality(text, expected):
    assert lexicon.laterality_of(text) == expected


@pytest.mark.parametrize("text,expected", [("two", 2), ("3", 3), ("none", 0), ("several", None), ("liver", None)])
def test_count_extraction(text, expected):
    assert lexicon.count_of(text) == expected


def test_negation_cues():
    assert lexicon.has_negation("is there no fracture")
    assert not lexicon.has_negation("is there a fracture")


def test_modality_inference():
    assert lexicon.infer_modality("what does this ct scan show?") == "ct"
    assert lexicon.infer_modality("is the histopathology slide normal?") == "pathology"
    assert lexicon.infer_modality("is this abnormal?") == "unknown"


def test_normal_claim_detection():
    assert lexicon.is_normal_claim("normal")
    assert lexicon.is_normal_claim("no")
    assert lexicon.is_normal_claim("unremarkable")
    assert not lexicon.is_normal_claim("pneumonia")
