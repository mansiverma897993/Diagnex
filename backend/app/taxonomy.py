"""12-category medical VQA error taxonomy.

Source of truth for the safety module. Eight categories are transcribed directly
from the project research materials (MedSafe_AI_Presentation slide 5 and the
B.Tech project guide section 3.2), including their published prevalence figures.

The guide states the full taxonomy has 12 categories but only enumerates 8
("Full taxonomy has 12 categories - Dr. Dubey will walk you through all of
them"). The remaining four are reconstructed here from the numbering gaps
(1.2, 2.3, 3.4, 4.2) and are flagged `provisional`. They are NOT presented as
published findings anywhere in the UI or reports. When the full taxonomy is
confirmed, edit only the entries whose `source` is Source.PROVISIONAL.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    """Clinical risk tier of an error category."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Source(str, Enum):
    PUBLISHED = "published"
    PROVISIONAL = "provisional"


#: Clinical Impact Score contribution per risk tier, on a 1-5 scale.
#: CRITICAL sits at the ceiling because a missed abnormality (false negative)
#: is the failure mode that delays treatment.
RISK_TO_CIS: dict[Risk, float] = {
    Risk.CRITICAL: 5.0,
    Risk.HIGH: 4.0,
    Risk.MEDIUM: 2.5,
    Risk.LOW: 1.0,
}


@dataclass(frozen=True)
class ErrorCategory:
    code: str
    group: str
    name: str
    plain_english: str
    risk: Risk
    published_rate: float | None
    example: str
    source: Source

    @property
    def cis_weight(self) -> float:
        return RISK_TO_CIS[self.risk]

    @property
    def is_published(self) -> bool:
        return self.source is Source.PUBLISHED


TAXONOMY: tuple[ErrorCategory, ...] = (
    # ---- Group 1: Visual ----------------------------------------------------
    ErrorCategory(
        code="1.1",
        group="Visual",
        name="Anatomical Misidentification",
        plain_english="The AI confused one body part or organ for another.",
        risk=Risk.HIGH,
        published_rate=0.301,
        example='Says "kidney" when the image shows the liver.',
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="1.2",
        group="Visual",
        name="Modality or Plane Confusion",
        plain_english="The AI misread what kind of scan or which viewing angle it is.",
        risk=Risk.MEDIUM,
        published_rate=None,
        example='Says "CT scan" when the image is an MRI, or axial when it is coronal.',
        source=Source.PROVISIONAL,
    ),
    ErrorCategory(
        code="1.3",
        group="Visual",
        name="Spatial Reasoning Failure",
        plain_english="The AI got left and right, or above and below, confused.",
        risk=Risk.HIGH,
        published_rate=0.029,
        example='Says "right lung" when the lesion is on the left.',
        source=Source.PUBLISHED,
    ),
    # ---- Group 2: Semantic --------------------------------------------------
    ErrorCategory(
        code="2.1",
        group="Semantic",
        name="Granularity Mismatch",
        plain_english="The AI gave a vague answer when a specific one was needed.",
        risk=Risk.MEDIUM,
        published_rate=0.124,
        example='Says "chest" instead of "left lower lobe".',
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="2.2",
        group="Semantic",
        name="Category Domain Confusion",
        plain_english="The AI answered about anatomy when asked about disease (or vice versa).",
        risk=Risk.HIGH,
        published_rate=0.190,
        example='Q: "What disease is shown?" A: "Stomach" - an organ, not a disease.',
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="2.3",
        group="Semantic",
        name="Attribute Description Error",
        plain_english="The AI described the wrong property - size, shape, colour or texture.",
        risk=Risk.MEDIUM,
        published_rate=None,
        example='Says "round and well-circumscribed" for an irregular, spiculated mass.',
        source=Source.PROVISIONAL,
    ),
    # ---- Group 3: Detection -------------------------------------------------
    ErrorCategory(
        code="3.1",
        group="Detection",
        name="Abnormality Detection Failure",
        plain_english='The AI said "normal" when there really is a problem.',
        risk=Risk.CRITICAL,
        published_rate=0.132,
        example="Misses a tumour that is present on the scan.",
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="3.2",
        group="Detection",
        name="False Positive Hallucination",
        plain_english="The AI invented a finding that is not actually there.",
        risk=Risk.HIGH,
        published_rate=0.142,
        example='Reports "pneumothorax" on a completely normal chest X-ray.',
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="3.3",
        group="Detection",
        name="Counting Error",
        plain_english="The AI counted the wrong number of structures or findings.",
        risk=Risk.MEDIUM,
        published_rate=0.100,
        example="Says 2 organs are visible when there are 4.",
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="3.4",
        group="Detection",
        name="Localisation Error",
        plain_english="The AI spotted the finding but placed it in the wrong location.",
        risk=Risk.HIGH,
        published_rate=None,
        example='Detects consolidation but reports it in the upper lobe instead of the lower.',
        source=Source.PROVISIONAL,
    ),
    # ---- Group 4: Language --------------------------------------------------
    ErrorCategory(
        code="4.1",
        group="Language",
        name="Negation Comprehension Failure",
        plain_english='The AI misunderstood a "no" or "not" in the question.',
        risk=Risk.HIGH,
        published_rate=0.005,
        example='Q: "Is there NO fracture?" - the AI inverts the meaning.',
        source=Source.PUBLISHED,
    ),
    ErrorCategory(
        code="4.2",
        group="Language",
        name="Question Misinterpretation",
        plain_english="The AI answered a different question from the one that was asked.",
        risk=Risk.MEDIUM,
        published_rate=None,
        example='Q: "Which side is affected?" A: "Yes" - a yes/no reply to a location question.',
        source=Source.PROVISIONAL,
    ),
)

#: Per-dataset error signatures reported in the source research
#: (MedSafe_AI_Presentation slide 6, "3 Domain-Specific Error Signatures").
#: The aggregate distribution is not the right comparison for our model,
#: because our training mix is 78% PathVQA and the published aggregate is not.
#: Comparing per dataset is like for like. `danger_zone` is the share of that
#: dataset's errors the research places in the confident-and-wrong quadrant.
PUBLISHED_SIGNATURES: dict[str, dict] = {
    "vqa-rad": {
        "label": "Radiology - detection-dominated",
        "rates": {"3.2": 0.373, "3.1": 0.227},
        "danger_zone": 0.53,
    },
    "path-vqa": {
        "label": "Histopathology - recognition-dominated",
        "rates": {"1.1": 0.317, "2.2": 0.216},
        "danger_zone": 0.26,
    },
    "slake": {
        "label": "Mixed radiology - spatial/counting",
        "rates": {"1.3": 0.208, "3.3": 0.100},
        "danger_zone": 0.17,
    },
}

BY_CODE: dict[str, ErrorCategory] = {c.code: c for c in TAXONOMY}
CODES: tuple[str, ...] = tuple(c.code for c in TAXONOMY)

assert len(TAXONOMY) == 12, "taxonomy must define exactly 12 categories"
assert len(BY_CODE) == 12, "duplicate error codes in taxonomy"


def get(code: str) -> ErrorCategory:
    """Look up a category by code, e.g. ``get("3.1")``."""
    try:
        return BY_CODE[code]
    except KeyError:
        raise KeyError(f"unknown error code {code!r}; known codes: {', '.join(CODES)}") from None


def published_categories() -> tuple[ErrorCategory, ...]:
    return tuple(c for c in TAXONOMY if c.is_published)
