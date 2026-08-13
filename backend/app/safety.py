"""Honest-uncertainty safety gate.

Implements the traffic-light + abstention policy described in the project
research materials:

    tau = 0.60 eliminates 51.1% of critical errors while retaining 91.8% of
    correct answers.

Two inputs drive every decision:

1. ``confidence`` - the *calibrated* probability of the top answer. Calibration
   matters more than it sounds: a raw softmax from a classification head is
   systematically overconfident, so a 0.60 cut on uncalibrated scores does not
   mean what the research says it means. See ``ml/train/calibrate.py``.
2. ``error_probs`` - the 12-way distribution from the error-type predictor,
   i.e. "*if* this answer is wrong, how is it most likely wrong?"

The second input is what separates this from a plain threshold: a 0.90-confidence
answer whose most likely failure mode is CRITICAL (a missed abnormality) is more
dangerous than a 0.70-confidence answer that would only be vague. The research
calls that the "danger zone" - wrong *and* highly confident - and puts 26.8% of
all errors there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from . import taxonomy
from .taxonomy import ErrorCategory, Risk

# --- Thresholds ------------------------------------------------------------
# Published in the research materials; do not tune these casually, the 51.1% /
# 91.8% trade-off quoted throughout the project is measured at exactly tau=0.60.

#: Abstention threshold. Below this the system refuses to answer.
TAU_ABSTAIN = 0.60
#: At or above this the answer is shown without a verification prompt.
TAU_GREEN = 0.85
#: Expected Clinical Impact Score at or above which an error is "severe".
#: Deliberately below 4.0, the CIS weight of a HIGH-risk category. Expected CIS
#: is a probability-weighted average over all 12 categories, so it only reaches
#: 4.0 when essentially the entire distribution sits on HIGH or CRITICAL - even
#: 90% mass on a HIGH category yields ~3.94. Setting the bar at 4.0 would make
#: the danger-zone detector almost inert. 3.5 reads as "on balance the likely
#: failure modes are severe", which is the intended meaning.
CIS_SEVERE = 3.5
#: A predicted CRITICAL failure mode this likely forces RED regardless of
#: confidence - the whole point is that a confident miss is the worst outcome.
CRITICAL_OVERRIDE_PROB = 0.30


class Band(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass(frozen=True)
class SafetyAssessment:
    band: Band
    confidence: float
    abstain: bool
    #: True when the model is confident enough to pass the gate but the likely
    #: failure mode is severe. These are the cases that hurt patients.
    danger_zone: bool
    expected_cis: float
    likely_error: ErrorCategory
    likely_error_prob: float
    #: Human-readable reason the band was downgraded, if it was.
    downgrade_reason: str | None
    message: str
    error_ranking: list[tuple[ErrorCategory, float]] = field(default_factory=list)

    @property
    def show_answer(self) -> bool:
        """Whether the UI may display the answer as a finding."""
        return not self.abstain

    def to_dict(self) -> dict:
        return {
            "band": self.band.value,
            "confidence": round(self.confidence, 4),
            "abstain": self.abstain,
            "danger_zone": self.danger_zone,
            "expected_cis": round(self.expected_cis, 3),
            "message": self.message,
            "downgrade_reason": self.downgrade_reason,
            "likely_error": {
                "code": self.likely_error.code,
                "name": self.likely_error.name,
                "group": self.likely_error.group,
                "plain_english": self.likely_error.plain_english,
                "risk": self.likely_error.risk.value,
                "example": self.likely_error.example,
                "probability": round(self.likely_error_prob, 4),
                "provisional": not self.likely_error.is_published,
            },
            "error_ranking": [
                {
                    "code": c.code,
                    "name": c.name,
                    "risk": c.risk.value,
                    "probability": round(p, 4),
                }
                for c, p in self.error_ranking
            ],
        }


_GREEN_MSG = (
    "High confidence result. The AI is quite certain about this answer. "
    "This is a screening aid, not a diagnosis."
)
_YELLOW_MSG = (
    "Moderate confidence. We suggest verifying this with your doctor, "
    "especially before making any health decisions."
)
_RED_MSG = (
    "The AI is not confident enough to give a reliable answer for this "
    "question. Please consult a qualified doctor."
)


def expected_cis(error_probs: dict[str, float]) -> float:
    """Probability-weighted Clinical Impact Score across the 12 categories.

    Answers the question "if this is wrong, how bad is it likely to be?" on the
    same 1-5 scale as ``taxonomy.RISK_TO_CIS``.
    """
    return sum(p * taxonomy.get(code).cis_weight for code, p in error_probs.items())


def assess(confidence: float, error_probs: dict[str, float]) -> SafetyAssessment:
    """Apply the traffic-light policy.

    Args:
        confidence: calibrated probability of the top answer, in [0, 1].
        error_probs: 12-way distribution over taxonomy codes. Need not sum to
            exactly 1 (it is renormalised), but must cover every code.

    Raises:
        ValueError: if ``confidence`` is out of range or a taxonomy code is
            missing, since silently guessing here would undermine the gate.
    """
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0, 1], got {confidence!r}")

    missing = set(taxonomy.CODES) - set(error_probs)
    if missing:
        raise ValueError(f"error_probs missing taxonomy codes: {sorted(missing)}")

    total = sum(error_probs.values())
    if total <= 0:
        raise ValueError("error_probs must contain at least one positive probability")
    probs = {code: error_probs[code] / total for code in taxonomy.CODES}

    ranking = sorted(
        ((taxonomy.get(code), p) for code, p in probs.items()),
        key=lambda pair: pair[1],
        reverse=True,
    )
    top_error, top_prob = ranking[0]
    cis = expected_cis(probs)

    # Base band from calibrated confidence alone.
    if confidence >= TAU_GREEN:
        band = Band.GREEN
    elif confidence >= TAU_ABSTAIN:
        band = Band.YELLOW
    else:
        band = Band.RED

    downgrade_reason: str | None = None

    # A likely CRITICAL failure mode overrides confidence entirely. This is the
    # rule that catches "confidently says normal while missing a tumour".
    critical_mass = sum(
        p for code, p in probs.items() if taxonomy.get(code).risk is Risk.CRITICAL
    )
    if critical_mass >= CRITICAL_OVERRIDE_PROB and band is not Band.RED:
        downgrade_reason = (
            f"A critical failure mode ({top_error.name.lower()}) is likely enough "
            f"({critical_mass:.0%}) that we will not stand behind this answer."
        )
        band = Band.RED
    elif band is Band.GREEN and top_error.risk is Risk.HIGH and cis >= CIS_SEVERE:
        downgrade_reason = (
            f"Confidence is high, but the most likely way this answer could be "
            f"wrong is {top_error.name.lower()}, which carries high clinical risk."
        )
        band = Band.YELLOW

    message = {Band.GREEN: _GREEN_MSG, Band.YELLOW: _YELLOW_MSG, Band.RED: _RED_MSG}[band]

    return SafetyAssessment(
        band=band,
        confidence=confidence,
        abstain=band is Band.RED,
        # Confident enough to pass the gate, yet the likely failure is severe.
        danger_zone=confidence >= TAU_ABSTAIN and cis >= CIS_SEVERE,
        expected_cis=cis,
        likely_error=top_error,
        likely_error_prob=top_prob,
        downgrade_reason=downgrade_reason,
        message=message,
        error_ranking=ranking,
    )
