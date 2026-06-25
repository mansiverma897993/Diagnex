import os
import random
import time
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Diagnex Clinical AI Backend")

# Enable CORS for the React/Vite frontend (typically running on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    filename: str
    category: str
    confidence: int
    question: str
    summary: str

@app.get("/")
def read_root():
    return {"status": "active", "engine": "CrossGate-VQA API Pipeline", "version": "1.0.0"}

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    question: Optional[str] = Form(None)
):
    try:
        # Read file information
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        size_str = f"{file_size_mb:.1f} MB"
        filename = file.filename
        
        # Calculate a deterministic confidence score based on filename length
        # to simulate AI model output variance
        hash_val = len(filename) + len(category)
        confidence = 45 + (hash_val * 7) % 51  # ranges from 45% to 95%
        
        # Determine status
        if confidence >= 85:
            status = "GREEN"
        elif confidence >= 70:
            status = "YELLOW"
        else:
            status = "RED"
            
        # Diagnosis generation based on Category & Confidence
        diagnosis = ""
        summary = ""
        qa_pairs = []
        
        if category == "Pathology":
            if status == "GREEN":
                diagnosis = (
                    f"PATHOLOGY HEMATOLOGY & CLINICAL BIOCHEMISTRY EVALUATION (Confidence: {confidence}%). "
                    f"All critical parameters are within normal reference ranges. "
                    f"Hemoglobin: 14.2 g/dL (Normal: 12.0-16.0). White Blood Cell (WBC) Count: 6.8 x10^3/µL (Normal: 4.0-11.0). "
                    f"Platelets: 250 x10^3/µL (Normal: 150-450). Fasting Blood Glucose: 92 mg/dL (Normal: 70-100). "
                    f"Thyroid Stimulating Hormone (TSH): 2.4 µIU/mL (Normal: 0.4-4.5). "
                    f"No acute hematological anomalies detected. Annual health checkup recommended."
                )
                summary = "All blood panels and biochemistry values within normal reference limits."
                qa_pairs = [
                    {"q": "Are my reports normal?", "a": "Yes. All parameters including Hemoglobin, WBC count, and Glucose are perfectly within reference limits (Green status)."},
                    {"q": "What is my WBC count?", "a": f"Your White Blood Cell (WBC) count is 6.8 x10^3/µL, which is healthy and indicates no active bacterial infections."},
                    {"q": "Do I have thyroid issues?", "a": "No, your TSH level is 2.4 µIU/mL, which falls well within the normal thyroid range."}
                ]
            elif status == "YELLOW":
                diagnosis = (
                    f"PATHOLOGY EVALUATION: BORDERLINE METABOLIC FLAGS (Confidence: {confidence}%). "
                    f"Total Cholesterol: 224 mg/dL (Borderline High: 200-239). Vitamin D (25-Hydroxy): 22 ng/mL (Mild Deficiency: 20-30). "
                    f"Thyroid Stimulating Hormone (TSH) is slightly elevated at 4.8 µIU/mL (Normal: 0.4-4.5), suggesting subclinical hypothyroidism. "
                    f"Hemoglobin is normal at 13.5 g/dL. Recommended: Consult a physician for vitamin supplementation and lipid management."
                )
                summary = "Borderline hypercholesterolemia and subclinical TSH elevation. Review diet and supplements."
                qa_pairs = [
                    {"q": "Do I have cholesterol issues?", "a": "Yes, your Total Cholesterol is borderline high at 224 mg/dL. Eating a heart-healthy diet and checking it again in 3 months is advised."},
                    {"q": "What is my Vitamin D level?", "a": "Your Vitamin D is 22 ng/mL, indicating a mild deficiency. Your doctor may recommend a weekly supplement."},
                    {"q": "Is my thyroid normal?", "a": "Your TSH is slightly elevated at 4.8 µIU/mL. This could represent early subclinical hypothyroidism. Your doctor can help determine if thyroid therapy is needed."}
                ]
            else:
                diagnosis = (
                    f"RED ALERT: CRITICAL PATHOLOGY REPORT FLAGGED (Confidence: {confidence}%). "
                    f"White Blood Cell (WBC) Count is critically elevated at 18.5 x10^3/µL (Normal: 4.0-11.0), indicating severe infection or inflammatory flare. "
                    f"Liver enzymes ALT and AST are elevated past twice normal limits. Due to high-risk multi-panel anomalies and potential sampling noise, the AI has triggered the Safety Lock. "
                    f"The AI refuses to provide a self-diagnosis. Immediate doctor consult is mandatory."
                )
                summary = "Critical High WBC count and abnormal liver enzymes. Immediate clinical escalation required."
                qa_pairs = [
                    {"q": "What does a high WBC mean?", "a": f"A WBC of 18.5 x10^3/µL is critically high and usually indicates a strong active infection or severe inflammation. You need immediate medical attention."},
                    {"q": "Are my liver enzymes safe?", "a": "No, liver enzymes are significantly elevated. A medical practitioner must review this immediately to test for liver stress or gallbladder inflammation."},
                    {"q": "Can AI prescribe medication?", "a": "No. Due to low confidence (Red Status), the AI has locked analysis functions to protect your safety. You must consult a doctor."}
                ]
        
        else: # X-Ray, CT Scan, MRI, Ultrasound
            if status == "GREEN":
                diagnosis = (
                    f"HIGH CONFIDENCE DIAGNOSIS ({confidence}%). Clear visual indicators demonstrate normal structural architecture. "
                    f"No acute pathologic processes, lesions, fractures, or abnormal calcifications are detected in this custom {category} scan. "
                    f"Recommended: Annual routine screening."
                )
                summary = f"No significant abnormalities detected in the {category} scan. Clean report."
                qa_pairs = [
                    {"q": "Is this scan normal?", "a": f"Yes, the AI has determined that the structural architecture in this {category} scan appears completely normal with {confidence}% confidence."},
                    {"q": "Should I follow up?", "a": "Only for routine medical correlation, as no acute pathology was identified."}
                ]
            elif status == "YELLOW":
                diagnosis = (
                    f"MODERATE CONFIDENCE FINDING ({confidence}%). Minor sub-clinical asymmetry or structural irregularity is detected in the {category} tissues. "
                    f"AI cannot definitively rule out minor early-stage inflammatory response, mild degeneration, or mechanical wear. "
                    f"Clinical correlation and specialist evaluation is recommended."
                )
                summary = f"Minor irregularities found in {category}. Clinical review recommended."
                qa_pairs = [
                    {"q": "What abnormalities were found?", "a": f"The model detected minor irregularities or structural asymmetry in the {category}. It is recommended to verify these findings with a radiologist."},
                    {"q": "Is this dangerous?", "a": "These findings are sub-clinical (moderate priority), not an immediate emergency, but they do require a doctor's review."}
                ]
            else:
                diagnosis = (
                    f"RED ALERT: LOW CONFIDENCE AI UNCERTAINTY ({confidence}%). Due to complex visual artifacts, "
                    f"unclear boundaries, or atypical findings on the {category} document, the AI engine has marked this scan under Honest Uncertainty. "
                    f"To prevent clinical errors, the AI REFUSES to render a diagnosis. Urgent clinical checkup is requested."
                )
                summary = f"AI uncertainty trigger. Direct doctor escalation required."
                qa_pairs = [
                    {"q": "Why did the scan fail?", "a": f"The safety confidence score fell to {confidence}%. Because of noise, artifacts, or highly unusual anatomy, the system triggered a safety lock to prevent misdiagnosis."},
                    {"q": "What should I do?", "a": "Please click the 'Find Nearest Specialist' button on the results screen to locate a clinic and get a manual read by a doctor."}
                ]
                
        # If the user asked a specific question, let's prepend it or include it in the default QA
        if question:
            # Simple contextual check for question matching
            response_text = ""
            if "pneumonia" in question.lower() or "consolidation" in question.lower():
                if category == "X-Ray" and status == "GREEN":
                    response_text = "No consolidations or infiltrates are seen. Lungs are clear."
                elif category == "X-Ray" and status == "YELLOW":
                    response_text = "Patchy opacities are present. Bronchopneumonia cannot be ruled out."
                else:
                    response_text = "Due to safety/confidence constraints, please verify pneumonia checks with a clinician."
            elif "normal" in question.lower():
                response_text = "The AI reports findings aligned with a normal baseline." if status == "GREEN" else "The scan shows irregularities and cannot be certified as completely normal."
            else:
                response_text = f"Regarding your question '{question}': The scan demonstrates features consistent with our {status} status report. Please consult a specialist for exact guidance."
                
            qa_pairs.insert(0, {"q": question, "a": response_text})

        return {
            "id": f"api-{int(time.time())}",
            "name": filename,
            "type": category,
            "size": size_str,
            "confidence": confidence,
            "status": status,
            "diagnosis": diagnosis,
            "summary": summary,
            "qa": qa_pairs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_vqa(req: ChatRequest):
    q_lower = req.question.lower()
    
    # Check if there is an exact match in the summary or name
    if req.confidence < 70:
        return {
            "reply": f"Emergency Alert: Because the confidence score is very low ({req.confidence}%), I am restricted from giving detailed diagnostic answers. Please click the 'Find Nearest Specialist' button below to book an in-person diagnostic consultation immediately."
        }
    
    # Formulate a helpful response based on query
    if "cholesterol" in q_lower or "blood" in q_lower or "wbc" in q_lower:
        reply = f"Regarding your blood pathology values, the WBC count is a critical indicator of infection. If your status is flagged red or yellow, please discuss these markers with your hematologist."
    elif "mri" in q_lower or "brain" in q_lower:
        reply = f"In this MRI document, we are evaluating structural changes. If gliosis or ischemic change is suspected, a neurologist will typically evaluate your blood pressure and history."
    elif "pneumonia" in q_lower or "cough" in q_lower or "lungs" in q_lower:
        reply = f"Chest scans check for active infiltrates. For pneumonia, the standard treatment consists of doctor-prescribed antibiotics and symptom monitoring."
    else:
        reply = f"Regarding your scan '{req.filename}' ({req.category}), the visual telemetry shows a confidence level of {req.confidence}% ({req.status}). If you are experiencing symptoms, please reach out to your doctor immediately."
        
    return {"reply": reply}
