import { jsPDF } from "jspdf";
import fs from "fs";

const doc = new jsPDF({ unit: "mm", format: "a4" });
const PAGE_W = 210;
const PAGE_H = 297;
const MARGIN = 15;
const CONTENT_W = PAGE_W - MARGIN * 2;
const TOP = 18;
const BOTTOM = 14;

const NAVY = [30, 58, 138];
const SLATE = [30, 41, 59];
const MUTED = [100, 116, 139];
const FILL = [241, 245, 249];
const BORDER = [203, 213, 225];

let y = 0;

function ensure(h) {
  if (y + h > PAGE_H - BOTTOM) {
    doc.addPage();
    y = TOP;
    return true;
  }
  return false;
}

function lh(size) {
  return size * 0.44;
}

function header(text) {
  ensure(lh(12) + 4);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(...NAVY);
  doc.text(text, MARGIN, y);
  y += 1.6;
  doc.setDrawColor(...BORDER);
  doc.setLineWidth(0.4);
  doc.line(MARGIN, y, PAGE_W - MARGIN, y);
  y += lh(12) - 1.8;
}

function sub(text) {
  ensure(lh(10) + 2);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...NAVY);
  doc.text(text, MARGIN, y);
  y += lh(10) + 0.6;
}

function para(text, size = 8.7) {
  const lines = doc.splitTextToSize(text, CONTENT_W);
  ensure(lines.length * lh(size) + 2);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(size);
  doc.setTextColor(...SLATE);
  doc.text(lines, MARGIN, y);
  y += lines.length * lh(size) + 1.4;
}

function bullet(text, size = 8.7) {
  const lines = doc.splitTextToSize(text, CONTENT_W - 4);
  ensure(lines.length * lh(size) + 1.6);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(size);
  doc.setTextColor(...SLATE);
  doc.text(lines, MARGIN + 3.2, y);
  doc.setFont("helvetica", "bold");
  doc.text("\u2022", MARGIN, y);
  y += lines.length * lh(size) + 1.2;
}

function table(headers, rows, widths, aligns = []) {
  const rowPad = 1.1;
  const cellPadX = 1.5;

  function cellTexts(r, c) {
    return doc.splitTextToSize(String(r[c]), widths[c] - cellPadX * 2);
  }

  const all = [headers, ...rows];
  const cellWraps = all.map((r) => r.map((_, c) => cellTexts(r, c)));

  function rowHeight(wraps) {
    const h = Math.max(...wraps.map((w) => w.length * lh(8)));
    return h + rowPad * 2 + 1.2;
  }

  for (let i = 0; i < all.length; i++) {
    const h = rowHeight(cellWraps[i]);
    ensure(h);
    if (i > 0 && y === TOP) {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(8);
      doc.setTextColor(...MUTED);
      doc.text(headers.join("   |   "), MARGIN, y);
      y += 4;
    }

    if (i === 0) {
      doc.setFillColor(...NAVY);
      doc.rect(MARGIN, y, CONTENT_W, h, "F");
    } else if (i % 2 === 0) {
      doc.setFillColor(...FILL);
      doc.rect(MARGIN, y, CONTENT_W, h, "F");
    }

    let cx = MARGIN;
    cellWraps[i].forEach((wrap, c) => {
      let x = cx + cellPadX;
      if (aligns[c] === "center") {
        const w = Math.max(...wrap.map((l) => doc.getStringUnitWidth(l) * doc.internal.getFontSize() / 2.835));
        x = cx + (widths[c] - w) / 2;
      }
      doc.setFont("helvetica", i === 0 ? "bold" : "normal");
      doc.setFontSize(8);
      doc.setTextColor(...(i === 0 ? [255, 255, 255] : SLATE));
      doc.text(wrap, x, y + rowPad + lh(8));
      cx += widths[c];
    });

    y += h;
    if (i === 0 || i < all.length - 1) {
      doc.setDrawColor(...BORDER);
      doc.setLineWidth(0.2);
      doc.line(MARGIN, y, MARGIN + CONTENT_W, y);
    }
  }
  y += 1.2;
}

