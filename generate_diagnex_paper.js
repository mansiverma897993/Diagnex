// Historical paper draft. Its metrics predate the image-disjoint retraining and
// are superseded by PROJECT_STATUS.md. Do not cite or regenerate as current work.
import { jsPDF } from "jspdf";
import fs from "fs";

const doc = new jsPDF({ unit: "mm", format: "a4" });
const PAGE_W = 210;
const PAGE_H = 297;
const MARGIN = 24;
const CONTENT_W = PAGE_W - MARGIN * 2;
const TOP = 26;
const BOTTOM = 19;
const INDENT = 6;

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

function section(num, text) {
  ensure(lh(12.5) + 5);
  y += 2;
  doc.setFont("times", "bold");
  doc.setFontSize(12.5);
  doc.setTextColor(...NAVY);
  doc.text(`${num}  ${text}`, MARGIN, y);
  y += lh(12.5) + 1.2;
}

function sub(num, text) {
  ensure(lh(10.5) + 3);
  y += 1.2;
  doc.setFont("times", "bold");
  doc.setFontSize(10.5);
  doc.setTextColor(...SLATE);
  doc.text(`${num}  ${text}`, MARGIN, y);
  y += lh(10.5) + 0.7;
}

function para(text, size = 9.4, indent = true) {
  const lines = doc.splitTextToSize(text, CONTENT_W);
  ensure(lines.length * lh(size) + 2.5);
  doc.setFont("times", "normal");
  doc.setFontSize(size);
  doc.setTextColor(...SLATE);
  let ty = y;
  lines.forEach((line, i) => {
    const x = i === 0 && indent ? MARGIN + INDENT : MARGIN;
    doc.text(line, x, ty, { align: "justify", maxWidth: CONTENT_W - (i === 0 && indent ? INDENT : 0) });
    ty += lh(size);
  });
  y = ty + 1.4;
}

function item(num, text, size = 9.4) {
  const label = `${num}  `;
  const bodyLines = doc.splitTextToSize(text, CONTENT_W - 8);
  ensure(bodyLines.length * lh(size) + 2);
  doc.setFont("times", "normal");
  doc.setFontSize(size);
  doc.setTextColor(...SLATE);
  let ty = y;
  bodyLines.forEach((line, i) => {
    const x = i === 0 ? MARGIN + 8 : MARGIN + 11;
    doc.text(line, x, ty, { align: "justify", maxWidth: CONTENT_W - (i === 0 ? 8 : 11) });
    ty += lh(size);
  });
  doc.setFont("times", "bold");
  doc.text(label, MARGIN, y);
  y = ty + 1.1;
}

function table(headers, rows, widths, aligns = []) {
  const rowPad = 1.0;
  const cellPadX = 1.4;

  function cellTexts(r, c) {
    return doc.splitTextToSize(String(r[c]), widths[c] - cellPadX * 2);
  }

  const all = [headers, ...rows];
  const cellWraps = all.map((r) => r.map((_, c) => cellTexts(r, c)));

  function rowHeight(wraps) {
    const h = Math.max(...wraps.map((w) => w.length * lh(8.6)));
    return h + rowPad * 2 + 1;
  }

  for (let i = 0; i < all.length; i++) {
    const h = rowHeight(cellWraps[i]);
    ensure(h);
    if (i > 0 && y === TOP) {
      doc.setFont("times", "bold");
      doc.setFontSize(8.6);
      doc.setTextColor(...MUTED);
      doc.text(headers.join("     "), MARGIN, y);
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
      doc.setFont("times", i === 0 ? "bold" : "normal");
      doc.setFontSize(8.6);
      doc.setTextColor(...(i === 0 ? [255, 255, 255] : SLATE));
      doc.text(wrap, x, y + rowPad + lh(8.6));
      cx += widths[c];
    });
    y += h;
    if (i === 0 || i < all.length - 1) {
      doc.setDrawColor(...BORDER);
      doc.setLineWidth(0.2);
      doc.line(MARGIN, y, MARGIN + CONTENT_W, y);
    }
  }
  y += 2;
}

