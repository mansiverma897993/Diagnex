"""Download VQA-RAD + SLAKE + PathVQA and unify them into one manifest.

Produces, under DATA_ROOT (default D:\\diagnex\\data):

    images/<sha1>.jpg     every unique image, content-addressed
    manifest.jsonl        one JSON record per question-answer pair
    answer_vocab.json     the closed answer set the classifier predicts over
    build_report.json     counts, per-dataset stats, what was skipped and why

Content-addressing the images matters: PathVQA repeats the same slide across
dozens of QA pairs, so hashing collapses ~32k rows onto ~5k files and the
BiomedCLIP feature extraction (the expensive CPU step) runs once per image
rather than once per question.

Resumable - each dataset writes a .done marker, so re-running skips finished
work. Safe to interrupt.

    python ml/data/build_dataset.py
    python ml/data/build_dataset.py --only path-vqa      # retry one source
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import shutil
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

os.environ.setdefault("HF_HOME", r"D:\diagnex\.hf")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from PIL import ImageFile  # noqa: E402

from backend.app import lexicon  # noqa: E402

# PathVQA ships a handful of truncated TIFFs. Without this, a single bad byte
# stream aborts a 32k-row build; with it, Pillow returns what it could decode
# and genuinely unreadable rows are skipped and counted below.
ImageFile.LOAD_TRUNCATED_IMAGES = True

DATA_ROOT = Path(os.environ.get("DIAGNEX_DATA", r"D:\diagnex\data"))
IMAGE_DIR = DATA_ROOT / "images"
MANIFEST = DATA_ROOT / "manifest.jsonl"
MARKER_DIR = DATA_ROOT / ".markers"

VAL_FRACTION = 0.10  # carved from train for datasets with no native val split
SEED = 20260813
MAX_RETRIES = 5


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def retry(fn, what: str, attempts: int = MAX_RETRIES):
    """Run fn() with exponential backoff. The HF connection here is flaky."""
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we genuinely want to retry anything
            if i == attempts:
                raise
            wait = min(60, 2**i)
            log(f"{what} failed ({type(exc).__name__}: {str(exc)[:120]}); retry {i}/{attempts - 1} in {wait}s")
            time.sleep(wait)
    raise AssertionError("unreachable")


def save_image(img) -> str:
    """Write a PIL image to the content-addressed store, return its sha1 stem.

    Deduplication is the content hash and nothing else. An earlier version
    memoised on ``id(img)`` to skip re-encoding; that is unsound, because
    CPython recycles object ids once a decoded image is garbage collected, so
    consecutive rows could collide and two different scans would be stored
    under one hash. Re-encoding every row is the cheap, correct option.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    raw = buf.getvalue()
    sha = hashlib.sha1(raw).hexdigest()

    dest = IMAGE_DIR / f"{sha}.jpg"
    if not dest.exists():
        dest.write_bytes(raw)
    return sha


def record(
    *,
    sid: str,
    dataset: str,
    image: str,
    question: str,
    answer: str,
    split: str,
    modality: str = "",
    location: str = "",
    content_type: str = "",
) -> dict | None:
    """Build one unified manifest row, or None if the row is unusable."""
    q = (question or "").strip()
    a_norm = lexicon.normalize_answer(answer)
    if not q or not a_norm:
        return None

    if not modality:
        modality = lexicon.infer_modality(q, answer)
    modality = modality.strip().lower() or "unknown"
    # Fold dataset-specific modality spellings onto our canonical tags.
    modality = {
        "x-ray": "xray", "xray": "xray", "cxr": "xray",
        "ct": "ct", "ct scan": "ct",
        "mri": "mri", "mr": "mri",
        "ultrasound": "ultrasound", "us": "ultrasound",
        "pathology": "pathology", "histology": "pathology",
    }.get(modality, modality)

    return {
        "sid": sid,
        "dataset": dataset,
        "image": image,
        "question": q,
        "answer": answer.strip(),
        "answer_norm": a_norm,
        "answer_type": "closed" if lexicon.is_closed(answer) else "open",
        "modality": modality,
        "location": (location or "").strip().lower(),
        "content_type": (content_type or "").strip(),
        "split": split,
    }


def assign_val(rows: list[dict], rng: random.Random) -> None:
    """Carve a val split out of train, grouped by image.

    Grouping by image is the point: VQA-RAD asks ~7 questions about each scan,
    so a naive per-row split would put the same image in train and val and
    inflate validation accuracy.
    """
    train_images = sorted({r["image"] for r in rows if r["split"] == "train"})
    rng.shuffle(train_images)
    n_val = max(1, int(len(train_images) * VAL_FRACTION))
    val_images = set(train_images[:n_val])
    for r in rows:
        if r["split"] == "train" and r["image"] in val_images:
            r["split"] = "val"


