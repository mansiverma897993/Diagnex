"""Probe the three public VQA datasets before writing the unifier.

Run once. Prints each dataset's splits, columns, dtypes and a few example rows
so the normalisation code in unify.py is written against reality rather than
against what the docs claim the schema is.

    python ml/data/inspect_datasets.py
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("HF_HOME", r"D:\diagnex\.hf")

from datasets import get_dataset_config_names, load_dataset  # noqa: E402

DATASETS = [
    "flaviagiammarino/vqa-rad",
    "flaviagiammarino/path-vqa",
    "BoKelvin/SLAKE",
]


def describe(name: str) -> None:
    print("=" * 78)
    print(name)
    print("=" * 78)
    try:
        configs = get_dataset_config_names(name)
        print(f"configs: {configs}")
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        print(f"config lookup failed: {type(exc).__name__}: {exc}")
        configs = [None]

    try:
        ds = load_dataset(name)
    except Exception as exc:  # noqa: BLE001
        print(f"!! load_dataset failed: {type(exc).__name__}: {exc}")
        traceback.print_exc(limit=3)
        return

    for split, data in ds.items():
        print(f"\n--- split={split}  rows={len(data)} ---")
        print("features:")
        for col, feat in data.features.items():
            print(f"    {col:16s} {feat}")
        for i in range(min(3, len(data))):
            row = data[i]
            preview = {}
            for k, v in row.items():
                if hasattr(v, "size") and hasattr(v, "mode"):  # PIL image
                    preview[k] = f"<PIL {v.mode} {v.size}>"
                else:
                    s = str(v)
                    preview[k] = s[:90] + ("..." if len(s) > 90 else "")
            print(f"  [{i}] {preview}")


if __name__ == "__main__":
    targets = sys.argv[1:] or DATASETS
    for name in targets:
        describe(name)
        print()
