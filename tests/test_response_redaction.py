"""An abstained model answer must not be serialized in the API payload."""

import json

from backend.app import safety, taxonomy
from backend.app.engine import Analysis


def test_abstention_removes_predicted_answer_and_alternatives():
    probs = {code: 1.0 for code in taxonomy.CODES}
    assessment = safety.assess(0.2, probs)
    result = Analysis(
        answer="secret predicted diagnosis",
        confidence=0.2,
        assessment=assessment,
        alternatives=[("secret alternative", 0.1)],
        modality="xray",
        modality_confidence=0.7,
    )
    payload = result.to_dict()
    encoded = json.dumps(payload)
    assert payload["answer"] is None
    assert payload["alternatives"] == []
    assert "secret predicted diagnosis" not in encoded
    assert "secret alternative" not in encoded