function ref(text, size = 8.5) {
  const lines = doc.splitTextToSize(text, CONTENT_W - 6);
  ensure(lines.length * lh(size) + 1.2);
  doc.setFont("times", "normal");
  doc.setFontSize(size);
  doc.setTextColor(...SLATE);
  let ty = y;
  lines.forEach((line, i) => {
    const x = i === 0 ? MARGIN : MARGIN + 6;
    doc.text(line, x, ty, { align: "justify", maxWidth: CONTENT_W - (i === 0 ? 0 : 6) });
    ty += lh(size);
  });
  y = ty + 0.9;
}

// ============================= TITLE BLOCK =============================
doc.setFillColor(...NAVY);
doc.rect(0, 0, PAGE_W, 6, "F");
doc.setTextColor(...NAVY);
doc.setFont("times", "bold");
doc.setFontSize(20);
doc.text("DIAGNEX: A Safety-Gated Medical Visual Question Answering", PAGE_W / 2, 24, { align: "center" });
doc.text("System for Clinical Imaging", PAGE_W / 2, 31, { align: "center" });
doc.setFont("times", "italic");
doc.setFontSize(12);
doc.setTextColor(...SLATE);
doc.text("Mansi Verma", PAGE_W / 2, 39, { align: "center" });
doc.setFont("times", "normal");
doc.setFontSize(10);
doc.setTextColor(...MUTED);
doc.text("Department of Computer Science and Engineering, KIET Group of Institutions, India", PAGE_W / 2, 44, { align: "center" });
doc.text("Mentor: Dr. Gaurav Dubey  |  Project name history: MedSafe to Diagnex  |  August 2026", PAGE_W / 2, 48.5, { align: "center" });
doc.setDrawColor(...BORDER);
doc.setLineWidth(0.6);
doc.line(MARGIN, 53, PAGE_W - MARGIN, 53);
y = 58;

// ============================= ABSTRACT =============================
section("Abstract", "");
para("Medical Visual Question Answering (VQA) models are increasingly capable but dangerously overconfident when they are incorrect. Source research for this project reports that 26.8% of model errors fall into a clinical danger zone, in which the model is simultaneously wrong and highly confident. Such errors can lead to incorrect treatment decisions and make unguarded artificial intelligence unsafe for clinical use. This paper presents DIAGNEX, a full-stack, CPU-viable medical imaging portal that answers natural-language questions about X-ray, CT, MRI, ultrasound and histopathology images, and that refuses to answer when it cannot defend its answer. The system combines a frozen BiomedCLIP vision-language encoder with a compact trainable fusion head of approximately 6.6 million parameters, and guards every answer with an Honest Uncertainty Safety Gate. The gate fuses two complementary signals: temperature-calibrated confidence, which achieves an expected calibration error of 0.083, and a predicted twelve-way clinical error type that feeds an expected Clinical Impact Score. These signals are collapsed into a three-level traffic-light policy that withholds answers rather than bluffing. Evaluated on 8,231 held-out question-answer pairs drawn from the VQA-RAD, SLAKE and PathVQA datasets, the system achieves 62.8% overall accuracy and 85.5% accuracy on closed yes/no questions. With an abstention threshold of 0.60, the system answers only 69.6% of the questions it receives but is correct 81.9% of the time when it does answer, a 19-point improvement over answering everything. DIAGNEX is not presented as a diagnostic tool; it is a screening and educational aid engineered to know when it might be wrong, and to say so.", 9.4);

doc.setFont("times", "bold");
doc.setFontSize(9.4);
doc.setTextColor(...SLATE);
ensure(6);
doc.text("Keywords:  ", MARGIN, y);
doc.setFont("times", "normal");
const kw = "Medical Visual Question Answering; uncertainty quantification; abstention; selective prediction; biomedical vision-language models; deep learning safety; clinical decision support; calibration; error taxonomy.";
const kwLines = doc.splitTextToSize(kw, CONTENT_W - 18);
doc.text(kwLines, MARGIN + 18, y);
y += kwLines.length * lh(9.4) + 2;

