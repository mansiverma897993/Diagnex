"""Image intake: decode uploads, handle DICOM, and strip identifying metadata.

Ethics rule 2 of the project brief is absolute: never store identifiable
patient data. DICOM files routinely carry PatientName, PatientBirthDate,
PatientID, InstitutionName and AccessionNumber in the header, and ordinary
JPEGs carry EXIF that can include GPS coordinates.

Everything here therefore returns a bare PIL image with no metadata attached.
De-identification happens at the boundary, before the pixels reach anything
else, so no downstream code can accidentally persist a patient identifier.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

DICOM_MAGIC_OFFSET = 128
DICOM_MAGIC = b"DICM"
MAX_PIXELS = 64_000_000  # refuse absurd images rather than exhaust memory

#: DICOM tags that identify a patient, institution or visit. Read only to
#: report *that* they were present and removed - the values are never returned.
IDENTIFYING_TAGS = (
    "PatientName", "PatientID", "PatientBirthDate", "PatientAddress",
    "PatientTelephoneNumbers", "OtherPatientIDs", "OtherPatientNames",
    "InstitutionName", "InstitutionAddress", "ReferringPhysicianName",
    "PerformingPhysicianName", "OperatorsName", "AccessionNumber",
    "StudyID", "StudyDate", "StudyTime", "SeriesDate", "AcquisitionDate",
    "ContentDate", "DeviceSerialNumber", "StationName",
)


class UnreadableImage(ValueError):
    """The upload could not be decoded as an image."""


@dataclass
class IntakeResult:
    image: Image.Image
    source_format: str
    #: Names of identifying fields found and discarded. Never their values.
    stripped_fields: list[str] = field(default_factory=list)
    #: Modality reported by the DICOM header, if the file had one.
    declared_modality: str | None = None

    def to_dict(self) -> dict:
        return {
            "source_format": self.source_format,
            "width": self.image.width,
            "height": self.image.height,
            "stripped_fields": self.stripped_fields,
            "declared_modality": self.declared_modality,
            "deidentified": True,
        }


def is_dicom(data: bytes) -> bool:
    return (
        len(data) > DICOM_MAGIC_OFFSET + 4
        and data[DICOM_MAGIC_OFFSET : DICOM_MAGIC_OFFSET + 4] == DICOM_MAGIC
    )


def _window(pixels: np.ndarray, centre: float | None, width: float | None) -> np.ndarray:
    """Map stored DICOM values to 8-bit display range.

    Uses the window centre/width from the header when present - that is the
    radiologist-chosen contrast for the study. Falls back to a percentile
    stretch, which is more robust than min/max against a few hot pixels.
    """
    p = pixels.astype(np.float32)
    if centre is not None and width is not None and width > 0:
        lo, hi = centre - width / 2.0, centre + width / 2.0
    else:
        lo, hi = np.percentile(p, 1.0), np.percentile(p, 99.0)
        if hi <= lo:
            lo, hi = float(p.min()), float(p.max())
    if hi <= lo:
        return np.zeros(p.shape, dtype=np.uint8)
    return (np.clip((p - lo) / (hi - lo), 0.0, 1.0) * 255.0).astype(np.uint8)


def _first(value):
    """DICOM values may be scalars or multi-valued sequences."""
    if value is None:
        return None
    try:
        if isinstance(value, (list, tuple)) or hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
            seq = list(value)
            return float(seq[0]) if seq else None
        return float(value)
    except (TypeError, ValueError):
        return None


def read_dicom(data: bytes) -> IntakeResult:
    import pydicom

    try:
        ds = pydicom.dcmread(io.BytesIO(data), force=True)
    except Exception as exc:  # noqa: BLE001
        raise UnreadableImage(f"could not parse DICOM: {exc}") from exc

    stripped = [tag for tag in IDENTIFYING_TAGS if getattr(ds, tag, None) not in (None, "")]
    declared = str(getattr(ds, "Modality", "") or "").strip().upper() or None

    if not hasattr(ds, "pixel_array"):
        raise UnreadableImage("DICOM file contains no image data")
    try:
        pixels = ds.pixel_array
    except Exception as exc:  # noqa: BLE001 - missing codecs surface here
        raise UnreadableImage(f"could not decode DICOM pixel data: {exc}") from exc

    if pixels.ndim == 3 and pixels.shape[-1] not in (3, 4):
        pixels = pixels[pixels.shape[0] // 2]  # multi-frame: take the middle slice
    if pixels.ndim == 3 and pixels.shape[-1] in (3, 4):
        arr = pixels[..., :3].astype(np.uint8)
    else:
        slope = _first(getattr(ds, "RescaleSlope", None)) or 1.0
        intercept = _first(getattr(ds, "RescaleIntercept", None)) or 0.0
        arr = _window(
            pixels.astype(np.float32) * slope + intercept,
            _first(getattr(ds, "WindowCenter", None)),
            _first(getattr(ds, "WindowWidth", None)),
        )
        if str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
            arr = 255 - arr  # MONOCHROME1 stores inverted greyscale
        arr = np.stack([arr] * 3, axis=-1)

    return IntakeResult(
        image=Image.fromarray(arr, mode="RGB"),
        source_format="DICOM",
        stripped_fields=stripped,
        declared_modality=declared,
    )


def read_upload(data: bytes) -> IntakeResult:
    """Decode an uploaded file into a de-identified RGB image."""
    if not data:
        raise UnreadableImage("empty upload")

    if is_dicom(data):
        return read_dicom(data)

    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format or "unknown"
            if im.width * im.height > MAX_PIXELS:
                raise UnreadableImage(
                    f"image is {im.width}x{im.height}, larger than the {MAX_PIXELS:,} pixel limit"
                )
            im.load()
            # Re-encoding through a fresh array drops EXIF, ICC and any other
            # ancillary chunks; nothing but pixels survives.
            clean = Image.fromarray(np.array(im.convert("RGB")), mode="RGB")
    except UnreadableImage:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UnreadableImage(f"could not decode image: {exc}") from exc

    return IntakeResult(image=clean, source_format=fmt, stripped_fields=[], declared_modality=None)
