# 🧬 PROJECT SYNOPSIS: DIAGNEX

## 1. Project Title & Overview
**DIAGNEX: Full-Stack AI-Assisted Medical Imaging & Visual Question Answering (VQA) Portal**

Diagnex operates as an intelligent digital radiologist assistant that analyzes complex medical images and answers diagnostic questions instantly in natural language.

---

## 2. The Problem: Overburdened Radiologists & Unsafe AI Models
Interpretation of medical scans (X-Rays, MRIs, CTs, and Ultrasounds) requires certified experts. Due to a global shortage of clinical radiologists, patient wait times for critical diagnostics have increased. While deep learning models offer a potential solution for automation, typical AI models are prone to hallucinating predictions when presented with low-resolution, noisy, or atypical inputs. Generating false positive or false negative results can lead to incorrect treatments, making unguarded AI unsafe for clinical diagnostics.

---

## 3. The Solution: Intelligent Multi-Modal Diagnosis & VQA
Diagnex addresses these vulnerabilities by offering a complete multi-modal clinical portal. It provides a non-intrusive, anonymous experience to encourage honest usage and supports both closed (yes/no) and open-ended natural language medical queries. The platform integrates a standardized, clinically validated answer system to prevent ambiguous output. It handles files across multiple categories, including X-Rays, CT Scans, MRIs, Ultrasounds, and biochemical Pathology reports, where it dynamically renders structured metabolic tables (such as Hemoglobin, WBC count, and Cholesterol levels).

---

## 4. Safety Traffic Light Gating & Specialist Escalation
- **GREEN ZONE (Certainty >= 85%)**: High confidence diagnosis. Displays full diagnostic findings and enables the VQA interactive chat widget so clinicians can ask follow-up questions.
- **YELLOW ZONE (Certainty 70% - 84%)**: Moderate confidence. Renders findings but stamps them with prominent warning flags and disclaimers urging verification.
- **RED ZONE (Certainty < 70%)**: Honest Uncertainty Trigger. The AI completely suppresses diagnostic outputs to safeguard the patient. Instead of guessing, it locks the screen and automatically triggers a Specialist Locator to route patients to nearby radiologists.

---

## 5. Core Safety & Mathematical Gating Algorithms
- **Monte Carlo Dropout (BNN)**: Performs 50+ forward passes at inference time with active dropout layers. The variance between outputs determines the model's epistemic uncertainty.
- **Shannon Entropy Indexing**: Computes the entropy $H(X) = - \sum P(x_i) \log_2 P(x_i)$ of class probability vectors. High entropy triggers the Red Zone.
- **Conformal Prediction Sets**: Enforces valid diagnostic intervals to guarantee statistical coverage under atypical scan parameters.
- **Out-of-Distribution (OOD) VAEs**: Flags scan artifacts, high scanner noise, or foreign objects to prevent out-of-distribution hallucinations.

---

## 6. Expected Clinical Impact
Diagnex establishes a critical milestone in medical AI integration. By bridging the gap between deep learning capabilities and strict clinical safety thresholds, it safeguards patient health by avoiding wrong answers. It accelerates the diagnostic pipeline for high-certainty cases, reduces patient anxiety, and safely filters complex cases directly to certified healthcare practitioners.