// ============================= 1. INTRODUCTION =============================
section("1", "Introduction");
para("The interpretation of medical scans is one of the most consequential tasks in clinical practice. X-rays, computed tomography (CT), magnetic resonance imaging (MRI), ultrasound and histopathology slides must be read by certified specialists, and a well-documented global shortage of clinical radiologists has lengthened waiting times for critical diagnostics and increased the workload on the practitioners who remain. Machine learning offers a pathway to automated assistance in this bottleneck, and medical visual question answering, the task of answering a natural-language question about a medical image, has emerged as a natural interface for such systems: a clinician or patient can ask what the image shows, whether a finding is present, or how many lesions are visible, and receive an answer in plain language.");
para("The risk profile of such systems, however, is unforgiving. Neural networks are systematically miscalibrated; their confidence scores do not reflect the probability that the answer is correct. In the medical setting this is compounded by a second phenomenon documented in the source research that motivates this project: medical VQA models place roughly one error in four, 26.8%, into a clinical danger zone, meaning the model is wrong and simultaneously confident enough that its answer could influence a clinical decision. A false positive can cause unnecessary anxiety, additional procedures and incorrect treatment; a false negative can cause a finding to be missed entirely. An unguarded model is therefore unsafe in front of a patient, regardless of how impressive its aggregate accuracy appears.");
para("The premise of DIAGNEX is a deliberate inversion of the usual objective. Rather than aiming to be right every time, a goal no published medical VQA model currently achieves, the system is designed to be honest about its own uncertainty: to answer when it can defend the answer, and to refuse, with an explanation and a route to a qualified professional, when it cannot. This paper documents the design, implementation, evaluation and honest limitations of that system, developed as a B.Tech final-year project at the Department of Computer Science and Engineering, KIET Group of Institutions, under the working name MedSafe and later renamed DIAGNEX. The safety methodology, comprising the error taxonomy, the 0.60 abstention threshold and the Clinical Impact Score, follows the published research of the project mentor, Dr. Gaurav Dubey.");

sub("1.1", "Problem Statement");
para("The specific problems addressed by this work are threefold. First, existing medical VQA models are overconfident when wrong, and no practical mechanism existed to detect and suppress the confidently incorrect answers that fall into the clinical danger zone. Second, uncertainty estimates in deep medical models are rarely calibrated, so thresholds applied to raw confidence scores do not mean what the research literature says they mean. Third, when a model does refuse to answer, existing systems offer the user no constructive path forward; a safe system must route the uncertain case to a human expert. DIAGNEX addresses all three problems with a single integrated design.");

sub("1.2", "Contributions");
item("(i)", "A safety-gated medical VQA pipeline that combines a frozen biomedical foundation encoder with a compact fusion head, trainable and serviceable entirely on CPU.");
item("(ii)", "A two-signal Honest Uncertainty Safety Gate that fuses calibrated confidence with a predicted clinical failure mode, producing a three-level traffic-light policy with hard abstention.");
item("(iii)", "A twelve-category error taxonomy, a deterministic rule-based error labeller, and a failure-mode predictor that estimates how an answer is most likely to fail.");
item("(iv)", "A full-stack implementation with a React frontend, a FastAPI backend that is authoritative for all safety decisions, and a privacy-preserving intake that strips identifiers at the boundary.");
item("(v)", "A reproducible evaluation on 8,231 held-out question-answer pairs, including a quantitative account of the abstention trade-off and a candid statement of limitations.");

// ============================= 2. RELATED WORK =============================
section("2", "Related Work");

sub("2.1", "Medical Visual Question Answering");
para("Medical VQA research is built on three widely used public benchmarks. VQA-RAD, introduced by Lau et al., contains clinically generated radiology questions and answers over head, chest and abdominal images, with a mix of closed yes/no and open-ended questions [1]. SLAKE, proposed by Liu et al., is a semantically labelled and knowledge-enhanced radiology VQA dataset in which every question is also annotated with a content type by its authors, a property this project exploits as an independent check on error labelling [2]. PathVQA, introduced by He et al., provides more than 30,000 questions on histopathology images and exercises long descriptive open-ended answers [3]. Together these three datasets span radiology and histopathology, and they form the training and evaluation substrate for this work. Architecturally, medical VQA systems commonly pair a vision encoder with a language model or a learned answer head; this project adopts the answer-generation paradigm in which a head scores every token of a fixed medical vocabulary, which keeps output constrained to clinically meaningful surface forms.");