// ============================= COVER HEADER =============================
doc.setFillColor(...NAVY);
doc.rect(0, 0, PAGE_W, 7, "F");
doc.setTextColor(...NAVY);
doc.setFont("helvetica", "bold");
doc.setFontSize(24);
doc.text("DIAGNEX", PAGE_W / 2, 28, { align: "center" });
doc.setFont("helvetica", "bold");
doc.setFontSize(12);
doc.setTextColor(...MUTED);
doc.text("Full-Stack AI-Assisted Medical Imaging & Clinical VQA Platform", PAGE_W / 2, 34.5, { align: "center" });
doc.setFont("helvetica", "normal");
doc.setFontSize(9);
doc.text("(formerly MedSafe)  \u2022  Project Report  \u2022  August 2026", PAGE_W / 2, 39.5, { align: "center" });
doc.setDrawColor(...BORDER);
doc.setLineWidth(0.6);
doc.line(MARGIN, 44, PAGE_W - MARGIN, 44);
y = 49;

para("Diagnex is a safety-gated medical Visual Question Answering (VQA) system: a full-stack application in which a user uploads an X-ray, CT, MRI, ultrasound or pathology slide, asks a natural-language question, and receives an answer together with an honest account of how much to trust it — or an explicit refusal, when the model should not be trusted. It is a B.Tech final-year work (Dept. of CSE, KIET Group of Institutions) mentored by Dr. Gaurav Dubey, originally developed under the name MedSafe and renamed Diagnex. It is intended as a screening and educational aid, not a medical diagnosis and not a substitute for examination by a qualified doctor.");

// ============================= 1. PROBLEM =============================
header("1. Problem Statement");
para("Medical scan interpretation requires certified radiologists, and a global shortage pushes wait times for critical diagnostics upward. Deep-learning models offer automation, but published medical VQA models are dangerously overconfident when wrong: the research underlying this project reports that 26.8% of errors land in a \u201cclinical danger zone\u201d where the model is simultaneously incorrect and highly confident. False positives and negatives can cause incorrect treatment, so unguarded AI is unsafe for clinical use. Diagnex\u2019s goal is therefore not to be right every time — no published medical VQA model is — but to know when it might be wrong, and say so.");

// ============================= 2. OBJECTIVES & SOLUTION =============================
header("2. Objectives & Solution");
para("Diagnex combines a full-stack clinical portal, an ML inference engine and a hard safety gate. Key objectives:");
bullet("Multi-modal intake — X-ray, CT, MRI, ultrasound and histopathology images as PNG/JPEG/TIFF or native DICOM, with identifiers stripped at the boundary.");
bullet("Natural-language VQA — closed (yes/no) and open-ended clinical questions answered over a standardised 3,698-word medical answer vocabulary.");
bullet("Honest Uncertainty Safety Gate — a GREEN / YELLOW / RED traffic light that withholds answers rather than bluffing, driven by calibrated confidence plus a predicted failure mode.");
bullet("Follow-up chat — a series of questions about one scan via a de-identified, TTL-bounded in-memory session (30 minutes).");
bullet("Zero fabrication by design — every report sentence is derived from model output; withheld answers are removed from the API response body, not merely flagged.");
bullet("CPU-only operation — the vision transformer is frozen and runs once during feature extraction, so the whole system trains and serves on a laptop.");

// ============================= 3. ARCHITECTURE & TECH STACK =============================
header("3. Architecture & Tech Stack");
para("The system is a decoupled three-part stack. The React 19 + Vite frontend (src/) provides the dashboard, scan visualisation, traffic-light results and clinical chat; the FastAPI backend (backend/main.py) is authoritative for all safety decisions; the ML pipeline (ml/) builds datasets, extracts features, trains heads and mines error corpora. A resilient local fallback engine keeps the UI alive if the API is offline.");
bullet("Frontend: React 19, Vite, GSAP animations, jsPDF report export.");
bullet("Backend: Python 3.10+, FastAPI 2.x — /api/upload, /api/chat, /api/health, /api/taxonomy, /api/stats.");
bullet("ML: PyTorch 2.5.1 (CPU); frozen BiomedCLIP ViT-B/16 encoder (1,536-d image embedding); BiomedCLIP text + TF-IDF n-grams; fusion head over [image ; text ; image\u00d7text] (~6.6M trainable parameters).");
bullet("Inference engine: frozen towers + trained heads, temperature-scaled confidence, 12-way error-type predictor, zero-shot modality detection.");
bullet("Data: three public research datasets — VQA-RAD, SLAKE, PathVQA — unified into ~41,900 QA pairs over ~5,244 images.");
para("Two design choices matter: the multiplicative image\u00d7text term forces image and question to agree (answer priors are so strong that concatenation alone barely consults the image); and TF-IDF complements the CLIP text embedding because contrastive text encoders represent negation poorly — relevant since negation failures are themselves an error category.");

