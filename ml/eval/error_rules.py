"""Rule-based labeller that sorts model mistakes into the 12 taxonomy categories.

This is the stand-in for Dr. Dubey's 1,975-error annotated dataset. Rather than
hand-annotating, we run the trained model over held-out data, take every wrong
prediction, and classify *how* it was wrong using deterministic rules over the
question, the gold answer and the predicted answer.

Two properties make this defensible rather than a fudge:

1. Every rule is a stated, inspectable clinical criterion - not a black box. An
   examiner can read `rule_abnormality_miss` and check it against case 3.1 in
   the taxonomy.
2. SLAKE carries a `content_type` field (Organ / Abnormality / Position /
   Modality / Shape / Color / Quantity / Plane) that was annotated by the SLAKE
   authors, independently of us. `agreement_against_slake()` scores our rules
   against it, giving an honest accuracy number for the labeller itself.

Rule order matters and is not arbitrary: the safety-critical detection failures
are tested before the softer semantic ones, so a missed tumour is never
downgraded to "vague answer".
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app import lexicon  # noqa: E402

#: SLAKE content_type -> the taxonomy codes a mistake on that question could
#: plausibly fall into. Used only for scoring the labeller, never for labelling.
SLAKE_CONTENT_EXPECTED: dict[str, set[str]] = {
    "Modality": {"1.2"},
    "Plane": {"1.2"},
    "Organ": {"1.1", "2.2"},
    "Position": {"1.3", "3.4"},
    "Abnormality": {"3.1", "3.2", "2.2"},
    "Shape": {"2.3"},
    "Color": {"2.3"},
    "Size": {"2.3", "2.1"},
    "Quantity": {"3.3"},
    "KG": {"2.2", "2.1"},
}

_OPPOSED_POSITIONS: tuple[tuple[str, str], ...] = (
    ("upper", "lower"),
    ("superior", "inferior"),
    ("anterior", "posterior"),
    ("proximal", "distal"),
    ("medial", "lateral"),
    ("central", "peripheral"),
    ("apex", "base"),
    ("apical", "basal"),
    ("above", "below"),
    ("top", "bottom"),
    ("cranial", "caudal"),
    ("dorsal", "ventral"),
)


@dataclass(frozen=True)
class ErrorLabel:
    code: str
    rule: str
    #: False when we fell through to the residual rule, i.e. the label is a
    #: best guess rather than a positive match. Reported honestly in metrics.
    confident: bool


def _opposed_position(gold: set[str], pred: set[str]) -> bool:
    for a, b in _OPPOSED_POSITIONS:
        if (a in gold and b in pred) or (b in gold and a in pred):
            return True
    return False


def _is_vaguer(pred: str, gold: str) -> bool:
    """True when `pred` is a less specific version of `gold`.

    "lung" for "left lower lobe of lung" is a granularity failure, not an
    anatomical misidentification - the model was right, just not useful.
    """
    p, g = set(lexicon.tokens(pred)), set(lexicon.tokens(gold))
    if not p or not g:
        return False
    return p < g or (bool(p & g) and len(p) < len(g))


# --- Individual rules ------------------------------------------------------
# Each takes (question, gold, pred) and returns a taxonomy code or None.


def rule_negation(q: str, gold: str, pred: str) -> str | None:
    """4.1 - question carries a negation and the model inverted a yes/no."""
    if not lexicon.has_negation(q):
        return None
    g, p = lexicon.normalize_answer(gold), lexicon.normalize_answer(pred)
    if {g, p} == {"yes", "no"}:
        return "4.1"
    return None


def rule_abnormality_miss(q: str, gold: str, pred: str) -> str | None:
    """3.1 CRITICAL - a real finding was called normal."""
    g, p = lexicon.normalize_answer(gold), lexicon.normalize_answer(pred)
    if g == "yes" and p == "no":
        return "3.1"
    if lexicon.is_abnormality(gold) and lexicon.is_normal_claim(pred):
        return "3.1"
    return None


def rule_false_positive(q: str, gold: str, pred: str) -> str | None:
    """3.2 - the model invented a finding on a normal study."""
    g, p = lexicon.normalize_answer(gold), lexicon.normalize_answer(pred)
    if g == "no" and p == "yes":
        return "3.2"
    if lexicon.is_normal_claim(gold) and lexicon.is_abnormality(pred):
        return "3.2"
    return None


def rule_counting(q: str, gold: str, pred: str) -> str | None:
    """3.3 - a counting question answered with the wrong number."""
    if not lexicon.question_starts_with(q, lexicon.COUNT_STEMS):
        return None
    gc, pc = lexicon.count_of(gold), lexicon.count_of(pred)
    if gc is not None and pc is not None and gc != pc:
        return "3.3"
    return "3.3" if gc is not None or pc is not None else None


def rule_spatial(q: str, gold: str, pred: str) -> str | None:
    """1.3 - left/right flipped, or an opposed positional term."""
    gl, pl = lexicon.laterality_of(gold), lexicon.laterality_of(pred)
    if gl and pl and gl != pl:
        return "1.3"
    if _opposed_position(set(lexicon.tokens(gold)), set(lexicon.tokens(pred))):
        return "1.3"
    return None


def rule_modality_plane(q: str, gold: str, pred: str) -> str | None:
    """1.2 - wrong scan type or wrong viewing plane."""
    if lexicon.question_starts_with(q, lexicon.MODALITY_STEMS):
        return "1.2"
    if lexicon.question_starts_with(q, lexicon.PLANE_STEMS):
        return "1.2"
    gt, pt = set(lexicon.tokens(gold)), set(lexicon.tokens(pred))
    if (gt & lexicon.PLANE) and (pt & lexicon.PLANE):
        return "1.2"
    all_modality = set().union(*lexicon.MODALITY_TERMS.values())
    if (gt & all_modality) and (pt & all_modality):
        return "1.2"
    return None


def rule_localisation(q: str, gold: str, pred: str) -> str | None:
    """3.4 - the finding is real but placed in the wrong spot."""
    if not lexicon.question_starts_with(q, lexicon.LOCATION_STEMS):
        return None
    gt, pt = set(lexicon.tokens(gold)), set(lexicon.tokens(pred))
    locational = lexicon.ANATOMY | lexicon.POSITIONAL | lexicon.LATERALITY
    if (gt & locational) and (pt & locational):
        return "3.4"
    return None


def rule_anatomy_mixup(q: str, gold: str, pred: str) -> str | None:
    """1.1 - the depicted entity mistaken for *another* entity.

    Matches organ-for-organ, tissue-for-tissue and lesion-for-lesion
    confusions. The broad reading follows the source research, which reports
    31.7% of PathVQA errors as "Anatomical Misidentification" on a
    histopathology corpus containing almost no gross anatomy - see
    lexicon.is_medical_entity.

    Naming a less specific structure ("lobe" for "left lower lobe") is not a
    misidentification: the model named the right thing, just too coarsely. That
    is category 2.1, and it carries MEDIUM rather than HIGH risk, so the
    distinction changes the safety band. Defer those to rule_granularity.
    """
    if _is_vaguer(pred, gold):
        return None
    if lexicon.is_medical_entity(gold) and lexicon.is_medical_entity(pred):
        if lexicon.normalize_answer(gold) != lexicon.normalize_answer(pred):
            return "1.1"
    return None


def rule_category_domain(q: str, gold: str, pred: str) -> str | None:
    """2.2 - answered anatomy when asked disease, or the reverse."""
    asked_disease = lexicon.question_starts_with(q, lexicon.DISEASE_STEMS)
    asked_anatomy = lexicon.question_starts_with(q, lexicon.ANATOMY_STEMS)
    if asked_disease and lexicon.is_anatomy(pred) and not lexicon.is_abnormality(pred):
        return "2.2"
    if asked_anatomy and lexicon.is_abnormality(pred) and not lexicon.is_anatomy(pred):
        return "2.2"
    if lexicon.is_abnormality(gold) and lexicon.is_anatomy(pred) and not lexicon.is_abnormality(pred):
        return "2.2"
    if lexicon.is_anatomy(gold) and lexicon.is_abnormality(pred) and not lexicon.is_anatomy(pred):
        return "2.2"
    return None


def rule_granularity(q: str, gold: str, pred: str) -> str | None:
    """2.1 - right idea, wrong level of detail."""
    return "2.1" if _is_vaguer(pred, gold) else None


def rule_attribute(q: str, gold: str, pred: str) -> str | None:
    """2.3 - wrong size / shape / colour / texture descriptor."""
    if lexicon.question_starts_with(q, lexicon.ATTRIBUTE_STEMS):
        return "2.3"
    if lexicon.is_attribute(gold) and lexicon.is_attribute(pred):
        return "2.3"
    return None


def rule_question_misread(q: str, gold: str, pred: str) -> str | None:
    """4.2 - answered a different question than the one asked."""
    g_closed, p_closed = lexicon.is_closed(gold), lexicon.is_closed(pred)
    if g_closed != p_closed:
        return "4.2"
    return None


#: Evaluated top to bottom; first match wins. Safety-critical detection
#: failures precede softer semantic ones by design.
RULES: tuple = (
    ("negation", rule_negation),
    ("abnormality_miss", rule_abnormality_miss),
    ("false_positive", rule_false_positive),
    ("counting", rule_counting),
    ("spatial", rule_spatial),
    ("modality_plane", rule_modality_plane),
    ("localisation", rule_localisation),
    ("category_domain", rule_category_domain),
    ("anatomy_mixup", rule_anatomy_mixup),
    ("attribute", rule_attribute),
    ("granularity", rule_granularity),
    ("question_misread", rule_question_misread),
)


def label_error(question: str, gold: str, pred: str) -> ErrorLabel:
    """Classify a single wrong prediction into one of the 12 categories."""
    for name, fn in RULES:
        code = fn(question, gold, pred)
        if code is not None:
            return ErrorLabel(code=code, rule=name, confident=True)

    # Residual: nothing matched positively. Route by whatever signal the
    # question form still offers, rather than tipping every unmatched error
    # into one bucket - doing that inflates a single category and makes the
    # resulting distribution meaningless.
    stem_routes = (
        (lexicon.COUNT_STEMS, "3.3", "residual_count"),
        (lexicon.LOCATION_STEMS, "3.4", "residual_location"),
        (lexicon.MODALITY_STEMS, "1.2", "residual_modality"),
        (lexicon.PLANE_STEMS, "1.2", "residual_plane"),
        (lexicon.ATTRIBUTE_STEMS, "2.3", "residual_attribute"),
        (lexicon.DISEASE_STEMS, "2.2", "residual_disease"),
        (lexicon.ANATOMY_STEMS, "1.1", "residual_anatomy"),
    )
    for stems, code_, rule in stem_routes:
        if lexicon.question_starts_with(question, stems):
            return ErrorLabel(code_, rule, confident=False)

    if lexicon.is_closed(gold) != lexicon.is_closed(pred):
        return ErrorLabel("4.2", "residual_type_mismatch", confident=False)
    if lexicon.is_closed(gold):
        return ErrorLabel("4.2", "residual_closed", confident=False)
    # One side names something concrete and the other does not: the model
    # answered in the wrong register, which is a domain confusion.
    if lexicon.is_medical_entity(gold) != lexicon.is_medical_entity(pred):
        return ErrorLabel("2.2", "residual_domain", confident=False)
    return ErrorLabel("2.1", "residual_open", confident=False)


def agreement_against_slake(rows: list[dict]) -> dict:
    """Score the labeller against SLAKE's independent content_type annotations.

    `rows` are error records carrying `content_type`, `question`, `answer` and
    `predicted`. Returns coverage and agreement, so the labeller's own accuracy
    can be reported rather than assumed.
    """
    total = hits = 0
    per_type: dict[str, list[int]] = {}
    for r in rows:
        ctype = (r.get("content_type") or "").strip()
        expected = SLAKE_CONTENT_EXPECTED.get(ctype)
        if not expected:
            continue
        label = label_error(r["question"], r["answer"], r["predicted"])
        ok = int(label.code in expected)
        total += 1
        hits += ok
        per_type.setdefault(ctype, [0, 0])
        per_type[ctype][0] += ok
        per_type[ctype][1] += 1
    return {
        "scored": total,
        "agreement": (hits / total) if total else None,
        "per_content_type": {
            k: {"agreement": v[0] / v[1], "n": v[1]} for k, v in sorted(per_type.items())
        },
    }