sub("2.2", "Uncertainty Estimation in Medical AI");
para("Uncertainty in deep models is commonly decomposed into aleatoric uncertainty, which arises from irreducible noise in the data, and epistemic uncertainty, which arises from limited knowledge in the model. Bayesian approaches estimate epistemic uncertainty by sampling over the posterior; Monte Carlo dropout, introduced by Gal and Ghahramani, approximates this by keeping dropout active at inference time and measuring variance across forward passes [7]. Entropy-based measures over the predicted distribution, such as Shannon entropy, capture the spread of the probability mass and rise when the model is torn between competing answers. Conformal prediction provides distribution-free coverage guarantees by constructing prediction sets at a pre-specified confidence level, and out-of-distribution (OOD) detection, often built on reconstruction-based variational auto-encoders, flags inputs that lie far from the training distribution, such as scans corrupted by high noise or containing foreign objects.");
para("The project synopsis originally framed the safety methodology in terms of these four techniques. The deployed implementation retains the spirit of that framing while adopting a more tractable, production-grade formulation: post-hoc temperature scaling, a calibration method introduced by Guo et al., converts raw logits into trustworthy probabilities [6], and a learned failure-mode predictor replaces exhaustive sampling with a single forward pass. This design decision is discussed further in Section 6.");

sub("2.3", "Selective Prediction and Abstention");
para("Selective prediction, also called classification with abstention, studies classifiers that are permitted to decline to predict on selected inputs. The central quantity in this literature is the coverage-accuracy trade-off: by answering only a fraction of inputs, a selective system can raise its accuracy on the inputs it chooses to answer. This is precisely the mechanism that makes a modest medical VQA model defensible. Whereas most selective classifiers abstain on the basis of confidence alone, this work abstains on the basis of confidence combined with a clinically weighted prediction of the failure mode, which is unusual and is the key safety contribution.");

// ============================= 3. PROPOSED SYSTEM =============================
section("3", "Proposed System: DIAGNEX");

sub("3.1", "System Overview");
para("DIAGNEX is organized as a decoupled three-part stack, as shown conceptually in Figure 1. The React frontend presents the clinical dashboard, the scan visualiser, the traffic-light results and the follow-up chat interface. The FastAPI backend is authoritative for every safety decision: it computes calibrated confidence, predicts the failure mode, applies the traffic-light policy and only then composes the patient-facing report. The machine-learning pipeline builds the datasets, caches frozen embeddings, trains the fusion head and mines the error corpus. A resilient local fallback engine on the client keeps the application functional if the API server is offline, protecting critical access.");

sub("3.2", "Data Acquisition and Preprocessing");
para("The three public datasets are downloaded and unified into a single manifest of approximately 41,900 question-answer pairs over approximately 5,244 images. Every image is decoded to bare RGB pixels before any downstream processing. De-identification happens at the intake boundary: DICOM metadata tags and EXIF headers are stripped before pixels reach any other module, so no module downstream of intake can persist an identifier. The data is split with an image-grouped held-out strategy so that no image and its associated questions appear in both training and test splits, yielding a test split of 8,231 question-answer pairs.");

sub("3.3", "Model Architecture");
para("The vision encoder is a frozen BiomedCLIP ViT-B/16 model [4], which maps an image to a 1,536-dimensional embedding. The question is embedded in two complementary ways. The BiomedCLIP text tower produces a 512-dimensional contextual embedding, and a TF-IDF bag-of-ngrams vector provides a sparse lexical representation. The TF-IDF channel is retained deliberately: contrastive text encoders represent negation poorly, since the phrases \"is there a mass\" and \"is there no mass\" sit close together in CLIP space, and negation failure is itself one of the twelve error categories (category 4.1). A lexical representation separates the two reliably.");
para("The fusion head is the only trainable component of the network. It consumes the concatenation of the image and text embeddings together with their element-wise product, written as [i ; t ; i x t], and scores every token of a fixed medical answer vocabulary of 3,698 words. The multiplicative term is important. Answer priors in medical VQA are strong enough that a head trained only on concatenated features can reach respectable accuracy while barely consulting the image; the element-wise product forces the image and the question to agree before an answer token can be supported. The head contains approximately 6.6 million parameters, which is what makes laptop-scale training and serving feasible.");