// ============================= 4. SAFETY GATE =============================
header("4. The Honest Uncertainty Safety Gate");
para("Confidence alone is insufficient, so two signals drive every decision: (1) calibrated confidence — a temperature fitted on the validation split (T ~ 1.085) brings calibration error (ECE) down to 0.083 — and (2) a 12-way error-type prediction answering \u201cif this answer is wrong, how is it most likely wrong?\u201d, which feeds an expected Clinical Impact Score. A confident answer whose likely failure mode is CRITICAL is forced to RED and withheld: a 92%-confident answer can be suppressed because the way it would fail is a missed tumour. That is the core idea.");
table(
  ["Band", "When", "Behaviour"],
  [
    ["GREEN", ">= 85% and no high-risk failure mode", "Answer shown in full"],
    ["YELLOW", "60\u201385%, or GREEN downgraded by a high-risk failure mode", "Answer shown \u2014 verify with a doctor"],
    ["RED", "< 60%, or a likely CRITICAL failure mode", "Answer withheld; specialist finder shown"],
  ],
  [24, 92, 64],
  ["center", "left", "left"]
);
para("A withheld answer is removed from the API response body rather than merely flagged, so the client cannot render what it was never sent. The gate runs in the backend; the React UI never sees an answer the gate refused, and the API refuses to serve simulated results (503 until the model is trained). The synopsis frames the same objective through complementary methods — Monte Carlo (Bayesian) dropout, Shannon-entropy indexing, conformal prediction and OOD VAE gating — which informed the deployed calibrated-confidence plus failure-mode design.");

// ============================= 5. ERROR TAXONOMY =============================
header("5. The 12-Category Error Taxonomy");
para("The gate is powered by a clinically-weighted taxonomy of how medical VQA systems fail. Eight categories and their published rates come from the source research; four (marked \u201cprovisional\u201d) are reconstructed from numbering gaps and are never presented as published findings.");
table(
  ["Code", "Category", "Risk", "Published rate"],
  [
    ["1.1", "Anatomical Misidentification", "HIGH", "30.1%"],
    ["1.2", "Modality or Plane Confusion", "MEDIUM", "provisional"],
    ["1.3", "Spatial Reasoning Failure", "HIGH", "2.9%"],
    ["2.1", "Granularity Mismatch", "MEDIUM", "12.4%"],
    ["2.2", "Category Domain Confusion", "HIGH", "19.0%"],
    ["2.3", "Attribute Description Error", "MEDIUM", "provisional"],
    ["3.1", "Abnormality Detection Failure", "CRITICAL", "13.2%"],
    ["3.2", "False Positive Hallucination", "HIGH", "14.2%"],
    ["3.3", "Counting Error", "MEDIUM", "10.0%"],
    ["3.4", "Localisation Error", "HIGH", "provisional"],
    ["4.1", "Negation Comprehension Failure", "HIGH", "0.5%"],
    ["4.2", "Question Misinterpretation", "MEDIUM", "provisional"],
  ],
  [16, 82, 30, 52],
  ["center", "left", "left", "left"]
);
para("As the mentor\u2019s 1,975-error annotated dataset was unavailable, the error corpus is generated instead: the trained model runs over held-out data and every wrong prediction is classified by deterministic, inspectable rules (ml/eval/error_rules.py), yielding ~5,885 labelled errors (~2,768 train / ~3,117 test). The labeller is measured, not assumed: SLAKE\u2019s independent content-type annotations show 63% agreement with 88% rule coverage (radiology reliable; long histopathology free-text weak, dragging aggregate coverage to ~47% — a stated limitation).");

