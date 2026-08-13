"""Cache frozen BiomedCLIP embeddings for every image and question.

This is the one expensive step in the pipeline, and it runs exactly once. After
this, training the answer head is a matter of minutes on CPU because the
vision transformer never runs again during training.

BiomedCLIP (microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224) is a
CLIP trained on 15M biomedical image-text pairs from PubMed Central, so its
image tower already understands radiographs and histology slides. That is what
makes a frozen-encoder approach viable here - a general-purpose ImageNet
backbone would not be.

Image features are 1536-d: the ViT CLS token concatenated with the mean of the
patch tokens, both taken *before* the CLIP projection head. The pre-projection
768-d space retains detail that the 512-d contrastive projection discards, and
mean-pooled patches carry coarse spatial information that a CLS token alone
loses. Falls back to the 512-d projected embedding if the model structure
differs from what we expect.

    python ml/features/extract.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HOME", r"D:\diagnex\.hf")

# Must be set before torch is imported. Building the timm ViT under open_clip
# otherwise dies with a Windows access violation inside nn.Linear.__init__:
# torch and MKL each load their own OpenMP runtime (libiomp5md.dll), and the
# duplicate initialisation corrupts the allocator. Plain timm.create_model does
# not trip it, which is why the crash only appears on the open_clip path.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Thread count is configured through the environment, never through
# torch.set_num_threads(). Resizing the OpenMP pool after torch has loaded and
# then constructing the timm ViT reliably faults here (0xC0000005); setting it
# before import is stable. run_extract.py passes this through.
os.environ.setdefault("OMP_NUM_THREADS", os.environ.get("DIAGNEX_THREADS", "8"))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

DATA_ROOT = Path(os.environ.get("DIAGNEX_DATA", r"D:\diagnex\data"))
IMAGE_DIR = DATA_ROOT / "images"
MANIFEST = DATA_ROOT / "manifest.jsonl"
FEATURE_DIR = DATA_ROOT / "features"

MODEL_ID = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"


def log(msg: str) -> None:
    print(f"[extract] {msg}", flush=True)


def load_model():
    import open_clip

    log(f"loading {MODEL_ID} (first run downloads ~800 MB)")
    model, preprocess = open_clip.create_model_from_pretrained(MODEL_ID)
    tokenizer = open_clip.get_tokenizer(MODEL_ID)
    model.eval()
    torch.set_grad_enabled(False)
    return model, preprocess, tokenizer


def image_embedder(model):
    """Return a callable batch -> np.ndarray, using rich features when possible."""
    trunk = getattr(getattr(model, "visual", None), "trunk", None)
    can_use_trunk = trunk is not None and hasattr(trunk, "forward_features")

    if can_use_trunk:
        # Verify the trunk really yields token sequences before committing.
        try:
            probe = trunk.forward_features(torch.zeros(1, 3, 224, 224))
            ok = probe.ndim == 3 and probe.shape[1] > 1
        except Exception as exc:  # noqa: BLE001
            log(f"trunk probe failed ({type(exc).__name__}), using projected embedding")
            ok = False
        if ok:
            dim = probe.shape[-1] * 2
            log(f"using pre-projection trunk features, dim={dim}")

            def embed(batch: torch.Tensor) -> np.ndarray:
                feats = trunk.forward_features(batch)
                cls = feats[:, 0]
                mean = feats[:, 1:].mean(dim=1)
                return torch.cat([cls, mean], dim=-1).float().numpy()

            return embed, dim

    log("using projected 512-d encode_image embedding")

    def embed(batch: torch.Tensor) -> np.ndarray:
        return model.encode_image(batch).float().numpy()

    return embed, 512


def _progress_path(name: str) -> Path:
    return FEATURE_DIR / f"{name}.progress"


def _open_memmap(name: str, rows: int, dim: int) -> np.memmap:
    """Checkpoint store that survives a process crash.

    torch on this machine intermittently dies with a Windows access violation
    (exit code 0xC0000005) partway through a long forward-pass loop. A native
    crash cannot be caught in Python, so progress has to be durable on disk and
    the work resumable - see run_extract.py, which restarts until complete.
    """
    path = FEATURE_DIR / f"{name}.partial.npy"
    mode = "r+" if path.exists() else "w+"
    return np.lib.format.open_memmap(path, mode=mode, dtype=np.float32, shape=(rows, dim))


def _read_progress(name: str) -> int:
    p = _progress_path(name)
    if not p.exists():
        return 0
    try:
        return int(p.read_text().strip())
    except ValueError:
        return 0


def extract_images(model, preprocess, shas: list[str], batch_size: int) -> np.ndarray:
    embed, dim = image_embedder(model)
    out = _open_memmap("images", len(shas), dim)
    done = _read_progress("images")
    if done:
        log(f"resuming images from {done}/{len(shas)}")

    t0, started_at = time.time(), done
    for start in range(done, len(shas), batch_size):
        chunk = shas[start : start + batch_size]
        tensors = []
        for sha in chunk:
            with Image.open(IMAGE_DIR / f"{sha}.jpg") as im:
                tensors.append(preprocess(im.convert("RGB")))
        out[start : start + len(chunk)] = embed(torch.stack(tensors))

        finished = start + len(chunk)
        out.flush()
        _progress_path("images").write_text(str(finished))

        if finished % (batch_size * 10) < batch_size or finished == len(shas):
            rate = (finished - started_at) / max(1e-6, time.time() - t0)
            eta = (len(shas) - finished) / max(1e-6, rate)
            log(f"images {finished}/{len(shas)}  {rate:.1f}/s  eta {eta/60:.1f} min")
    return np.asarray(out)


def extract_texts(model, tokenizer, texts: list[str], batch_size: int) -> np.ndarray:
    with torch.no_grad():
        dim = model.encode_text(tokenizer(texts[:1])).shape[1]
    out = _open_memmap("questions", len(texts), dim)
    done = _read_progress("questions")
    if done:
        log(f"resuming questions from {done}/{len(texts)}")

    t0, started_at = time.time(), done
    for start in range(done, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        out[start : start + len(chunk)] = model.encode_text(tokenizer(chunk)).float().numpy()

        finished = start + len(chunk)
        out.flush()
        _progress_path("questions").write_text(str(finished))

        if finished % (batch_size * 20) < batch_size or finished == len(texts):
            rate = (finished - started_at) / max(1e-6, time.time() - t0)
            log(f"texts {finished}/{len(texts)}  {rate:.1f}/s")
    return np.asarray(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    # Deliberately no torch.set_num_threads() call - see the OMP_NUM_THREADS
    # note at the top of this file. Set DIAGNEX_THREADS to change it.
    log(f"torch threads = {torch.get_num_threads()}")

    if not MANIFEST.exists():
        log(f"missing {MANIFEST}; run ml/data/build_dataset.py first")
        return 1

    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
    shas = sorted({r["image"] for r in rows})
    questions = sorted({r["question"] for r in rows})
    log(f"{len(rows)} rows -> {len(shas)} unique images, {len(questions)} unique questions")

    FEATURE_DIR.mkdir(parents=True, exist_ok=True)
    img_npy = FEATURE_DIR / "images.npy"
    txt_npy = FEATURE_DIR / "questions.npy"

    if img_npy.exists() and txt_npy.exists() and not args.force:
        log("features already cached; use --force to recompute")
        return 0

    model, preprocess, tokenizer = load_model()

    log("encoding images")
    img_feats = extract_images(model, preprocess, shas, args.batch_size)
    np.save(img_npy, img_feats)
    (FEATURE_DIR / "image_index.json").write_text(
        json.dumps({sha: i for i, sha in enumerate(shas)}), encoding="utf-8"
    )

    log("encoding questions")
    txt_feats = extract_texts(model, tokenizer, questions, args.batch_size * 4)
    np.save(txt_npy, txt_feats)
    (FEATURE_DIR / "question_index.json").write_text(
        json.dumps({q: i for i, q in enumerate(questions)}), encoding="utf-8"
    )

    (FEATURE_DIR / "meta.json").write_text(
        json.dumps(
            {
                "model": MODEL_ID,
                "image_dim": int(img_feats.shape[1]),
                "text_dim": int(txt_feats.shape[1]),
                "n_images": len(shas),
                "n_questions": len(questions),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Both final arrays are written, so the crash-resume scratch is now dead
    # weight (and would otherwise be resumed from on a later --force run).
    for name in ("images", "questions"):
        (FEATURE_DIR / f"{name}.partial.npy").unlink(missing_ok=True)
        _progress_path(name).unlink(missing_ok=True)

    log(f"done: images {img_feats.shape}, questions {txt_feats.shape}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
