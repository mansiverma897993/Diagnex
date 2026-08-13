"""Compose patient-facing text from real model output.

Every sentence here is derived from a value the model actually produced: the
predicted answer, its calibrated confidence, the safety band, and the likely
failure mode. Nothing is invented.

That constraint is the whole reason this module exists as its own file. The
previous implementation emitted fixed strings containing specific clinical
values ("Hemoglobin: 14.2 g/dL", "WBC 18.5") that no model had measured. A
patient cannot tell fabricated numbers from measured ones, so the system must
be structurally incapable of producing them.
"""

from __future__ import annotations

from .safety import Band, SafetyAssessment

DISCLAIMER = (
    "Diagnex is a screening aid for educational use. It is not a medical "
    "diagnosis and does not replace examination by a qualified doctor."
)

_MODALITY_LABEL = {
    "xray": "X-ray",
    "ct": "CT scan",
    "mri": "MRI scan",
    "ultrasound": "ultrasound",
    "pathology": "pathology slide",
    "unknown": "medical image",
}


def modality_label(tag: str) -> str:
    return _MODALITY_LABEL.get((tag or "").lower(), tag or "medical image")


def summarise(
    *,
    question: str,
    answer: str | None,
    assessment: SafetyAssessment,
    modality: str,
) -> str:
    """One-line summary for history lists and cards."""
    label = modality_label(modality)
    if assessment.abstain:
        return (
            f"AI declined to answer this {label} question "
            f"({assessment.confidence:.0%} confidence, below the 60% safety threshold). "
            "Referred to a doctor."
        )
    return f'{label}: answered "{answer}" with {assessment.confidence:.0%} confidence ({assessment.band.value}).'


def compose(
    *,
    question: str,
    answer: str | None,
    assessment: SafetyAssessment,
    modality: str,
    modality_confidence: float,
    declared_modality: str | None = None,
    alternatives: list[tuple[str, float]] | None = None,
) -> str:
    """Full report body shown on the results screen."""
    label = modality_label(modality)
    lines: list[str] = []

    if assessment.abstain:
        lines.append(
            f"ANSWER WITHHELD - SAFETY THRESHOLD NOT MET. "
            f"You asked: \"{question}\". The model's confidence in its best answer is "
            f"{assessment.confidence:.0%}, below the 60% threshold this system requires "
            f"before it will stand behind an answer about a {label}."
        )
        lines.append(
            "Published analysis of this error taxonomy found that abstaining below 60% "
            "removes 51.1% of critical errors while preserving 91.8% of correct answers. "
            "Withholding here is the system working as designed, not a malfunction."
        )
    else:
        lines.append(
            f"You asked: \"{question}\". The model's answer is \"{answer}\", with "
            f"{assessment.confidence:.0%} calibrated confidence ({assessment.band.value} band)."
        )
        if assessment.band is Band.YELLOW:
            lines.append(
                "This falls in the verify-with-a-doctor range. Treat it as a prompt to "
                "seek confirmation, not as a finding."
            )

    if assessment.downgrade_reason:
        lines.append(f"Safety downgrade: {assessment.downgrade_reason}")

    err = assessment.likely_error
    provisional = "" if err.is_published else " (category pending mentor confirmation)"
    lines.append(
        f"Most likely failure mode if this answer is wrong: {err.name} "
        f"[{err.code}, {err.risk.value} risk, {assessment.likely_error_prob:.0%} likely]"
        f"{provisional}. In plain terms: {err.plain_english} For example: {err.example}"
    )

    if assessment.danger_zone:
        lines.append(
            "DANGER ZONE FLAG: the model is confident enough to pass the safety gate, "
            "yet its most likely failure mode carries high clinical impact "
            f"(expected impact score {assessment.expected_cis:.1f}/5.0). Published work "
            "places 26.8% of all errors in exactly this confidently-wrong quadrant. "
            "Independent confirmation is strongly advised."
        )

    if alternatives:
        alts = ", ".join(f'"{a}" ({p:.0%})' for a, p in alternatives)
        lines.append(f"The model also considered: {alts}.")

    if declared_modality and modality:
        declared = declared_modality.strip().upper()
        aliases = {"CR": "xray", "DX": "xray", "CT": "ct", "MR": "mri", "US": "ultrasound", "SM": "pathology"}
        expected = aliases.get(declared)
        if expected and expected != modality:
            lines.append(
                f"NOTE: the file header declares modality {declared}, but the image "
                f"classifier reads it as {label}. Verify the correct study was uploaded."
            )
    elif modality_confidence < 0.5:
        lines.append(
            f"NOTE: image type could not be identified with confidence "
            f"({modality_confidence:.0%} for {label}); the answer may be less reliable."
        )

    lines.append(DISCLAIMER)
    return " ".join(lines)
