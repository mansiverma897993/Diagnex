"""Regression checks for image-level train/validation/test separation."""

from collections import defaultdict

from ml.data.build_dataset import enforce_image_disjoint_splits


def test_vqa_rad_repartition_is_disjoint_and_deterministic():
    rows = [
        {"dataset": "vqa-rad", "image": f"image-{i}", "split": split}
        for i in range(100)
        for split in ("train", "test")
    ]
    first = [row.copy() for row in rows]
    second = [row.copy() for row in rows]
    enforce_image_disjoint_splits(first)
    enforce_image_disjoint_splits(second)
    assert first == second
    image_splits = defaultdict(set)
    for row in first:
        image_splits[row["image"]].add(row["split"])
    assert all(len(splits) == 1 for splits in image_splits.values())
    assert {row["split"] for row in first} == {"train", "val", "test"}


def test_native_splits_keep_test_image_out_of_training():
    rows = [
        {"dataset": "path-vqa", "image": "same", "split": "train"},
        {"dataset": "path-vqa", "image": "same", "split": "test"},
        {"dataset": "slake", "image": "other", "split": "train"},
    ]
    enforce_image_disjoint_splits(rows)
    assert [row["split"] for row in rows] == ["test", "test", "train"]
