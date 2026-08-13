"""Train and calibrate the VQA answer head on cached BiomedCLIP features.

The vision and text towers stay frozen; only this head learns. That is what
lets the whole thing train on a laptop CPU in minutes.

Head architecture - concat + elementwise product:

    image 1536-d ──Linear─┐
                          ├── [i ; t ; i*t] ──MLP──> answer logits
    question (CLIP 512-d  │
      + TF-IDF n-grams) ──┘

The `i*t` term is a low-rank bilinear interaction. Plain concatenation lets the
head learn "questions like this usually have answer X" without ever consulting
the image, which scores deceptively well on medical VQA because answer priors
are strong. The multiplicative term forces image and question to agree.

TF-IDF n-grams sit alongside the CLIP text embedding because contrastive text
encoders represent negation poorly - "is there a mass" and "is there no mass"
land close together in CLIP space. Since negation is itself error category 4.1,
the head needs a representation that separates them.

Calibration: raw softmax is overconfident, so a 0.60 cut on uncalibrated scores
would not carry the meaning the research assigns it. We fit a single temperature
on the validation split by minimising NLL, then report ECE before and after.

    python ml/train/train_vqa.py
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("HF_HOME", r"D:\diagnex\.hf")

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.app import lexicon  # noqa: E402

DATA_ROOT = Path(os.environ.get("DIAGNEX_DATA", r"D:\diagnex\data"))
FEATURE_DIR = DATA_ROOT / "features"
ARTIFACT_DIR = REPO_ROOT / "ml" / "artifacts"

SEED = 20260813


def log(msg: str) -> None:
    print(f"[train] {msg}", flush=True)


# --- Model -----------------------------------------------------------------


class VQAHead(nn.Module):
    def __init__(self, img_dim: int, txt_dim: int, n_answers: int, hidden: int = 512, dropout: float = 0.3):
        super().__init__()
        self.img_proj = nn.Sequential(
            nn.Linear(img_dim, hidden), nn.GELU(), nn.LayerNorm(hidden)
        )
        self.txt_proj = nn.Sequential(
            nn.Linear(txt_dim, hidden), nn.GELU(), nn.LayerNorm(hidden)
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden * 3, hidden * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden * 2),
            nn.Linear(hidden * 2, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, n_answers),
        )

    def forward(self, img: torch.Tensor, txt: torch.Tensor) -> torch.Tensor:
        i = self.img_proj(img)
        t = self.txt_proj(txt)
        return self.classifier(torch.cat([i, t, i * t], dim=-1))


# --- Metrics ---------------------------------------------------------------


def expected_calibration_error(conf: np.ndarray, correct: np.ndarray, bins: int = 15) -> float:
    """Mean gap between confidence and accuracy, weighted by bin population."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if not mask.any():
            continue
        ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Single-parameter temperature scaling (Guo et al., 2017)."""
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.exp().item())


# --- Data ------------------------------------------------------------------


def build_answer_vocab(rows: list[dict], min_count: int, max_answers: int) -> list[str]:
    counts = Counter(r["answer_norm"] for r in rows if r["split"] == "train")
    # yes/no must always be present - they carry the closed questions that the
    # safety module's abnormality rules depend on.
    vocab = ["yes", "no"]
    for ans, n in counts.most_common():
        if ans in ("yes", "no"):
            continue
        if n < min_count or len(vocab) >= max_answers:
            continue
        vocab.append(ans)
    return vocab


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--hidden", type=int, default=512)
    ap.add_argument("--dropout", type=float, default=0.3)
    ap.add_argument("--min-answer-count", type=int, default=3)
    ap.add_argument("--max-answers", type=int, default=1500)
    ap.add_argument("--tfidf-features", type=int, default=3000)
    ap.add_argument("--patience", type=int, default=8)
    args = ap.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    manifest = DATA_ROOT / "manifest.jsonl"
    if not manifest.exists():
        log(f"missing {manifest}; run ml/data/build_dataset.py")
        return 1
    if not (FEATURE_DIR / "images.npy").exists():
        log("missing cached features; run ml/features/extract.py")
        return 1

    rows = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l]
    img_feats = np.load(FEATURE_DIR / "images.npy")
    txt_feats = np.load(FEATURE_DIR / "questions.npy")
    img_index = json.loads((FEATURE_DIR / "image_index.json").read_text(encoding="utf-8"))
    q_index = json.loads((FEATURE_DIR / "question_index.json").read_text(encoding="utf-8"))
    log(f"{len(rows)} rows | image feats {img_feats.shape} | text feats {txt_feats.shape}")

    vocab = build_answer_vocab(rows, args.min_answer_count, args.max_answers)
    ans_to_idx = {a: i for i, a in enumerate(vocab)}
    log(f"answer vocabulary: {len(vocab)} answers")

    for split in ("train", "val", "test"):
        subset = [r for r in rows if r["split"] == split]
        covered = sum(1 for r in subset if r["answer_norm"] in ans_to_idx)
        if subset:
            log(f"  {split}: {len(subset)} rows, vocab covers {covered/len(subset):.1%}")

    # TF-IDF over question text, fitted on train only.
    from sklearn.feature_extraction.text import TfidfVectorizer

    train_questions = [r["question"] for r in rows if r["split"] == "train"]
    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=args.tfidf_features,
        sublinear_tf=True,
        min_df=2,
    )
    tfidf.fit(train_questions)
    log(f"tf-idf features: {len(tfidf.vocabulary_)}")

    all_questions = sorted(q_index, key=lambda q: q_index[q])
    tfidf_mat = tfidf.transform(all_questions).toarray().astype(np.float32)
    txt_combined = np.hstack([txt_feats, tfidf_mat])

    # Normalise both towers; frozen CLIP features have very different scales
    # from TF-IDF counts and the head trains poorly without this.
    def l2norm(x: np.ndarray) -> np.ndarray:
        return x / np.clip(np.linalg.norm(x, axis=1, keepdims=True), 1e-8, None)

    img_feats = l2norm(img_feats)
    txt_combined = l2norm(txt_combined)

    def make_split(split: str, keep_oov: bool):
        idx_i, idx_t, ys, keep = [], [], [], []
        for r in rows:
            if r["split"] != split:
                continue
            in_vocab = r["answer_norm"] in ans_to_idx
            if not in_vocab and not keep_oov:
                continue
            idx_i.append(img_index[r["image"]])
            idx_t.append(q_index[r["question"]])
            ys.append(ans_to_idx.get(r["answer_norm"], -1))
            keep.append(r)
        return (
            torch.from_numpy(img_feats[idx_i]),
            torch.from_numpy(txt_combined[idx_t]),
            torch.tensor(ys, dtype=torch.long),
            keep,
        )

    tr_img, tr_txt, tr_y, _ = make_split("train", keep_oov=False)
    va_img, va_txt, va_y, va_rows = make_split("val", keep_oov=True)
    te_img, te_txt, te_y, te_rows = make_split("test", keep_oov=True)
    log(f"tensors: train {tuple(tr_img.shape)}, val {tuple(va_img.shape)}, test {tuple(te_img.shape)}")

    model = VQAHead(tr_img.shape[1], tr_txt.shape[1], len(vocab), args.hidden, args.dropout)
    n_params = sum(p.numel() for p in model.parameters())
    log(f"head parameters: {n_params/1e6:.2f}M (vision/text towers frozen)")

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    @torch.no_grad()
    def evaluate(img, txt, y):
        model.eval()
        logits = model(img, txt)
        pred = logits.argmax(dim=1)
        # y == -1 marks answers outside the vocabulary: unreachable by
        # construction, and counted as wrong rather than quietly dropped.
        return float((pred == y).float().mean()), logits

    best_acc, best_state, stale = -1.0, None, 0
    n = tr_img.shape[0]
    t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(n)
        total_loss = 0.0
        for start in range(0, n, args.batch_size):
            sel = perm[start : start + args.batch_size]
            opt.zero_grad()
            loss = F.cross_entropy(model(tr_img[sel], tr_txt[sel]), tr_y[sel], label_smoothing=0.05)
            loss.backward()
            opt.step()
            total_loss += float(loss) * len(sel)
        sched.step()

        val_acc, _ = evaluate(va_img, va_txt, va_y)
        marker = ""
        if val_acc > best_acc:
            best_acc, stale = val_acc, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            marker = "  *best"
        else:
            stale += 1
        log(f"epoch {epoch:3d}  loss {total_loss/n:.4f}  val_acc {val_acc:.4f}{marker}")
        if stale >= args.patience:
            log(f"early stop (no val improvement for {args.patience} epochs)")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    log(f"training took {time.time()-t0:.1f}s; best val acc {best_acc:.4f}")

    # --- Calibration -------------------------------------------------------
    model.eval()
    with torch.no_grad():
        val_logits = model(va_img, va_txt)
    cal_mask = va_y >= 0  # temperature is fit only where a true class exists
    temperature = fit_temperature(val_logits[cal_mask], va_y[cal_mask])
    log(f"fitted temperature: {temperature:.4f}")

    def confidences(logits, y, temp):
        probs = F.softmax(logits / temp, dim=1)
        conf, pred = probs.max(dim=1)
        return conf.numpy(), (pred == y).numpy().astype(float)

    for name, temp in (("raw", 1.0), ("calibrated", temperature)):
        c, ok = confidences(val_logits, va_y, temp)
        log(f"  val ECE {name:11s} {expected_calibration_error(c, ok):.4f}  mean_conf {c.mean():.3f}  acc {ok.mean():.3f}")

    # --- Test metrics ------------------------------------------------------
    with torch.no_grad():
        test_logits = model(te_img, te_txt)
    test_probs = F.softmax(test_logits / temperature, dim=1)
    test_conf, test_pred = test_probs.max(dim=1)
    test_correct = (test_pred == te_y).numpy().astype(float)

    metrics: dict = {
        "n_test": len(te_rows),
        "overall_accuracy": float(test_correct.mean()),
        "temperature": temperature,
        "test_ece": expected_calibration_error(test_conf.numpy(), test_correct),
        "answer_vocab_size": len(vocab),
        "head_parameters": int(n_params),
    }
    for key, sel in (
        ("closed", [i for i, r in enumerate(te_rows) if r["answer_type"] == "closed"]),
        ("open", [i for i, r in enumerate(te_rows) if r["answer_type"] == "open"]),
    ):
        if sel:
            metrics[f"{key}_accuracy"] = float(test_correct[sel].mean())
            metrics[f"{key}_n"] = len(sel)
    by_ds: dict = {}
    for ds in sorted({r["dataset"] for r in te_rows}):
        sel = [i for i, r in enumerate(te_rows) if r["dataset"] == ds]
        entry = {"n": len(sel), "accuracy": float(test_correct[sel].mean())}
        for key, want in (("closed", "closed"), ("open", "open")):
            sub = [i for i in sel if te_rows[i]["answer_type"] == want]
            if sub:
                entry[f"{key}_accuracy"] = float(test_correct[sub].mean())
                entry[f"{key}_n"] = len(sub)
        by_ds[ds] = entry
    metrics["by_dataset"] = by_ds

    # Abstention trade-off at the published threshold.
    conf_np = test_conf.numpy()
    for tau in (0.50, 0.60, 0.70, 0.85):
        answered = conf_np >= tau
        metrics[f"tau_{tau:.2f}"] = {
            "answer_rate": float(answered.mean()),
            "accuracy_when_answered": float(test_correct[answered].mean()) if answered.any() else None,
            "errors_removed": float(
                1 - (test_correct[answered] == 0).sum() / max(1, (test_correct == 0).sum())
            ),
        }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "img_dim": tr_img.shape[1],
            "txt_dim": tr_txt.shape[1],
            "hidden": args.hidden,
            "dropout": args.dropout,
            "n_answers": len(vocab),
            "temperature": temperature,
        },
        ARTIFACT_DIR / "vqa_head.pt",
    )
    (ARTIFACT_DIR / "answer_vocab.json").write_text(json.dumps(vocab, indent=0), encoding="utf-8")
    with (ARTIFACT_DIR / "tfidf.pkl").open("wb") as fh:
        pickle.dump(tfidf, fh)
    (ARTIFACT_DIR / "vqa_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    log("=" * 60)
    log(f"TEST accuracy      {metrics['overall_accuracy']:.4f}")
    if "closed_accuracy" in metrics:
        log(f"  closed (yes/no)  {metrics['closed_accuracy']:.4f}  (n={metrics['closed_n']})")
    if "open_accuracy" in metrics:
        log(f"  open-ended       {metrics['open_accuracy']:.4f}  (n={metrics['open_n']})")
    for ds, e in by_ds.items():
        log(f"  {ds:10s}       {e['accuracy']:.4f}  (n={e['n']})")
    log(f"calibrated ECE     {metrics['test_ece']:.4f}")
    t60 = metrics["tau_0.60"]
    log(f"tau=0.60: answers {t60['answer_rate']:.1%} of questions, "
        f"{t60['accuracy_when_answered']:.1%} correct when it does")
    log(f"artifacts -> {ARTIFACT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