def enforce_image_disjoint_splits(rows: list[dict]) -> None:
    """Keep every image in exactly one split within each dataset.

    The published VQA-RAD question split reuses images across train and test.
    Repartition its images deterministically so a test image is genuinely unseen.
    Other datasets retain their supplied splits; any duplicated image is moved
    wholly to the most protected split (test, then val, then train).
    """
    by_dataset: dict[str, list[dict]] = {}
    for row in rows:
        by_dataset.setdefault(row["dataset"], []).append(row)

    for dataset, subset in by_dataset.items():
        if dataset == "vqa-rad":
            images = sorted({row["image"] for row in subset})
            random.Random(SEED).shuffle(images)
            n_test = max(1, round(len(images) * 0.20))
            n_val = max(1, round(len(images) * 0.10))
            test_images = set(images[:n_test])
            val_images = set(images[n_test:n_test + n_val])
            for row in subset:
                image = row["image"]
                row["split"] = "test" if image in test_images else "val" if image in val_images else "train"
        else:
            priority = {"train": 0, "val": 1, "test": 2}
            final = {}
            for row in subset:
                image, split = row["image"], row["split"]
                if image not in final or priority[split] > priority[final[image]]:
                    final[image] = split
            for row in subset:
                row["split"] = final[row["image"]]

        image_splits: dict[str, set[str]] = {}
        for row in subset:
            image_splits.setdefault(row["image"], set()).add(row["split"])
        if any(len(splits) != 1 for splits in image_splits.values()):
            raise AssertionError(f"{dataset} contains images in multiple splits")


# --- Per-dataset builders --------------------------------------------------


def build_vqa_rad() -> list[dict]:
    from datasets import load_dataset

    ds = retry(lambda: load_dataset("flaviagiammarino/vqa-rad"), "vqa-rad download")
    rows: list[dict] = []
    for split, data in ds.items():
        split_name = "train" if split == "train" else "test"
        for i, row in enumerate(data):
            sha = save_image(row["image"])
            rec = record(
                sid=f"vqarad-{split}-{i}",
                dataset="vqa-rad",
                image=sha,
                question=row["question"],
                answer=row["answer"],
                split=split_name,
            )
            if rec:
                rows.append(rec)
        log(f"vqa-rad/{split}: {len(data)} rows")
    assign_val(rows, random.Random(SEED))
    return rows


def build_path_vqa() -> list[dict]:
    from datasets import load_dataset

    ds = retry(lambda: load_dataset("flaviagiammarino/path-vqa"), "path-vqa download")
    rows: list[dict] = []
    corrupt = 0
    for split, data in ds.items():
        split_name = {"train": "train", "validation": "val", "val": "val", "test": "test"}.get(split, split)
        for i in range(len(data)):
            # Decoding happens lazily on __getitem__, so a corrupt image raises
            # here rather than at load time. Skip the row, keep the build.
            try:
                row = data[i]
                sha = save_image(row["image"])
            except (OSError, ValueError) as exc:
                corrupt += 1
                if corrupt <= 5:
                    log(f"  skipping unreadable image at {split}[{i}]: {type(exc).__name__}")
                continue
            rec = record(
                sid=f"pathvqa-{split}-{i}",
                dataset="path-vqa",
                image=sha,
                question=row["question"],
                answer=row["answer"],
                split=split_name,
                modality="pathology",
            )
            if rec:
                rows.append(rec)
        log(f"path-vqa/{split}: {len(data)} rows")
    if corrupt:
        log(f"path-vqa: skipped {corrupt} rows with undecodable images")
    return rows


