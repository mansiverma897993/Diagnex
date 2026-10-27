"""The complete HTTP response must not reveal a refused model prediction."""

import asyncio
import io
import json

from fastapi import UploadFile
from PIL import Image

from backend import main
from backend.app import safety, taxonomy
from backend.app.engine import Analysis


class RefusingEngine:
    def is_medical_image(self, image):
        return True, "xray", 0.9

    def analyze(self, image, question):
        assessment = safety.assess(0.2, {code: 1.0 for code in taxonomy.CODES})
        return Analysis(
            answer="secret finding",
            confidence=0.2,
            assessment=assessment,
            alternatives=[("secret alternative", 0.1)],
            modality="xray",
            modality_confidence=0.9,
        )


def test_upload_and_chat_hide_refused_answers(monkeypatch):
    monkeypatch.setattr(main, "_engine_or_503", lambda: RefusingEngine())
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buffer, format="PNG")
    upload = UploadFile(filename="sample.png", file=io.BytesIO(buffer.getvalue()))

    result = asyncio.run(main.upload(file=upload, category="xray", question="Is there a finding?"))
    encoded = json.dumps(result)
    assert result["answer"] is None
    assert result["alternatives"] == []
    assert "secret finding" not in encoded
    assert "secret alternative" not in encoded

    followup = asyncio.run(main.chat(main.ChatRequest(session_id=result["session_id"], question="What now?")))
    followup_encoded = json.dumps(followup)
    assert followup["answer"] is None
    assert followup["alternatives"] == []
    assert "secret finding" not in followup_encoded
    assert "secret alternative" not in followup_encoded
