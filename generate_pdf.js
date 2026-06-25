import { jsPDF } from "jspdf";
import fs from "fs";

const doc = new jsPDF();

// Document Header (Compact but elegant layout)
doc.setFont("helvetica", "bold");
doc.setFontSize(22);
doc.setTextColor(30, 58, 138); // Dark blue primary
doc.text("DIAGNEX - PROJECT SYNOPSIS", 105, 16, { align: "center" });

doc.setFont("helvetica", "bold");
doc.setFontSize(11);
doc.setTextColor(100, 116, 139); // Muted slate secondary
doc.text("AI-Assisted Medical Imaging & Clinical VQA Platform", 105, 21, { align: "center" });

// Line separator
doc.setDrawColor(203, 213, 225);
doc.setLineWidth(0.6);
doc.line(15, 25, 195, 25);

let y = 32;
const margin = 15;
const pageWidth = 180; // 210 - 30 margin

const addSectionHeader = (text) => {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(30, 58, 138);
  doc.text(text, margin, y);
  y += 5.5;
};

const addParagraph = (text) => {
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.2);
  doc.setTextColor(30, 41, 59); // Slate-800
  const lines = doc.splitTextToSize(text, pageWidth);
  const heightNeeded = lines.length * 4.5;
  doc.text(lines, margin, y);
  y += heightNeeded + 3;
};

const addListItem = (title, description) => {
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.2);
  doc.setTextColor(30, 41, 59);
  
  const titleText = "• " + title + ": ";
  const fullText = titleText + description;
  const lines = doc.splitTextToSize(fullText, pageWidth - 4);
  const heightNeeded = lines.length * 4.5;
  
  doc.text(lines, margin + 3, y);
  y += heightNeeded + 2.2;
};

// 1. Project Title
addSectionHeader("1. Project Title & Overview");
addParagraph("DIAGNEX: A Full-Stack AI-Assisted Medical Imaging Portal & Radiologist Visual Question Answering (VQA) Platform. Diagnex operates as an intelligent digital radiologist assistant that analyzes complex medical images and answers diagnostic questions instantly in natural language.");

// 2. Problem Statement
addSectionHeader("2. The Problem: Overburdened Radiologists & Unsafe AI Models");
addParagraph("Interpretation of medical scans (X-Rays, MRIs, CTs, and Ultrasounds) requires certified experts. Due to a global shortage of clinical radiologists, patient wait times for critical diagnostics have increased. While deep learning models offer a potential solution for automation, typical AI models are prone to hallucinating predictions when presented with low-resolution, noisy, or atypical inputs. Generating false positive or false negative results can lead to incorrect treatments, making unguarded AI unsafe for clinical diagnostics.");

// 3. The Solution: Diagnex AI Medical Portal
addSectionHeader("3. The Solution: Intelligent Multi-Modal Diagnosis & VQA");
addParagraph("Diagnex addresses these vulnerabilities by offering a complete multi-modal clinical portal. It provides a non-intrusive, anonymous experience to encourage honest usage and supports both closed (yes/no) and open-ended natural language medical queries. The platform integrates a standardized, clinically validated answer system to prevent ambiguous output. It handles files across multiple categories, including X-Rays, CT Scans, MRIs, Ultrasounds, and biochemical Pathology reports, where it dynamically renders structured metabolic tables (such as Hemoglobin, WBC count, and Cholesterol levels).");

// 4. Safety Traffic Light System & Doctor Escalation
addSectionHeader("4. Safety Traffic Light Gating & Specialist Escalation");
addListItem("GREEN ZONE (Certainty >= 85%)", "High confidence diagnosis. Displays full diagnostic findings and enables the VQA interactive chat widget so clinicians can ask follow-up questions.");
addListItem("YELLOW ZONE (Certainty 70% - 84%)", "Moderate confidence. Renders findings but stamps them with prominent warning flags and disclaimers urging verification.");
addListItem("RED ZONE (Certainty < 70%)", "Honest Uncertainty Trigger. The AI completely suppresses diagnostic outputs to safeguard the patient. Instead of guessing, it locks the screen and automatically triggers a Specialist Locator to route patients to nearby radiologists.");

// 5. Underpinning Safety & Certainty Algorithms
addSectionHeader("5. Core Safety & Mathematical Gating Algorithms");
addListItem("Monte Carlo Dropout (BNN)", "Performs 50+ forward passes at inference time with active dropout layers. The variance between outputs determines the model's epistemic uncertainty.");
addListItem("Shannon Entropy Indexing", "Computes the entropy H(X) = - ∑ P(x_i) log₂ P(x_i) of class probability vectors. High entropy triggers the Red Zone.");
addListItem("Conformal Prediction Sets", "Enforces valid diagnostic intervals to guarantee statistical coverage under atypical scan parameters.");
addListItem("Out-of-Distribution (OOD) VAEs", "Flags scan artifacts, high scanner noise, or foreign objects to prevent out-of-distribution hallucinations.");

// 6. Expected Clinical Impact
addSectionHeader("6. Expected Clinical Impact");
addParagraph("Diagnex establishes a critical milestone in medical AI integration. By bridging the gap between deep learning capabilities and strict clinical safety thresholds, it safeguards patient health by avoiding wrong answers. It accelerates the diagnostic pipeline for high-certainty cases, reduces patient anxiety, and safely filters complex cases directly to certified healthcare practitioners.");

// Save PDF
const pdfData = doc.output();
fs.writeFileSync("d:\\diagnex\\SYNOPSIS.pdf", pdfData, "binary");
console.log("PDF successfully generated at d:\\diagnex\\SYNOPSIS.pdf");
console.log("Current final y coordinate is:", y);