sub("3.4", "Calibration and Confidence");
para("A raw softmax is systematically overconfident, so a confidence cut applied to uncalibrated scores would not have the meaning the research literature assigns to it. A temperature parameter T is fitted on the validation split and applied to the logits before the softmax, following the temperature-scaling method of Guo et al. [6]. The fitted temperature of approximately 1.085 brings the expected calibration error (ECE) of the final model down to 0.083. All downstream thresholds in the safety gate operate on this calibrated quantity.");

sub("3.5", "Error Taxonomy and Failure-Mode Prediction");
para("The safety gate requires a second signal in addition to confidence: an estimate of how an answer would fail if it were wrong. The system defines twelve error categories organised into four groups, each mapped to a clinical risk tier. Table 1 lists the categories together with the published prevalence figures taken from the source research. Eight categories and their rates are transcribed from the research; the research states that the taxonomy has twelve categories but enumerates only eight, so the remaining four are reconstructed from the numbering gaps and are marked provisional everywhere they appear. They are never presented as published findings.");
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
  [18, 76, 30, 38],
  ["center", "left", "left", "left"]
);
para("Because the mentor's annotated error dataset of 1,975 errors was unavailable, the error corpus is generated instead. The trained model is run over held-out data and every wrong prediction is classified by deterministic, inspectable rules implemented in the error-labelling module. This yields approximately 5,885 labelled errors, split into about 2,768 for training and 3,117 for testing. A twelve-way failure-mode predictor is then trained on the labelled corpus; at inference time it estimates, for a candidate answer, the most likely category of failure, which is mapped through the taxonomy to an expected Clinical Impact Score. The predictor reaches about 62.9% accuracy over twelve classes against a chance baseline of about 8.3%.");

sub("3.6", "The Honest Uncertainty Safety Gate");
para("Every candidate answer is evaluated on two signals: the calibrated confidence and the predicted error type with its Clinical Impact Score. The policy is a three-level traffic light, summarised in Table 2. A GREEN answer is shown in full. A YELLOW answer is shown but carries prominent warning flags and disclaimers urging verification with a doctor. A RED answer is withheld entirely, the self-diagnosis screen is locked, and a specialist locator is triggered to route the patient to a nearby radiologist.");
table(
  ["Band", "Condition", "Behaviour"],
  [
    ["GREEN", "Confidence at least 85% and no high-risk failure mode", "Answer shown in full"],
    ["YELLOW", "Confidence 60% to 84%, or GREEN downgraded by a high-risk failure mode", "Answer shown; verify with a doctor"],
    ["RED", "Confidence below 60%, or a likely CRITICAL failure mode", "Answer withheld; specialist finder shown"],
  ],
  [24, 92, 60],
  ["center", "left", "left"]
);
para("Two properties of the gate deserve emphasis. First, a confident answer can still be suppressed: an answer at 92% confidence whose predicted failure mode is an abnormality detection failure, the category in which the model says normal while a finding is present, is forced to RED because the way it would fail is a missed tumour. Second, a withheld answer is removed from the API response body rather than merely flagged, so the client cannot render what it was never sent. The gate runs entirely in the backend, which is authoritative; the frontend never sees a refused answer. The API likewise refuses to serve simulated results: until the model is trained, every analysis endpoint returns HTTP 503 with instructions.");

// ============================= 4. IMPLEMENTATION =============================
section("4", "Implementation");

