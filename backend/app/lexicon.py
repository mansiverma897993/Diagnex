"""Medical term lexicons and answer normalisation.

Shared by the training-time error labeller (``ml/eval/error_rules.py``) and by
runtime inference, so that "is this answer an anatomy word?" means exactly the
same thing in both places. If those two ever drift apart, the error-type
predictor is calibrated against a labelling rule the server no longer applies.

The vocabularies are deliberately small and hand-curated rather than pulled from
UMLS: every term here appears in VQA-RAD / SLAKE / PathVQA answers, and a
curated list is auditable by a human examiner, which a 3-million-concept
ontology is not.
"""

from __future__ import annotations

import re
import unicodedata

# --- Answer normalisation --------------------------------------------------

_ARTICLES = {"a", "an", "the"}
_PUNCT_RE = re.compile(r"[^\w\s%<>/+-]")
_WS_RE = re.compile(r"\s+")

#: Surface forms that mean yes / no across the three datasets.
_YES = {"yes", "y", "yeah", "yep", "true", "present", "positive"}
_NO = {"no", "n", "nope", "false", "absent", "negative", "none"}


def normalize_answer(text: str) -> str:
    """Canonical form of a free-text answer.

    Lowercases, strips accents and punctuation, drops articles, collapses
    whitespace, and folds yes/no synonyms. Keeps ``%``, ``<``, ``>``, ``/``,
    ``+`` and ``-`` because they carry meaning in measurements and gradings.
    """
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    tokens = [t for t in s.split() if t not in _ARTICLES]
    s = " ".join(tokens)
    if s in _YES:
        return "yes"
    if s in _NO:
        return "no"
    return s


def is_closed(answer: str) -> bool:
    """True for yes/no answers - the "closed" question type in the literature."""
    return normalize_answer(answer) in {"yes", "no"}


# --- Term categories -------------------------------------------------------

ANATOMY: frozenset[str] = frozenset(
    """
    lung lungs liver kidney kidneys heart brain stomach spleen pancreas gallbladder
    bladder colon intestine bowel duodenum esophagus esophagous trachea bronchus
    aorta artery arteries vein veins ventricle atrium myocardium pericardium
    diaphragm rib ribs sternum clavicle scapula humerus femur tibia fibula pelvis
    spine vertebra vertebrae spinal cord skull cranium mandible maxilla sinus sinuses
    thyroid adrenal prostate uterus ovary ovaries testis breast lymph node nodes
    cerebellum cerebrum thalamus hippocampus ventricles cortex white matter grey matter
    gray matter frontal lobe temporal lobe parietal lobe occipital lobe brainstem
    pituitary appendix rectum ureter urethra muscle tendon ligament cartilage bone
    skin epidermis dermis mucosa submucosa serosa endometrium cervix placenta
    abdomen thorax chest head neck extremity limb arm leg hand foot shoulder knee
    hip elbow wrist ankle joint airway pleura pleural space mediastinum hilum
    """.split()
)

ABNORMALITY: frozenset[str] = frozenset(
    """
    pneumonia pneumothorax effusion edema oedema consolidation infiltrate atelectasis
    emphysema fibrosis cardiomegaly mass lesion tumor tumour cancer carcinoma sarcoma
    lymphoma metastasis metastases nodule cyst abscess hematoma haemorrhage hemorrhage
    bleed infarct infarction ischemia ischaemia stroke thrombus embolism aneurysm
    stenosis occlusion calcification fracture dislocation arthritis osteoporosis
    hernia obstruction perforation inflammation infection sepsis necrosis fistula
    ulcer polyp adenoma hyperplasia dysplasia neoplasia neoplasm melanoma glioma
    meningioma hydrocephalus atrophy gliosis demyelination sclerosis cirrhosis
    steatosis hepatomegaly splenomegaly ascites pleural effusion opacity opacities
    granuloma tuberculosis covid fibroid hemangioma haemangioma inflammatory
    """.split()
)

#: Tissue, cell and histology terms. PathVQA answers name these constantly and
#: they are neither "anatomy" (an organ) nor "abnormality" (a disease), so
#: without them a large share of pathology errors match no rule at all.
TISSUE: frozenset[str] = frozenset(
    """
    epithelium epithelial endothelium endothelial stroma stromal parenchyma
    connective adipose fibrous muscular smooth skeletal cardiac squamous
    columnar cuboidal glandular acinar ductal lobular tubular alveolar
    cell cells nucleus nuclei nucleoli cytoplasm membrane basement lumen
    lymphocyte lymphocytes neutrophil neutrophils macrophage macrophages
    eosinophil eosinophils plasma erythrocyte erythrocytes fibroblast
    fibroblasts myocyte hepatocyte keratin collagen elastin mucin glycogen
    villi crypt crypts gland glands follicle follicles septa septum trabeculae
    capsule cortex medulla papilla sinusoid canaliculi tubule glomerulus
    """.split()
)

MODALITY_TERMS: dict[str, frozenset[str]] = {
    "xray": frozenset("xray x-ray radiograph radiography plain film cxr kub".split()),
    "ct": frozenset("ct cat computed tomography".split()),
    "mri": frozenset("mri magnetic resonance mr flair t1 t2 dwi adc".split()),
    "ultrasound": frozenset("ultrasound us sonogram sonography doppler echo echocardiogram".split()),
    "pathology": frozenset(
        "pathology histology histopathology microscopy slide stain h&e biopsy "
        "cytology specimen microscopic".split()
    ),
    "pet": frozenset("pet fdg nuclear scintigraphy spect".split()),
}

