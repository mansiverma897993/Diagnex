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

from .safety import TAU_ABSTAIN, Band, SafetyAssessment

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


def abstention_reason(assessment: SafetyAssessment) -> str:
    """Why an answer was withheld, in one clause.

    Abstention has two distinct causes and they must not be conflated: the
    confidence fell below tau, or the confidence was fine but the predicted
    failure mode was severe enough to override it. Reporting "below the 60%
    threshold" for a 94%-confidence answer is simply false, and a patient
    reading it would draw the wrong conclusion about how sure the model was.
    """
    if assessment.confidence < TAU_ABSTAIN:
        return (
            f"its confidence of {assessment.confidence:.0%} is below the "
            f"{TAU_ABSTAIN:.0%} safety threshold"
        )
    return (
        f"although its confidence is {assessment.confidence:.0%}, the most likely way "
        f"this answer could be wrong is {assessment.likely_error.name.lower()}, which "
        f"carries {assessment.likely_error.risk.value} clinical risk"
    )


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
            f"AI declined to answer this {label} question - {abstention_reason(assessment)}. "
            "Consult a qualified doctor."
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
            f"ANSWER WITHHELD. You asked: \"{question}\". The system will not stand "
            f"behind an answer about this {label} because {abstention_reason(assessment)}."
        )
        lines.append("The answer was withheld by the model's safety rule. A clinician should review the image.")
    else:
        lines.append(
            f"You asked: \"{question}\". The model's answer is \"{answer}\", with "
            f"{assessment.confidence:.0%} model confidence ({assessment.band.value} band). "
            "This score is not the probability that a diagnosis is correct for an individual patient."
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
        f"Estimated failure mode if this answer is wrong: {err.name} "
        f"[{err.code}, {err.risk.value} risk, model score {assessment.likely_error_prob:.0%}]"
        f"{provisional}. In plain terms: {err.plain_english} For example: {err.example}"
    )

    if assessment.danger_zone:
        lines.append(
            "DANGER ZONE FLAG: the model is confident enough to pass the safety gate, "
            "yet its most likely failure mode carries high clinical impact "
            f"(estimated impact score {assessment.expected_cis:.1f}/5.0). "
            "Independent clinical review is needed."
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
