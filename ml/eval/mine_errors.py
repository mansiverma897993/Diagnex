"""Mine a labelled error corpus and train the 12-way error-type predictor.

Pipeline:

    val split  -> model predicts -> keep wrong ones -> rule-label into 12
                  categories -> train error predictor
    test split -> same, held out -> report predictor accuracy

The predictor never sees the gold answer, because at inference time there isn't
one. Its inputs are exactly what the server has at request time: the image
embedding, the question embedding, the predicted answer, and the shape of the
probability distribution (confidence, entropy, top-2 margin). It answers the
question "*if* this prediction is wrong, how is it most likely wrong?" - which
is what feeds the Clinical Impact Score and the traffic light.

Validation without ground truth: SLAKE annotates every question with a
`content_type` (Organ / Abnormality / Position / Modality / ...) assigned by its
authors, entirely independently of us. `agreement_against_slake` scores our rule
labeller against it, so the corpus comes with an honest quality number instead
of an assumption.

    python ml/eval/mine_errors.py
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("HF_HOME", r"D:\diagnex\.hf")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.app import taxonomy  # noqa: E402
from ml.eval.error_rules import agreement_against_slake, label_error  # noqa: E402
from ml.train.train_vqa import VQAHead  # noqa: E402

DATA_ROOT = Path(os.environ.get("DIAGNEX_DATA", r"D:\diagnex\data"))
FEATURE_DIR = DATA_ROOT / "features"
ARTIFACT_DIR = REPO_ROOT / "ml" / "artifacts"


def log(msg: str) -> None:
    print(f"[errors] {msg}", flush=True)


def distribution_features(probs: torch.Tensor) -> np.ndarray:
    """Shape-of-uncertainty features, independent of which answer won.

    Confidence alone cannot distinguish "one clear winner" from "two plausible
    answers tied"; entropy and margin can, and those correspond to different
    failure modes.
    """
    top2 = probs.topk(2, dim=1).values
    conf = top2[:, 0]
    margin = top2[:, 0] - top2[:, 1]
    entropy = -(probs.clamp_min(1e-12) * probs.clamp_min(1e-12).log()).sum(dim=1)
    max_entropy = float(np.log(probs.shape[1]))
    return torch.stack(
        [conf, margin, entropy / max_entropy, (conf < 0.6).float(), (conf < 0.85).float()], dim=1
    ).numpy()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=256)
    args = ap.parse_args()

    ckpt_path = ARTIFACT_DIR / "vqa_head.pt"
    if not ckpt_path.exists():
        log("missing ml/artifacts/vqa_head.pt; run ml/train/train_vqa.py first")
        return 1

    rows = [
        json.loads(l)
        for l in (DATA_ROOT / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if l
    ]
    img_feats = np.load(FEATURE_DIR / "images.npy")
    txt_feats = np.load(FEATURE_DIR / "questions.npy")
    img_index = json.loads((FEATURE_DIR / "image_index.json").read_text(encoding="utf-8"))
    q_index = json.loads((FEATURE_DIR / "question_index.json").read_text(encoding="utf-8"))

    vocab = json.loads((ARTIFACT_DIR / "answer_vocab.json").read_text(encoding="utf-8"))
    with (ARTIFACT_DIR / "tfidf.pkl").open("rb") as fh:
        tfidf = pickle.load(fh)
    ckpt = torch.load(ckpt_path, weights_only=False)

    all_questions = sorted(q_index, key=lambda q: q_index[q])
    tfidf_mat = tfidf.transform(all_questions).toarray().astype(np.float32)
    txt_combined = np.hstack([txt_feats, tfidf_mat])

    def l2norm(x):
        return x / np.clip(np.linalg.norm(x, axis=1, keepdims=True), 1e-8, None)

    img_feats, txt_combined = l2norm(img_feats), l2norm(txt_combined)

    model = VQAHead(ckpt["img_dim"], ckpt["txt_dim"], ckpt["n_answers"], ckpt["hidden"], ckpt["dropout"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    temperature = ckpt["temperature"]

    def predict(split: str):
        sel = [r for r in rows if r["split"] == split]
        ii = [img_index[r["image"]] for r in sel]
        ti = [q_index[r["question"]] for r in sel]
        with torch.no_grad():
            logits = model(
                torch.from_numpy(img_feats[ii]), torch.from_numpy(txt_combined[ti])
            )
        probs = F.softmax(logits / temperature, dim=1)
        conf, pred = probs.max(dim=1)
        return sel, probs, conf.numpy(), pred.numpy(), np.array(ii), np.array(ti)

    corpora: dict[str, list[dict]] = {}
    for split in ("val", "test"):
        sel, probs, conf, pred, ii, ti = predict(split)
        dist = distribution_features(probs)
        errors = []
        for k, r in enumerate(sel):
            predicted = vocab[pred[k]]
            if predicted == r["answer_norm"]:
                continue
            lbl = label_error(r["question"], r["answer"], predicted)
            errors.append(
                {
                    **{key: r[key] for key in ("sid", "dataset", "question", "answer", "modality", "content_type")},
                    "predicted": predicted,
                    "confidence": float(conf[k]),
                    "error_code": lbl.code,
                    "rule": lbl.rule,
                    "rule_confident": lbl.confident,
                    "_img": int(ii[k]),
                    "_txt": int(ti[k]),
                    "_ans": int(pred[k]),
                    "_dist": dist[k].tolist(),
                }
            )
        corpora[split] = errors
        rate = len(errors) / max(1, len(sel))
        log(f"{split}: {len(sel)} rows, {len(errors)} errors ({rate:.1%})")

    train_err, test_err = corpora["val"], corpora["test"]
    if len(train_err) < 50:
        log(f"only {len(train_err)} errors to learn from; predictor will be unreliable")

    # --- Corpus quality ----------------------------------------------------
    dist_counts = Counter(e["error_code"] for e in train_err + test_err)
    total = sum(dist_counts.values())
    unconfident = sum(1 for e in train_err + test_err if not e["rule_confident"])
    log(f"rule coverage: {1 - unconfident/max(1,total):.1%} matched a positive rule")

    slake_rows = [e for e in train_err + test_err if e["dataset"] == "slake" and e.get("content_type")]
    agreement = agreement_against_slake(slake_rows)
    if agreement["agreement"] is not None:
        log(f"labeller agreement vs SLAKE content_type: {agreement['agreement']:.1%} (n={agreement['scored']})")

    log("error distribution (ours vs published):")
    for cat in taxonomy.TAXONOMY:
        ours = dist_counts.get(cat.code, 0) / max(1, total)
        pub = f"{cat.published_rate:.1%}" if cat.published_rate is not None else "  n/a"
        flag = "" if cat.is_published else "  (provisional category)"
        log(f"  {cat.code} {cat.name[:34]:34s} ours {ours:6.1%}   published {pub}{flag}")

    # --- Train the predictor ----------------------------------------------
    code_to_idx = {c: i for i, c in enumerate(taxonomy.CODES)}
    n_answers = len(vocab)

    def featurise(errs):
        img = img_feats[[e["_img"] for e in errs]]
        txt = txt_combined[[e["_txt"] for e in errs]]
        dist = np.array([e["_dist"] for e in errs], dtype=np.float32)
        ans = np.zeros((len(errs), n_answers), dtype=np.float32)
        ans[np.arange(len(errs)), [e["_ans"] for e in errs]] = 1.0
        x = np.hstack([img, txt, dist, ans]).astype(np.float32)
        y = np.array([code_to_idx[e["error_code"]] for e in errs], dtype=np.int64)
        return torch.from_numpy(x), torch.from_numpy(y)

    xtr, ytr = featurise(train_err)
    xte, yte = featurise(test_err)
    log(f"predictor inputs: train {tuple(xtr.shape)}, test {tuple(xte.shape)}")

    net = torch.nn.Sequential(
        torch.nn.Linear(xtr.shape[1], args.hidden),
        torch.nn.GELU(),
        torch.nn.Dropout(0.3),
        torch.nn.LayerNorm(args.hidden),
        torch.nn.Linear(args.hidden, len(taxonomy.CODES)),
    )
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=1e-4)

    # Rare categories (negation is 0.5% in the published data) would otherwise
    # never be predicted at all.
    counts = np.bincount(ytr.numpy(), minlength=len(taxonomy.CODES)).astype(np.float32)
    weights = torch.from_numpy((counts.sum() / np.clip(counts, 1, None)) ** 0.5)

    best, best_state = -1.0, None
    for epoch in range(1, args.epochs + 1):
        net.train()
        opt.zero_grad()
        loss = F.cross_entropy(net(xtr), ytr, weight=weights)
        loss.backward()
        opt.step()
        if epoch % 5 == 0 or epoch == args.epochs:
            net.eval()
            with torch.no_grad():
                acc = float((net(xte).argmax(1) == yte).float().mean()) if len(yte) else float("nan")
            if acc > best:
                best, best_state = acc, {k: v.clone() for k, v in net.state_dict().items()}
            log(f"  epoch {epoch:3d}  loss {float(loss):.4f}  test_acc {acc:.4f}")

    if best_state:
        net.load_state_dict(best_state)

    metrics = {
        "n_train_errors": len(train_err),
        "n_test_errors": len(test_err),
        "predictor_test_accuracy": best,
        "rule_coverage": 1 - unconfident / max(1, total),
        "slake_agreement": agreement,
        "error_distribution": {c: dist_counts.get(c, 0) / max(1, total) for c in taxonomy.CODES},
        "published_distribution": {
            c.code: c.published_rate for c in taxonomy.TAXONOMY if c.published_rate is not None
        },
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": net.state_dict(), "in_dim": int(xtr.shape[1]), "hidden": args.hidden,
         "codes": list(taxonomy.CODES), "n_answers": n_answers},
        ARTIFACT_DIR / "error_predictor.pt",
    )
    (ARTIFACT_DIR / "error_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    strip = lambda e: {k: v for k, v in e.items() if not k.startswith("_")}  # noqa: E731
    (DATA_ROOT / "error_corpus.jsonl").write_text(
        "\n".join(json.dumps(strip(e), ensure_ascii=False) for e in train_err + test_err),
        encoding="utf-8",
    )

    log("=" * 60)
    log(f"error corpus: {len(train_err) + len(test_err)} labelled errors -> data/error_corpus.jsonl")
    log(f"predictor test accuracy: {best:.4f} over 12 classes (chance = {1/12:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