def build_slake() -> list[dict]:
    """SLAKE ships QA rows as JSON and images separately in imgs.zip."""
    from huggingface_hub import hf_hub_download

    extract_dir = DATA_ROOT / "_slake_imgs"
    if not (extract_dir / "imgs").exists():
        log("fetching SLAKE imgs.zip (212 MB)")
        zip_path = retry(
            lambda: hf_hub_download(
                repo_id="BoKelvin/SLAKE", filename="imgs.zip", repo_type="dataset"
            ),
            "slake imgs.zip",
        )
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
        log("imgs.zip extracted")

    # The archive may or may not nest under an "imgs/" directory.
    img_root = extract_dir / "imgs"
    if not img_root.exists():
        img_root = extract_dir

    from datasets import load_dataset
    from PIL import Image

    ds = retry(lambda: load_dataset("BoKelvin/SLAKE"), "slake json")
    rows: list[dict] = []
    sha_by_name: dict[str, str] = {}
    missing = 0

    for split, data in ds.items():
        split_name = {"train": "train", "validation": "val", "test": "test"}.get(split, split)
        kept = 0
        for row in data:
            # SLAKE is bilingual; the English half is what we train on.
            if str(row.get("q_lang", "en")).lower() != "en":
                continue
            name = row["img_name"]
            sha = sha_by_name.get(name)
            if sha is None:
                path = img_root / name
                if not path.exists():
                    missing += 1
                    continue
                with Image.open(path) as im:
                    sha = save_image(im)
                sha_by_name[name] = sha
            rec = record(
                sid=f"slake-{split}-{row['qid']}",
                dataset="slake",
                image=sha,
                question=row["question"],
                answer=row["answer"],
                split=split_name,
                modality=str(row.get("modality", "")),
                location=str(row.get("location", "")),
                content_type=str(row.get("content_type", "")),
            )
            if rec:
                rows.append(rec)
                kept += 1
        log(f"slake/{split}: kept {kept} English rows")

    if missing:
        log(f"WARNING: {missing} SLAKE rows dropped, image file not found in archive")
    return rows


BUILDERS = {
    "vqa-rad": build_vqa_rad,
    "slake": build_slake,
    "path-vqa": build_path_vqa,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(BUILDERS), help="build a single source")
    ap.add_argument("--force", action="store_true", help="ignore .done markers")
    args = ap.parse_args()

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    MARKER_DIR.mkdir(parents=True, exist_ok=True)

    targets = [args.only] if args.only else list(BUILDERS)
    report: dict = {"datasets": {}}

    for name in targets:
        marker = MARKER_DIR / f"{name}.done"
        shard = DATA_ROOT / f"_shard_{name}.jsonl"
        if marker.exists() and shard.exists() and not args.force:
            log(f"{name}: already built, skipping (use --force to rebuild)")
            continue
        log(f"=== building {name} ===")
        try:
            rows = BUILDERS[name]()
        except Exception as exc:  # noqa: BLE001
            log(f"!! {name} FAILED: {type(exc).__name__}: {exc}")
            report["datasets"][name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            continue
        with shard.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        marker.write_text(str(len(rows)), encoding="utf-8")
        log(f"{name}: wrote {len(rows)} rows")

    # --- merge every available shard into the manifest ---------------------
    all_rows: list[dict] = []
    for name in BUILDERS:
        shard = DATA_ROOT / f"_shard_{name}.jsonl"
        if not shard.exists():
            log(f"NOTE: {name} shard missing, manifest will not include it")
            report["datasets"].setdefault(name, {"status": "missing"})
            continue
        rows = [json.loads(line) for line in shard.read_text(encoding="utf-8").splitlines() if line]
        all_rows.extend(rows)

    if not all_rows:
        log("no data built; aborting before writing manifest")
        return 1

    enforce_image_disjoint_splits(all_rows)

    for name in BUILDERS:
        rows = [r for r in all_rows if r["dataset"] == name]
        if not rows:
            continue
        splits = Counter(r["split"] for r in rows)
        report["datasets"][name] = {
            "status": "ok",
            "rows": len(rows),
            "images": len({r["image"] for r in rows}),
            "splits": dict(splits),
            "closed": sum(1 for r in rows if r["answer_type"] == "closed"),
            "open": sum(1 for r in rows if r["answer_type"] == "open"),
        }

    with MANIFEST.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    report["total_rows"] = len(all_rows)
    report["total_images"] = len({r["image"] for r in all_rows})
    report["splits"] = dict(Counter(r["split"] for r in all_rows))
    report["split_protocol"] = "image-disjoint; VQA-RAD images repartitioned 70/10/20"
    global_splits: dict[str, set[str]] = {}
    for row in all_rows:
        global_splits.setdefault(row["image"], set()).add(row["split"])
    report["image_split_overlap"] = sum(len(splits) > 1 for splits in global_splits.values())
    if report["image_split_overlap"]:
        raise ValueError("cross-dataset image overlap across splits")
    report["modalities"] = dict(Counter(r["modality"] for r in all_rows).most_common())
    (DATA_ROOT / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    log(f"manifest: {len(all_rows)} rows over {report['total_images']} unique images")
    log(f"splits: {report['splits']}")
    log(f"images on disk: {sum(1 for _ in IMAGE_DIR.glob('*.jpg'))}")
    log(f"disk used by images: {shutil.disk_usage(DATA_ROOT).used // 2**30} GB total on volume")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