sub("4.1", "Frontend");
para("The user interface is built with React 19 and bundled with Vite. GSAP provides the scan-animation effects, including the sweeping scan line rendered over the uploaded image, glowing safety indicators and interactive transitions. The interface presents the analysis results with the traffic-light indicator, the confidence score, the report text, suggested follow-up questions, and the clinical chat panel. Reports can be exported to PDF using jsPDF. A resilient local fallback engine runs client-side when the API server is offline, so the application never crashes and never presents fabricated results: in fallback mode it clearly marks outputs as simulated rather than pretending they came from the model.");

sub("4.2", "Backend and API");
para("The backend is implemented in Python with FastAPI and exposes six endpoints: a service-info root, /api/health for readiness, /api/taxonomy for the twelve error categories, /api/stats for aggregate safety statistics, /api/upload for scan analysis, and /api/chat for follow-up questions. The upload endpoint accepts PNG, JPEG, TIFF and native DICOM files up to 40 MB, returns 400 on unreadable images, 413 above the size limit, 503 when the model is untrained, and 404 for expired chat sessions. Suggested follow-up questions are themselves real model predictions, each independently passed through the gate, so a suggestion can itself come back withheld.");

sub("4.3", "Training Pipeline");
para("The training pipeline is designed to be resumable and CPU-friendly. The dataset builder downloads and unifies the three public datasets. The feature extractor runs the frozen BiomedCLIP towers once and caches the resulting embeddings to disk, which is the only expensive step; training the fusion head then takes minutes on CPU. The training script fits the temperature for calibration. The error-mining step generates the error corpus and trains the failure-mode predictor. On completion, the server loads the trained artefacts, the answer vocabulary, the TF-IDF vectoriser, the fusion head and the error predictor, from the artifacts directory.");

sub("4.4", "Privacy and Data Handling");
para("De-identified pixels live in a TTL-bounded in-memory session cache of thirty minutes with a cap of two hundred sessions, which is enough to support follow-up chat while deliberately creating no retention obligation. Nothing is written to disk. The system is designed on a principle of no fabrication, no patient data at rest, and no silent degradation; the endpoint error semantics above are part of that design.");

// ============================= 5. EXPERIMENTS =============================
section("5", "Experiments and Results");

sub("5.1", "Experimental Setup");
para("The model is evaluated on the held-out test split of 8,231 question-answer pairs described in Section 3.2. All reported figures are real numbers reproduced from the evaluation metrics file produced by the pipeline; no figure in this paper is simulated. Overall accuracy is reported alongside closed-question accuracy, for yes/no questions, and open-ended accuracy, for free-form answers. Calibration is reported as expected calibration error after temperature scaling.");

sub("5.2", "Overall Performance");
para("Table 3 reports the headline results. The model is substantially stronger on closed questions, at 85.5%, than on open-ended questions, at 41.5%, which is consistent with the difficulty of generating long descriptive answers over a fixed vocabulary and is discussed in Section 6. The overall accuracy of 62.8% is honest and modest, and the paper does not claim otherwise.");
table(
  ["Metric", "Result"],
  [
    ["Closed questions (yes/no)", "85.5%"],
    ["Open-ended questions", "41.5%"],
    ["Overall accuracy", "62.8%"],
    ["Calibration error (ECE) after temperature scaling", "0.083"],
    ["Answer vocabulary size", "3,698 words"],
    ["Temperature (fitted)", "1.085"],
  ],
  [124, 48],
  ["left", "center"]
);

sub("5.3", "Per-Dataset Performance");
para("Table 4 breaks down performance by dataset. SLAKE, with 1,061 test pairs, is the strongest split at 83.5% overall and a balanced 88.5% closed and 80.9% open. PathVQA, with 6,719 test pairs and long descriptive answers, reaches 60.9% overall and only 34.9% on open questions. VQA-RAD is the weakest split at 41.9% overall, a consequence of the very small amount of training data that survives the image-grouped split, roughly 1,620 rows, from which a strong answer head is difficult to learn.");
table(
  ["Dataset", "Test pairs", "Overall", "Closed", "Open"],
  [
    ["SLAKE", "1,061", "83.5%", "88.5%", "80.9%"],
    ["PathVQA", "6,719", "60.9%", "86.8%", "34.9%"],
    ["VQA-RAD", "451", "41.9%", "63.3%", "15.0%"],
  ],
  [42, 26, 36, 34, 34],
  ["left", "center", "center", "center", "center"]
);

