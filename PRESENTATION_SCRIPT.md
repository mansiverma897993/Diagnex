# 🧬 Diagnex - Presentation & Demo Script

Use this script to explain and demonstrate the **Diagnex** project during reviews or presentations. It is written in simple, clear English with actions and talking points.

---

## 📋 Part 1: Project Overview & Introduction (1-2 mins)

**What to Say:**
> *"Hello everyone. Today I am presenting **Diagnex**, a full-stack AI-assisted Medical Imaging and Visual Question Answering portal designed for radiologists and patients. 
> 
> The core problem we are solving is clinical safety in generative AI. Instead of giving blind guesses on noisy, blurry, or incorrect scans, Diagnex implements the **Honest Uncertainty Safety Gate** algorithm. This ensures that the AI only provides answers when it is highly confident, and safely locks down or recommends doctor consultations when confidence is low."*

---

## 🛠️ Part 2: High-Level Architecture & Tech Stack (1 min)

**What to Say:**
> *"Let's talk about the technology stack:
> 1. **Frontend**: Built using **React 19** and **Vite** for fast performance and hot-reloading.
> 2. **Animations**: Styled using **GSAP** (GreenSock) for smooth scan animations, glowing indicators, and interactive UI transitions.
> 3. **Backend**: Powered by a high-performance **FastAPI** server in Python to process live uploads.
> 4. **API Integration**: The frontend communicates via REST APIs (`/api/upload` and `/api/chat`). If the backend goes offline, the frontend has a **resilient local fallback engine** so the application never crashes."*

---

## 💻 Part 3: Step-by-Step Live Demo Track (3-4 mins)

Follow these steps to demonstrate the application:

### Step 1: Login & Welcome Dashboard
*   **Action**: Show the landing portal, type any mock details, and click **Login / Get Started**.
*   **What to Say**: 
    > *"First, we log in to our secure patient and clinician portal. Here, we see a premium dark dashboard showing our scan history and medical suites."*

### Step 2: Uploading & Visual Image Scanning
*   **Action**: Click **Diagnostic Lab** on the sidebar. Choose **X-Ray** and click **Sample 1: Chest X-Ray (Normal)** or upload a real image.
*   **What to Say**: 
    > *"Now, let's load a scan. When we select a file, the actual medical scan image is uploaded and immediately rendered in our visualizer box on the right. 
    > Let's click **Run Diagnostic AI Analysis**. You will see the GSAP scanning wave sweep over the actual scan image while progress logs are parsed in real-time."*

### Step 3: Diagnostic Results & Safety Dot System
*   **Action**: Wait for results to load. Point at the **Green/Yellow/Red Dot** indicator and the report details.
*   **What to Say**: 
    > *"The scanning is complete, and we are taken to the **Analysis Results** view. 
    > On the left, we see our analyzed scan. On the right, the **Honest Uncertainty Safety Gate** is displayed. 
    > Here, the AI calculated a **94% confidence score**, placing it in the **Green Zone**. Because the certainty is high, the portal outputs the complete diagnostic telemetry and enables our chat assistant."*

### Step 4: Interactive Clinical VQA Chat
*   **Action**: Scroll down to the Chat panel. Type: *"Is there any sign of pneumonia?"* and click Send.
*   **What to Say**: 
    > *"Below the report, we have the **Clinical Chat AI**. This is a Visual Question Answering (VQA) chat. We can ask specific questions about our scan. As you can see, the AI correctly identifies that there are no consolidations or signs of pneumonia."*

### Step 5: Digital Pathology Lab Report (Special Feature)
*   **Action**: Go back to the **Diagnostic Lab**, select **Pathology** category, load/upload a file, and click **Run Analysis**.
*   **What to Say**: 
    > *"Let's test our Pathology reporting. For blood and biochemical lab reports, we don't render anatomical images. 
    > Instead, Diagnex generates an interactive **Digital Reference Laboratory Sheet** rendering critical patient metrics—such as Hemoglobin, WBC count, TSH, and Cholesterol—highlighting normal, borderline, or critical values dynamically."*

### Step 6: Low-Certainty Safety Lockout
*   **Action**: Go back to **Diagnostic Lab**, select **Ultrasound**, choose **Sample 4: Ultrasound (Gallstones)**, and click **Run Analysis**.
*   **What to Say**: 
    > *"Finally, let's look at what happens when the AI is uncertain. We will analyze the ultrasound sample. 
    > As you can see, the AI confidence is only **54%**, which triggers a **Red Alert** due to potential noise in ultrasound readings. 
    > The AI refuses to diagnose the patient to prevent medical errors. Instead, the portal locks the self-diagnosis screen and automatically triggers our **Specialist Locator**, recommending local radiologists near the patient."*

---

## 🧠 Part 4: Conclusion (30 secs)

**What to Say:**
> *"To conclude, Diagnex successfully blends a high-fidelity, interactive user interface with a robust, safety-first clinical backend. It ensures patient safety while providing powerful medical insights. Thank you!"*
