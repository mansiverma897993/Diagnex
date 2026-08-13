"""Inference engine: image + question -> safety-gated answer.

Loads the frozen BiomedCLIP towers plus the two trained heads (answer
classifier, error-type predictor) and runs a single query end to end.

Feature construction here must mirror ml/train/train_vqa.py exactly - same
trunk features, same TF-IDF vectoriser, same L2 normalisation, same
temperature. A mismatch would not crash; it would silently produce
miscalibrated confidences, which is the one failure this project cannot
tolerate. `self_check()` verifies the pieces agree at load time.

If artifacts are missing the engine raises rather than falling back to
canned output. A medical tool that invents plausible findings when its model
is absent is worse than one that refuses to start.
"""

from __future__ import annotations

import json
import os
import pickle
import threading
from dataclasses import dataclass
from pathlib import Path

# Same OpenMP guard as ml/features/extract.py - must precede the torch import.
# Without it, building the timm ViT under open_clip crashes the process with a
# Windows access violation rather than raising.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from . import safety, taxonomy

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = Path(os.environ.get("DIAGNEX_ARTIFACTS", REPO_ROOT / "ml" / "artifacts"))
MODEL_ID = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"

#: Zero-shot prompts for modality detection. BiomedCLIP was trained on
#: PubMed figure captions, so caption-like phrasing works better than bare
#: labels ("a chest x-ray radiograph" beats "xray").
MODALITY_PROMPTS: dict[str, str] = {
    "xray": "a chest x-ray radiograph",
    "ct": "an axial computed tomography CT scan slice",
    "mri": "a magnetic resonance MRI scan of the body",
    "ultrasound": "an ultrasound sonogram image",
    "pathology": "a histopathology microscopy slide stained with hematoxylin and eosin",
}


class ArtifactsMissing(RuntimeError):
    """Raised when the engine cannot start because training has not been run."""


@dataclass
class Analysis:
    answer: str
    confidence: float
    assessment: safety.SafetyAssessment
    alternatives: list[tuple[str, float]]
    modality: str
    modality_confidence: float

    def to_dict(self) -> dict:
        d = {
            "answer": self.answer,
            "confidence": round(self.confidence, 4),
            "alternatives": [
                {"answer": a, "probability": round(p, 4)} for a, p in self.alternatives
            ],
            "modality": self.modality,
            "modality_confidence": round(self.modality_confidence, 4),
            "safety": self.assessment.to_dict(),
        }
        # The UI must never render an answer the gate refused.
        if self.assessment.abstain:
            d["answer"] = None
            d["withheld_answer"] = self.answer
        return d


def _l2norm(x: np.ndarray) -> np.ndarray:
    return x / np.clip(np.linalg.norm(x, axis=-1, keepdims=True), 1e-8, None)