PLANE: frozenset[str] = frozenset(
    "axial coronal sagittal transverse oblique longitudinal ap pa lateral supine prone".split()
)

LATERALITY: frozenset[str] = frozenset(
    "left right bilateral unilateral ipsilateral contralateral both".split()
)

POSITIONAL: frozenset[str] = frozenset(
    """
    upper lower superior inferior anterior posterior medial lateral proximal distal
    central peripheral apex apical base basal top bottom above below front back
    middle mid dorsal ventral cranial caudal
    """.split()
)

ATTRIBUTE: frozenset[str] = frozenset(
    """
    round oval irregular smooth spiculated lobulated well-circumscribed circumscribed
    large small tiny huge enlarged shrunken thick thin dense lucent hyperdense
    hypodense hyperintense hypointense isointense bright dark white black grey gray
    pink purple blue red brown homogeneous heterogeneous solid cystic calcified
    fatty fluid soft hard firm diffuse focal
    """.split()
)

NUMBER_WORDS: dict[str, int] = {
    "zero": 0, "none": 0, "no": 0,
    "one": 1, "single": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "both": 2, "pair": 2, "multiple": -1, "many": -1, "several": -1,
}

NEGATION_CUES: frozenset[str] = frozenset(
    "no not nor never without absent lacking free devoid unremarkable negative none".split()
)

NORMAL_TERMS: frozenset[str] = frozenset(
    """
    normal unremarkable clear healthy intact regular within limits nothing
    negative none unaffected uninvolved patent
    """.split()
)

#: Question stems that demand a specific location or structure back.
LOCATION_STEMS: tuple[str, ...] = ("where", "which side", "what side", "which part", "which lobe", "location")
COUNT_STEMS: tuple[str, ...] = ("how many", "how much", "number of", "count")
DISEASE_STEMS: tuple[str, ...] = (
    "what disease", "what condition", "what abnormality", "what pathology",
    "what is wrong", "what is the diagnosis", "diagnosis", "what abnormalities",
)
ANATOMY_STEMS: tuple[str, ...] = (
    "what organ", "which organ", "what structure", "which structure",
    "what part of the body", "what body part", "what anatomy",
)
MODALITY_STEMS: tuple[str, ...] = (
    "what modality", "which modality", "what imaging", "what kind of image",
    "what type of image", "what type of scan", "what kind of scan", "how was this taken",
)
PLANE_STEMS: tuple[str, ...] = ("what plane", "which plane", "what view", "which view")
ATTRIBUTE_STEMS: tuple[str, ...] = (
    "what color", "what colour", "what shape", "what size", "how big",
    "what does it look like", "describe the", "what is the appearance",
)


def tokens(text: str) -> list[str]:
    return normalize_answer(text).split()


def _has_any(text: str, terms: frozenset[str]) -> bool:
    return bool(set(tokens(text)) & terms)


def is_anatomy(text: str) -> bool:
    return _has_any(text, ANATOMY)


def is_abnormality(text: str) -> bool:
    return _has_any(text, ABNORMALITY)


def is_attribute(text: str) -> bool:
    return _has_any(text, ATTRIBUTE)


def is_tissue(text: str) -> bool:
    return _has_any(text, TISSUE)


def is_medical_entity(text: str) -> bool:
    """True when the text names *a thing depicted in the image*.

    Covers organs, diseases and tissue/cell structures alike. The distinction
    matters for error category 1.1: the source research reports 31.7%
    "Anatomical Misidentification" on PathVQA, a histopathology set with
    virtually no gross anatomy in it, so that category is evidently counting
    misidentification of the depicted entity in general - naming the wrong
    tissue or the wrong lesion - not strictly organ-for-organ confusion.
    """
    return is_anatomy(text) or is_abnormality(text) or is_tissue(text)


def is_normal_claim(text: str) -> bool:
    """True when an answer asserts absence of disease ("no", "normal", "clear")."""
    norm = normalize_answer(text)
    return norm == "no" or _has_any(text, NORMAL_TERMS)


def laterality_of(text: str) -> str | None:
    """Return 'left', 'right', 'bilateral' or None."""
    toks = set(tokens(text))
    if "bilateral" in toks or "both" in toks:
        return "bilateral"
    left, right = "left" in toks, "right" in toks
    if left and right:
        return "bilateral"
    if left:
        return "left"
    if right:
        return "right"
    return None


def count_of(text: str) -> int | None:
    """Extract a count from an answer, as digits or number words."""
    norm = normalize_answer(text)
    digits = re.findall(r"\d+", norm)
    if digits:
        return int(digits[0])
    for tok in norm.split():
        if tok in NUMBER_WORDS:
            val = NUMBER_WORDS[tok]
            return None if val < 0 else val
    return None


def has_negation(text: str) -> bool:
    return bool(set(tokens(text)) & NEGATION_CUES)


def question_starts_with(question: str, stems: tuple[str, ...]) -> bool:
    q = normalize_answer(question)
    return any(stem in q for stem in stems)


def infer_modality(*texts: str) -> str:
    """Best-effort modality tag from question/answer/caption text.

    Returns one of MODALITY_TERMS' keys, or "unknown". Used to tag dataset rows;
    at runtime the image classifier takes precedence over this.
    """
    blob = " ".join(t for t in texts if t)
    toks = set(tokens(blob))
    for modality, terms in MODALITY_TERMS.items():
        if toks & terms:
            return modality
    return "unknown"