sub("5.4", "The Abstention Trade-Off");
para("The central empirical claim of this paper is that abstention, not accuracy, is the safety mechanism. Table 5 shows the coverage-accuracy trade-off across candidate thresholds. Without a gate, the system answers everything and is correct 62.8% of the time. As the threshold rises, fewer questions are answered but the accuracy on the answered set rises monotonically, and the fraction of errors removed from the patient-facing output rises with it.");
table(
  ["Abstain threshold", "Answers given", "Accuracy when it answers", "Errors removed"],
  [
    ["No gate", "100%", "62.8%", "n/a"],
    ["0.50", "75.0%", "78.6%", "57.0%"],
    ["0.60 (published)", "69.6%", "81.9%", "66.1%"],
    ["0.70", "65.1%", "84.5%", "72.9%"],
    ["0.85", "56.7%", "89.0%", "83.2%"],
  ],
  [44, 42, 44, 42],
  ["left", "center", "center", "center"]
);
para("At the published threshold of 0.60 the system declines roughly three questions in ten and is right 81.9% of the time on the questions it chooses to answer. More than two-thirds of all model errors are removed from patient-facing output before they reach the user. This is the quantitative justification for exposing the system to patients at all.");

sub("5.5", "Failure-Mode Predictor");
para("The twelve-way failure-mode predictor scores about 62.9% accuracy over twelve classes against a chance baseline of about 8.3%. This is useful as a signal but not authoritative in isolation; the safety gate therefore treats it as a secondary channel that can downgrade a confident answer, never as the sole arbiter of correctness.");

sub("5.6", "Validation of the Error Labeller");
para("Because the error corpus is generated by rules rather than annotated by clinicians, its quality is measured rather than assumed. SLAKE annotates every question with a content type assigned by its authors independently of this project, which provides a ground-truth check on the rule-based labeller. On SLAKE, rule coverage is 88% with 63% independent agreement. The labeller is reliable on structured radiology questions and weak on long histopathology free-text, where PathVQA coverage falls to about 42% and drags the aggregate coverage down to about 47%. The uncovered errors receive a fallback label routed by question form, are marked as not rule-confident, and are reported separately rather than hidden.");

// ============================= 6. DISCUSSION =============================
section("6", "Discussion");

sub("6.1", "What Makes the System Safe");
para("The results show that a modest medical VQA model can be made safe to expose to patients by placing uncertainty, rather than accuracy, at the centre of the design. Two design choices carry this behaviour. Calibrated confidence ensures that the abstention threshold means what the literature says it means; without temperature scaling, a 0.60 cut on raw scores would admit a different and larger set of errors than the research anticipates. Failure-mode prediction ensures that a high-confidence answer with a dangerous likely failure mode is suppressed even when its score would pass a naive threshold. The 92%-confident abnormality-detection-failure example in Section 3.6 is the canonical instance: a naive gate would display it, and the safety gate correctly withholds it.");
para("The system also respects the human in the loop. YELLOW answers are shown but explicitly routed for verification. RED answers are withheld but the user is not abandoned; the specialist locator converts a refusal into a constructive clinical action. Refusals are explained in plain language, and every screen and report carries the medical disclaimer.");

sub("6.2", "Limitations");
para("Several limitations are acknowledged candidly. First, the model is not a diagnostic tool at current accuracy; at 62.8% overall and 41.9% on VQA-RAD, the safety gate is what makes it defensible, not the raw accuracy. Second, open-ended accuracy is weak, at 41.5%, in part because the answer vocabulary covers only about 83% of test answers and the remaining 17% are unreachable by construction. Third, the training mix is 78% PathVQA, so the observed error distribution differs from the published aggregate, which is not so dominated by histopathology; like-for-like comparison is reported per dataset. Fourth, the error labeller covers only about 47% of errors, and the remaining errors carry a fallback label that is reported separately. Fifth, four of the twelve taxonomy categories are provisional, reconstructed from numbering gaps and never presented as published findings. Finally, the failure-mode predictor, at 62.9%, is a useful signal but not an authority.");