class DiagnexEngine:
    def __init__(self, artifact_dir: Path = ARTIFACT_DIR):
        self.artifact_dir = Path(artifact_dir)
        self._lock = threading.Lock()
        self._loaded = False

    # --- loading -----------------------------------------------------------

    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._load_unlocked()
            self._loaded = True

    def _load_unlocked(self) -> None:
        import open_clip

        from ml.train.train_vqa import VQAHead

        required = ["vqa_head.pt", "answer_vocab.json", "tfidf.pkl", "error_predictor.pt"]
        missing = [f for f in required if not (self.artifact_dir / f).exists()]
        if missing:
            raise ArtifactsMissing(
                f"missing artifacts in {self.artifact_dir}: {', '.join(missing)}. "
                "Run: ml/data/build_dataset.py, ml/features/extract.py, "
                "ml/train/train_vqa.py, ml/eval/mine_errors.py"
            )

        self.clip, self.preprocess = open_clip.create_model_from_pretrained(MODEL_ID)
        self.tokenizer = open_clip.get_tokenizer(MODEL_ID)
        self.clip.eval()

        self.vocab: list[str] = json.loads(
            (self.artifact_dir / "answer_vocab.json").read_text(encoding="utf-8")
        )
        with (self.artifact_dir / "tfidf.pkl").open("rb") as fh:
            self.tfidf = pickle.load(fh)

        ckpt = torch.load(self.artifact_dir / "vqa_head.pt", weights_only=False)
        self.vqa = VQAHead(
            ckpt["img_dim"], ckpt["txt_dim"], ckpt["n_answers"], ckpt["hidden"], ckpt["dropout"]
        )
        self.vqa.load_state_dict(ckpt["state_dict"])
        self.vqa.eval()
        self.temperature = float(ckpt["temperature"])
        self.img_dim = int(ckpt["img_dim"])
        self.txt_dim = int(ckpt["txt_dim"])

        ep = torch.load(self.artifact_dir / "error_predictor.pt", weights_only=False)
        self.error_codes: list[str] = list(ep["codes"])
        self.error_net = torch.nn.Sequential(
            torch.nn.Linear(ep["in_dim"], ep["hidden"]),
            torch.nn.GELU(),
            torch.nn.Dropout(0.3),
            torch.nn.LayerNorm(ep["hidden"]),
            torch.nn.Linear(ep["hidden"], len(self.error_codes)),
        )
        self.error_net.load_state_dict(ep["state_dict"])
        self.error_net.eval()

        with torch.no_grad():
            prompts = list(MODALITY_PROMPTS.values())
            emb = self.clip.encode_text(self.tokenizer(prompts)).float().numpy()
        self._modality_keys = list(MODALITY_PROMPTS)
        self._modality_emb = _l2norm(emb)

        self.self_check()

    def self_check(self) -> None:
        """Fail loudly at load time if training and inference disagree."""
        probe = Image.new("RGB", (224, 224), color=(128, 128, 128))
        img = self._embed_image(probe)
        if img.shape[-1] != self.img_dim:
            raise ArtifactsMissing(
                f"image feature dim {img.shape[-1]} != trained {self.img_dim}; "
                "features were extracted with a different backbone configuration"
            )
        txt = self._embed_question("is there a fracture?")
        if txt.shape[-1] != self.txt_dim:
            raise ArtifactsMissing(
                f"question feature dim {txt.shape[-1]} != trained {self.txt_dim}; "
                "the TF-IDF vectoriser does not match the trained head"
            )
        if set(self.error_codes) != set(taxonomy.CODES):
            raise ArtifactsMissing("error predictor classes do not match the taxonomy")

    # --- feature construction (must mirror training) ------------------------

    def _embed_image(self, image: Image.Image) -> np.ndarray:
        tensor = self.preprocess(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            trunk = getattr(getattr(self.clip, "visual", None), "trunk", None)
            if trunk is not None and hasattr(trunk, "forward_features"):
                feats = trunk.forward_features(tensor)
                if feats.ndim == 3 and feats.shape[1] > 1:
                    vec = torch.cat([feats[:, 0], feats[:, 1:].mean(dim=1)], dim=-1)
                    return _l2norm(vec.float().numpy())
            return _l2norm(self.clip.encode_image(tensor).float().numpy())

    def _embed_question(self, question: str) -> np.ndarray:
        with torch.no_grad():
            clip_vec = self.clip.encode_text(self.tokenizer([question])).float().numpy()
        tfidf_vec = self.tfidf.transform([question]).toarray().astype(np.float32)
        return _l2norm(np.hstack([clip_vec, tfidf_vec]))

    # --- public API ---------------------------------------------------------

    def detect_modality(self, image: Image.Image) -> tuple[str, float]:
        """Zero-shot modality tag. Never used to override a user's choice,
        only to flag a mismatch."""
        tensor = self.preprocess(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            emb = _l2norm(self.clip.encode_image(tensor).float().numpy())
        sims = (emb @ self._modality_emb.T)[0]
        probs = np.exp(sims * 100.0 - (sims * 100.0).max())
        probs = probs / probs.sum()
        best = int(probs.argmax())
        return self._modality_keys[best], float(probs[best])

    def analyze(self, image: Image.Image, question: str, top_k: int = 4) -> Analysis:
        if not self._loaded:
            self.load()
        if not question or not question.strip():
            raise ValueError("question must not be empty")

        img_vec = self._embed_image(image)
        txt_vec = self._embed_question(question)

        with torch.no_grad():
            logits = self.vqa(torch.from_numpy(img_vec), torch.from_numpy(txt_vec))
            probs = F.softmax(logits / self.temperature, dim=1)[0]

        k = min(top_k, probs.shape[0])
        top = torch.topk(probs, k)
        answer = self.vocab[int(top.indices[0])]
        confidence = float(top.values[0])
        alternatives = [
            (self.vocab[int(i)], float(p)) for i, p in zip(top.indices[1:], top.values[1:])
        ]

        # Distribution shape features, identical to ml/eval/mine_errors.py.
        p2 = torch.topk(probs, min(2, probs.shape[0])).values
        margin = float(p2[0] - p2[1]) if p2.numel() > 1 else float(p2[0])
        entropy = float(-(probs.clamp_min(1e-12) * probs.clamp_min(1e-12).log()).sum())
        dist = np.array(
            [[confidence, margin, entropy / float(np.log(probs.shape[0])),
              float(confidence < 0.6), float(confidence < 0.85)]],
            dtype=np.float32,
        )
        onehot = np.zeros((1, len(self.vocab)), dtype=np.float32)
        onehot[0, int(top.indices[0])] = 1.0

        with torch.no_grad():
            err_logits = self.error_net(
                torch.from_numpy(np.hstack([img_vec, txt_vec, dist, onehot]).astype(np.float32))
            )
            err_probs = F.softmax(err_logits, dim=1)[0].numpy()

        assessment = safety.assess(
            confidence, {code: float(p) for code, p in zip(self.error_codes, err_probs)}
        )
        modality, modality_conf = self.detect_modality(image)

        return Analysis(
            answer=answer,
            confidence=confidence,
            assessment=assessment,
            alternatives=alternatives,
            modality=modality,
            modality_confidence=modality_conf,
        )


_engine: DiagnexEngine | None = None


def get_engine() -> DiagnexEngine:
    global _engine
    if _engine is None:
        _engine = DiagnexEngine()
    return _engine