// ============================= 6. PERFORMANCE =============================
header("6. Performance & Evaluation");
para("Measured on a held-out test split of 8,231 question\u2013answer pairs (real numbers from ml/artifacts/vqa_metrics.json).");
table(
  ["Metric", "Result"],
  [
    ["Closed questions (yes/no)", "85.5%"],
    ["Open-ended questions", "41.5%"],
    ["Overall accuracy", "62.8%"],
    ["Calibration error (ECE) after temperature scaling", "0.083"],
    ["Answer vocabulary", "3,698 words"],
  ],
  [120, 60],
  ["left", "center"]
);
sub("Per dataset");
table(
  ["Dataset", "n", "Overall", "Closed", "Open"],
  [
    ["SLAKE", "1,061", "83.5%", "88.5%", "80.9%"],
    ["PathVQA", "6,719", "60.9%", "86.8%", "34.9%"],
    ["VQA-RAD", "451", "41.9%", "63.3%", "15.0%"],
  ],
  [40, 20, 40, 40, 40],
  ["left", "center", "center", "center", "center"]
);
para("The abstention trade-off is the reason the project exists: withholding low-confidence answers converts a 62.8%-accurate model into a defensible screening aid.");
table(
  ["Threshold", "Answers given", "Accuracy when it answers", "Errors removed"],
  [
    ["No gate", "100%", "62.8%", "\u2014"],
    ["0.50", "75.0%", "78.6%", "57.0%"],
    ["0.60 (published)", "69.6%", "81.9%", "66.1%"],
    ["0.70", "65.1%", "84.5%", "72.9%"],
    ["0.85", "56.7%", "89.0%", "83.2%"],
  ],
  [46, 44, 46, 44],
  ["left", "center", "center", "center"]
);
para("At the published abstain threshold of 0.60 the system declines roughly three questions in ten and is right 81.9% of the time on the rest — a 19-point improvement over answering everything. The 12-way error-type predictor scores ~62.9% (chance ~ 8.3%): useful, not authoritative.");

// ============================= 7. ETHICS & SAFETY =============================
header("7. Ethics, Privacy & Safety");
bullet("Only public research datasets (VQA-RAD, SLAKE, PathVQA) are used; no patient images.");
bullet("DICOM tags and EXIF identifiers are stripped at the intake boundary before pixels reach any other code; nothing is written to disk.");
bullet("De-identified images live in a TTL-bounded in-memory cache (30 minutes, 200 sessions) for follow-up chat, creating no retention obligation.");
bullet("Every screen and report carries the medical disclaimer; the system refuses to start rather than serve simulated results.");
bullet("Endpoints return 503 when untrained, 400 on unreadable images, 413 above the 40 MB limit, and 404 for expired sessions.");

// ============================= 8. LIMITATIONS =============================
header("8. Honest Limitations");
bullet("Not a diagnostic tool at current accuracy (62.8% overall; 41.9% on VQA-RAD). The safety gate is what makes it defensible, not the raw accuracy.");
bullet("Open-ended accuracy is weak (41.5%); the vocabulary covers only 83% of test answers, the rest being unreachable by construction.");
bullet("VQA-RAD is the weakest split — only ~1,620 training rows survive the image-grouped validation split.");
bullet("Error-corpus labelling covers ~47% of errors; the rest get a fallback label marked rule_confident: false and reported separately.");
bullet("The error distribution differs from the published aggregate because the training mix is 78% PathVQA; like-for-like comparison is done per dataset.");
bullet("Four taxonomy categories remain provisional pending confirmation.");

// ============================= 9. IMPACT & CONCLUSION =============================
header("9. Clinical Impact & Conclusion");
para("Diagnex establishes a safety-first template for deploying deep learning in medical imaging. It safeguards patients by avoiding wrong answers: it accelerates the diagnostic pipeline for high-certainty cases, reduces anxiety with honest plain-language reporting, and safely routes uncertain cases to certified practitioners. The result is an end-to-end, CPU-viable, full-stack system whose central claim is not that it is always right, but that it knows when it might be wrong — and says so.");

header("Credits");
para("B.Tech final-year project, Dept. of CSE, KIET Group of Institutions. Mentor: Dr. Gaurav Dubey. Safety methodology — error taxonomy, 0.60 abstention threshold and Clinical Impact Score — follows his published research. Repository: github.com/mansiverma897993/Diagnex.");

doc.setProperties({
  title: "Diagnex - Project Report",
  subject: "Full-Stack AI-Assisted Medical Imaging & Clinical VQA Platform",
  author: "Diagnex Project Team",
  creator: "Diagnex",
});

const outPath = "D:\\docx\\Diagnex_Project_Report.pdf";
fs.writeFileSync(outPath, doc.output(), "binary");
console.log("PDF written to " + outPath);
console.log("Page count: " + doc.getNumberOfPages());