// ============================= 7. CONCLUSION =============================
section("7", "Conclusion and Future Work");
para("DIAGNEX demonstrates that a modest, CPU-viable medical VQA system can be made safe to expose to patients by engineering honesty into every layer: calibrated confidence, predicted failure modes, a hard abstention policy that refuses to bluff, and a constructive escalation path when the system cannot answer. Its contributions are a working blueprint that combines frozen biomedical foundation encoders with a compact fusion head, a two-signal safety gate, a reproducible error taxonomy and labelling methodology, and a full-stack implementation with privacy at the boundary.");
para("Future work proceeds along five directions: recovering open-ended accuracy by expanding the answer vocabulary; confirming the provisional taxonomy categories through clinical annotation; evaluating on prospective clinical data under clinician review; tightening conformal guarantees around the traffic-light bands; and studying the interaction between the failure-mode predictor and the calibration channel under distribution shift. The system's central claim is not that it is always right, but that it knows when it might be wrong, and says so.");

// ============================= ACKNOWLEDGMENT =============================
section("Acknowledgment", "");
para("The author thanks Dr. Gaurav Dubey, Department of Computer Science and Engineering, KIET Group of Institutions, for mentoring this project and for making available the research on medical VQA error taxonomy, the 0.60 abstention threshold and the Clinical Impact Score that underpin the safety methodology.");

// ============================= REFERENCES =============================
doc.addPage();
y = TOP;
section("References", "");
ref("[1]  J. J. Lau, S. Gayen, A. Ben Abacha, and D. Demner-Fushman, \"A dataset of clinically generated visual questions and answers about radiology images,\" Scientific Data, vol. 5, 2018. (VQA-RAD)");
ref("[2]  B. Liu, L.-M. Zhan, and X.-M. Wu, \"SLAKE: A semantically-labeled knowledge-enhanced dataset for medical visual question answering,\" in IEEE International Symposium on Biomedical Imaging (ISBI), 2021.");
ref("[3]  X. He, Y. Zhang, L. Mou, E. Xing, and P. Xie, \"PathVQA: 30,000+ questions for medical visual question answering,\" arXiv:2003.10286, 2020.");
ref("[4]  S. Zhang et al., \"BiomedCLIP: A multimodal biomedical foundation model pretrained from fifteen million scientific image-text pairs,\" 2023.");
ref("[5]  G. Dubey, \"Safety gating for medical visual question answering: error taxonomy, abstention threshold and Clinical Impact Score,\" project source research, unpublished.");
ref("[6]  C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, \"On calibration of modern neural networks,\" in Proceedings of the 34th International Conference on Machine Learning (ICML), 2017.");
ref("[7]  Y. Gal and Z. Ghahramani, \"Dropout as a Bayesian approximation: Representing model uncertainty in deep learning,\" in Proceedings of the 33rd International Conference on Machine Learning (ICML), 2016.");

doc.setProperties({
  title: "DIAGNEX: A Safety-Gated Medical Visual Question Answering System for Clinical Imaging",
  subject: "Updated research paper for the Diagnex project",
  author: "Mansi Verma",
  creator: "DIAGNEX",
});

const total = doc.getNumberOfPages();
for (let p = 1; p <= total; p++) {
  doc.setPage(p);
  doc.setFont("times", "normal");
  doc.setFontSize(8.5);
  doc.setTextColor(...MUTED);
  doc.text("DIAGNEX Research Paper", MARGIN, PAGE_H - 12);
  doc.text(`Page ${p} of ${total}`, PAGE_W - MARGIN, PAGE_H - 12, { align: "right" });
}

const outPath = "D:\\docx\\Diagnex_Research_Paper.pdf";
fs.writeFileSync(outPath, doc.output(), "binary");
console.log("PDF written to " + outPath);
console.log("Page count: " + total);
