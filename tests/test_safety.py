"""Tests for the traffic-light safety gate.

These encode the guarantees the project is evaluated on, so a regression here
should fail loudly rather than quietly change clinical behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import safety, taxonomy  # noqa: E402
from backend.app.safety import Band  # noqa: E402


def flat_errors(**overrides: float) -> dict[str, float]:
    """Uniform error distribution, with named codes overridden."""
    probs = {code: 0.01 for code in taxonomy.CODES}
    probs.update(overrides)
    return probs


def benign() -> dict[str, float]:
    """Error mass on a MEDIUM-risk category, so risk never forces a downgrade."""
    return flat_errors(**{"2.1": 0.9})


# --- threshold behaviour ---------------------------------------------------


def test_high_confidence_benign_error_is_green():
    a = safety.assess(0.95, benign())
    assert a.band is Band.GREEN
    assert not a.abstain
    assert a.show_answer


def test_mid_confidence_is_yellow():
    a = safety.assess(0.70, benign())
    assert a.band is Band.YELLOW
    assert not a.abstain


def test_below_tau_abstains():
    a = safety.assess(0.59, benign())
    assert a.band is Band.RED
    assert a.abstain
    assert not a.show_answer


@pytest.mark.parametrize("conf", [0.60, 0.6001])
def test_tau_boundary_is_inclusive(conf):
    """tau=0.60 answers; the research quotes retention *at* the threshold."""
    assert not safety.assess(conf, benign()).abstain


def test_just_below_tau_does_not_answer():
    assert safety.assess(0.5999, benign()).abstain


def test_green_boundary():
    assert safety.assess(0.85, benign()).band is Band.GREEN
    assert safety.assess(0.8499, benign()).band is Band.YELLOW


# --- risk-driven downgrades ------------------------------------------------


def test_likely_critical_error_forces_red_despite_high_confidence():
    """The core safety property: a confident missed abnormality is still RED."""
    a = safety.assess(0.97, flat_errors(**{"3.1": 0.5}))
    assert a.band is Band.RED
    assert a.abstain
    assert "critical" in a.downgrade_reason.lower()


def test_critical_below_override_threshold_does_not_force_red():
    a = safety.assess(0.97, flat_errors(**{"3.1": 0.1, "2.1": 0.5}))
    assert a.band is not Band.RED


def test_high_risk_error_downgrades_green_to_yellow():
    a = safety.assess(0.95, flat_errors(**{"1.1": 0.9}))  # anatomical, HIGH
    assert a.band is Band.YELLOW
    assert a.downgrade_reason is not None


def test_danger_zone_flags_confident_but_severe():
    a = safety.assess(0.95, flat_errors(**{"1.1": 0.9}))
    assert a.danger_zone, "confident + high-impact failure mode is the danger zone"


def test_no_danger_zone_when_abstaining_on_low_confidence():
    a = safety.assess(0.30, flat_errors(**{"1.1": 0.9}))
    assert not a.danger_zone, "an abstained answer never reaches the patient"


def test_benign_high_confidence_is_not_danger_zone():
    assert not safety.assess(0.95, benign()).danger_zone


# --- CIS -------------------------------------------------------------------


def test_expected_cis_matches_risk_weights():
    critical_only = {code: 0.0 for code in taxonomy.CODES}
    critical_only["3.1"] = 1.0
    assert safety.expected_cis(critical_only) == pytest.approx(5.0)

    medium_only = {code: 0.0 for code in taxonomy.CODES}
    medium_only["2.1"] = 1.0
    assert safety.expected_cis(medium_only) == pytest.approx(2.5)


def test_probabilities_are_renormalised():
    doubled = {code: 0.02 for code in taxonomy.CODES}
    doubled["2.1"] = 1.8
    a = safety.assess(0.9, doubled)
    assert sum(p for _, p in a.error_ranking) == pytest.approx(1.0)


# --- input validation ------------------------------------------------------


@pytest.mark.parametrize("conf", [-0.01, 1.01])
def test_out_of_range_confidence_rejected(conf):
    with pytest.raises(ValueError, match="confidence"):
        safety.assess(conf, benign())


def test_missing_taxonomy_code_rejected():
    partial = {code: 0.1 for code in list(taxonomy.CODES)[:5]}
    with pytest.raises(ValueError, match="missing taxonomy codes"):
        safety.assess(0.9, partial)


def test_all_zero_probabilities_rejected():
    with pytest.raises(ValueError, match="positive probability"):
        safety.assess(0.9, {code: 0.0 for code in taxonomy.CODES})


# --- serialisation ---------------------------------------------------------


def test_to_dict_is_json_safe():
    import json

    payload = json.dumps(safety.assess(0.9, benign()).to_dict())
    assert "likely_error" in payload
    assert "expected_cis" in payload


def test_to_dict_marks_provisional_categories():
    a = safety.assess(0.9, flat_errors(**{"3.4": 0.9}))  # provisional category
    assert a.to_dict()["likely_error"]["provisional"] is True

    b = safety.assess(0.9, flat_errors(**{"3.1": 0.005, "1.1": 0.9}))
    assert b.to_dict()["likely_error"]["provisional"] is False


# --- taxonomy integrity ----------------------------------------------------


def test_abstention_reason_distinguishes_its_two_causes():
    """A high-confidence risk override must not be reported as "below 60%".

    Both causes end in an abstention, but conflating them tells the patient the
    model was unsure when it was in fact 94% sure and overridden on risk.
    """
    from backend.app.report import abstention_reason

    low = safety.assess(0.30, benign())
    assert low.abstain
    text = abstention_reason(low)
    assert "below" in text and "60%" in text

    override = safety.assess(0.94, flat_errors(**{"3.1": 0.5}))
    assert override.abstain, "a likely critical failure must force abstention"
    text = abstention_reason(override)
    assert "below" not in text
    assert "94%" in text
    assert "CRITICAL" in text


def test_abstention_reason_never_misstates_confidence():
    from backend.app.report import abstention_reason

    for conf in (0.62, 0.75, 0.88, 0.99):
        a = safety.assess(conf, flat_errors(**{"3.1": 0.6}))
        if a.abstain:
            assert f"{conf:.0%}" in abstention_reason(a)
            assert "below the 60% safety threshold" not in abstention_reason(a)


def test_taxonomy_has_twelve_unique_categories():
    assert len(taxonomy.TAXONOMY) == 12
    assert len({c.code for c in taxonomy.TAXONOMY}) == 12


def test_exactly_one_critical_category():
    critical = [c for c in taxonomy.TAXONOMY if c.risk is taxonomy.Risk.CRITICAL]
    assert [c.code for c in critical] == ["3.1"], "missed abnormality is the critical failure"


def test_published_rates_match_source_materials():
    """Guards against silent edits to figures quoted from the research."""
    expected = {"1.1": 0.301, "1.3": 0.029, "2.1": 0.124, "2.2": 0.190,
                "3.1": 0.132, "3.2": 0.142, "3.3": 0.100, "4.1": 0.005}
    for code, rate in expected.items():
        assert taxonomy.get(code).published_rate == pytest.approx(rate)


def test_provisional_categories_have_no_published_rate():
    for c in taxonomy.TAXONOMY:
        if not c.is_published:
            assert c.published_rate is None, f"{c.code} is provisional but quotes a rate"
