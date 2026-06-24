import React, { useState, useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clipboard,
  Clock,
  Compass,
  FileText,
  Heart,
  HelpCircle,
  Layers,
  List,
  Loader2,
  LogIn,
  LogOut,
  Map,
  MapPin,
  MessageSquare,
  Navigation,
  Phone,
  Play,
  Plus,
  Search,
  Send,
  ShieldAlert,
  Sparkles,
  UploadCloud,
  User,
  Users,
  X
} from 'lucide-react'

// Mock database of pre-loaded sample scans for testing and demonstration
const SAMPLE_CASES = [
  {
    id: 'sample-chest-normal',
    name: 'Normal_Chest_XRay_P12.png',
    type: 'X-Ray',
    size: '4.2 MB',
    confidence: 94,
    diagnosis: 'NORMAL CHEST X-RAY. No focal airspace consolidation, pleural effusion, or pneumothorax is identified. Cardiomediastinal silhouette and hilar contours are within normal limits. The lung fields are clear and well-expanded. Visualized bony structures and soft tissues are unremarkable.',
    summary: 'No significant abnormalities detected in the chest X-ray. Lungs appear fully clear.',
    qa: [
      { q: "Is there any sign of pneumonia?", a: "No, there are no focal airspace consolidations, infiltrates, or patchy opacities. The lung fields are completely clear, making pneumonia highly unlikely (94% confidence)." },
      { q: "How is the heart size?", a: "The cardiomediastinal silhouette is within normal limits. There is no evidence of cardiomegaly (heart enlargement) or contour distortion." },
      { q: "Are the ribs normal?", a: "Yes, the visualized bony structures, including the ribs and clavicles, are intact with no fractures or abnormalities." }
    ]
  },
  {
    id: 'sample-chest-pneumonia',
    name: 'Chest_XRay_Bilateral_Infiltrates.png',
    type: 'X-Ray',
    size: '5.8 MB',
    confidence: 82,
    diagnosis: 'MULTIFOCAL PNEUMONIA. Patchy airspace opacities are noted in bilateral lower zones, significantly more pronounced on the right side. Findings are highly suggestive of multifocal bronchopneumonia or atypical infection. Mild pleural thickening is present. Recommend clinical correlation and immediate follow-up.',
    summary: 'Bilateral lower zone airspace opacities, highly suggestive of lobar pneumonia. Clinical verification is recommended.',
    qa: [
      { q: "Do I have pneumonia?", a: "Yes, the AI has identified patchy airspace opacities in both lower lung zones, which is a classic signature of pneumonia. The confidence score is 82% (Yellow), indicating clinical verification and doctor consult is recommended." },
      { q: "What should my next steps be?", a: "You should schedule a consultation with a pulmonologist or physician. The doctor will likely correlate these findings with your symptoms (fever, cough) and may prescribe antibiotics." },
      { q: "Is there a pleural effusion?", a: "There is mild pleural thickening, but no large free-flowing pleural effusion is clearly visualized. However, clinical correlation is advised." }
    ]
  },
  {
    id: 'sample-brain-gliosis',
    name: 'Brain_MRI_FLAIR_T2.pdf',
    type: 'MRI',
    size: '8.4 MB',
    confidence: 78,
    diagnosis: 'WHITE MATTER GLIOSIS. Foci of hyperintense signal on T2/FLAIR sequences are observed within the bilateral periventricular and subcortical white matter. These findings most likely represent chronic microvascular ischemic changes or mild reactive gliosis. No acute intracranial hemorrhage, mass effect, or midline shift is identified.',
    summary: 'Focal periventricular T2/FLAIR hyperintensities consistent with chronic microvascular gliosis. Doctor verification suggested.',
    qa: [
      { q: "Do I have a brain tumor?", a: "No acute intracranial masses, mass effect, or midline shifts are seen. The hyperintensities represent white matter gliosis (often due to small vessel aging), not a tumor, but verification with a neurologist is recommended (78% confidence)." },
      { q: "What causes white matter gliosis?", a: "Common causes include chronic microvascular ischemia, high blood pressure, migraines, or normal age-related changes. A neurologist can help evaluate your risk factors." },
      { q: "Is this an emergency?", a: "No acute infarct (stroke) or active hemorrhage is detected. It is not an immediate emergency, but requires routine clinical follow-up." }
    ]
  },
  {
    id: 'sample-abd-gallstones',
    name: 'Abdomen_Ultrasound_Gallbladder.jpg',
    type: 'Ultrasound',
    size: '3.1 MB',
    confidence: 54,
    diagnosis: 'CHOLELITHIASIS WITH ACUTE CHOLECYSTITIS? The gallbladder is distended and demonstrates multiple mobile echogenic foci with posterior acoustic shadowing, consistent with gallstones. The gallbladder wall is mildly thickened measuring 3.8mm (normal < 3mm). Mild pericholecystic fluid is suspected. RED ALERT: Due to borderline measurements and low confidence estimation (54%), AI cannot rule out acute cholecystitis. Direct specialist review is mandatory.',
    summary: 'Gallbladder stones detected with borderline wall thickening. AI confidence is low (54%). Immediate specialist consultation required.',
    qa: [
      { q: "Do I need surgery?", a: "AI detected gallbladder stones (cholelithiasis) and possible wall thickening. Because the confidence is below 60% (Red Dot), the AI REFUSES to make a definitive diagnosis. You must see a gastroenterologist or surgeon immediately to check for acute cholecystitis." },
      { q: "Why is the confidence so low?", a: "Acoustic shadowing and gas interference frequently obscure ultrasound margins. To protect your safety, the system flags this as 'Honest Uncertainty' and escalates to a medical practitioner." },
      { q: "What symptoms should I watch out for?", a: "Watch for severe upper right abdomen pain, fever, nausea, vomiting, or yellowing of skin (jaundice). If present, seek emergency medical care immediately." }
    ]
  }
];

// Mock database of nearby Radiologists / Doctors
const MOCK_DOCTORS = [
  {
    id: 'doc-neha',
    name: 'Dr. Neha Sharma, MD',
    specialty: 'Thoracic Radiologist (Chest & Lungs)',
    clinic: 'City Chest Imaging & Diagnostic Center',
    distance: '1.2 km',
    lat: 42,
    lng: 35,
    rating: 4.9,
    reviews: 124,
    phone: '+91 98765 43210',
    address: '402, Green Avenue, Medical District',
    availability: 'Today (2:00 PM - 6:00 PM)',
    matchTypes: ['X-Ray', 'CT Scan']
  },
  {
    id: 'doc-vikram',
    name: 'Dr. Vikram Aditya, DM',
    specialty: 'Neuroradiologist (Brain & Spine)',
    clinic: 'Apex Neuroscan Institute',
    distance: '2.7 km',
    lat: 68,
    lng: 60,
    rating: 4.8,
    reviews: 89,
    phone: '+91 98765 43222',
    address: 'Suite 12, Apex Healthcare Tower, Sector 4',
    availability: 'Tomorrow (10:00 AM - 1:00 PM)',
    matchTypes: ['MRI', 'CT Scan']
  },
  {
    id: 'doc-rajesh',
    name: 'Dr. Rajesh Patel, MD',
    specialty: 'Abdominal Imaging Specialist',
    clinic: 'Metro Diagnostic & Ultrasound Labs',
    distance: '0.8 km',
    lat: 28,
    lng: 25,
    rating: 4.7,
    reviews: 210,
    phone: '+91 98765 43233',
    address: '15, Ground Floor, Central Health Plaza',
    availability: 'Today (4:00 PM - 8:00 PM)',
    matchTypes: ['Ultrasound']
  },
  {
    id: 'doc-sarah',
    name: 'Dr. Sarah Jenkins, FRCR',
    specialty: 'General Radiologist & Pathology Lead',
    clinic: 'Diagnex Reference Laboratory',
    distance: '3.5 km',
    lat: 52,
    lng: 78,
    rating: 4.9,
    reviews: 342,
    phone: '+1 (555) 019-2834',
    address: '88, Parkway Boulevard, Health Hub',
    availability: 'Monday - Friday (9:00 AM - 5:00 PM)',
    matchTypes: ['Pathology', 'X-Ray', 'MRI', 'Ultrasound', 'CT Scan']
  }
];

function App() {
  // GSAP animation refs
  const blob1Ref = useRef(null);
  const blob2Ref = useRef(null);
  const blob3Ref = useRef(null);
  const welcomeGlow1Ref = useRef(null);
  const welcomeGlow2Ref = useRef(null);
  const welcomeGlow3Ref = useRef(null);

  // Floating background green nodes list
  const [bgNodes] = useState(() => {
    return Array.from({ length: 20 }).map((_, i) => ({
      id: i,
      size: Math.random() * 8 + 4,
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      opacity: Math.random() * 0.4 + 0.2
    }));
  });


  // Navigation / View State
  const [currentView, setCurrentView] = useState('welcome');

  // User Authentication State
  const [user, setUser] = useState(null); // { name: 'Aryan', email: 'aryan@health.org', phone: '+91 98765 12345' }
  const [authMode, setAuthMode] = useState('signup'); // 'signup' or 'login'
  const [authForm, setAuthForm] = useState({ name: '', phone: '', email: '', password: '' });

  // Scan / AI Lab State
  const [selectedScanType, setSelectedScanType] = useState('X-Ray');
  const [selectedFile, setSelectedFile] = useState(null); // { name, size, type, isSample, sampleId }
  const [userQuestion, setUserQuestion] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState([]);
  const [scanProgressIndex, setScanProgressIndex] = useState(0);

  // Current Active Scan Result
  const [activeResult, setActiveResult] = useState(null);
  // Chat dialogue state (VQA)
  const [vqaChat, setVqaChat] = useState([]);
  const [vqaQuestion, setVqaQuestion] = useState('');

  // Doctor/Map State
  const [searchDoctorQuery, setSearchDoctorQuery] = useState('');
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [bookingDoctor, setBookingDoctor] = useState(null);
  const [bookingForm, setBookingForm] = useState({ date: '', time: '', notes: '' });
  const [bookingSuccess, setBookingSuccess] = useState(false);
  const [mapFilterDistance, setMapFilterDistance] = useState('all'); // 'all', '1km', '3km'

  // Dashboard scan history
  const [scanHistory, setScanHistory] = useState([
    { id: 'h1', name: 'Chest_XRay_Routine_Aryan.png', type: 'X-Ray', date: 'Apr 14, 2026', confidence: 91, status: 'GREEN', summary: 'Lungs are clear. Normal chest scan.' },
    { id: 'h2', name: 'Lumbar_Spine_MRI.pdf', type: 'MRI', date: 'Apr 10, 2026', confidence: 76, status: 'YELLOW', summary: 'Mild L4-L5 disc bulge, verify with therapist.' },
    { id: 'h3', name: 'Thyroid_Ultrasound.jpg', type: 'Ultrasound', date: 'Apr 05, 2026', confidence: 58, status: 'RED', summary: 'Atypical nodule found. Escalated to endocrinologist.' }
  ]);

  // Clinical Assistant Chat AI State
  const [chatHistory, setChatHistory] = useState([
    { sender: 'ai', text: "Hello! I am Diagnex Clinical Assistant. Ask me anything about scan preparation, safety guidelines, or general medical imaging technology." }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatTyping, setIsChatTyping] = useState(false);

  // Log steps list for scanning effect
  const logSteps = [
    "Establishing handshake with CrossGate-VQA medical API...",
    "Uploading raw image buffers (secure TLS 1.3)...",
    "Pre-processing tensor grids (2048x2048 high-quality format)...",
    "Running structural segmentation (U-Net feature extractor)...",
    "Querying deep visual question-answering neural network...",
    "Extracting Bayesian uncertainty bounds...",
    "Compiling confidence thresholds and localizing findings...",
    "Analysis complete! Ready to view."
  ];

  // Ref for auto-scrolling logs
  const logEndRef = useRef(null);
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [scanProgress]);

  useEffect(() => {
    if (blob1Ref.current) {
      gsap.to(blob1Ref.current, {
        x: 'random(-90, 90)',
        y: 'random(-90, 90)',
        rotation: 'random(0, 360)',
        scale: 'random(0.9, 1.25)',
        duration: 5.5,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }
    if (blob2Ref.current) {
      gsap.to(blob2Ref.current, {
        x: 'random(-110, 110)',
        y: 'random(-110, 110)',
        rotation: 'random(-360, 0)',
        scale: 'random(0.85, 1.2)',
        duration: 7,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }
    if (blob3Ref.current) {
      gsap.to(blob3Ref.current, {
        x: 'random(-80, 80)',
        y: 'random(-80, 80)',
        rotation: 'random(-180, 180)',
        scale: 'random(0.9, 1.15)',
        duration: 4.8,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }

    if (welcomeGlow1Ref.current) {
      gsap.to(welcomeGlow1Ref.current, {
        x: 'random(-65, 65)',
        y: 'random(-65, 65)',
        scale: 'random(0.9, 1.25)',
        duration: 7,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }
    if (welcomeGlow2Ref.current) {
      gsap.to(welcomeGlow2Ref.current, {
        x: 'random(-85, 85)',
        y: 'random(-85, 85)',
        scale: 'random(0.85, 1.2)',
        duration: 9,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }
    if (welcomeGlow3Ref.current) {
      gsap.to(welcomeGlow3Ref.current, {
        x: 'random(-55, 55)',
        y: 'random(-55, 55)',
        scale: 'random(0.9, 1.15)',
        duration: 6,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    }

    gsap.utils.toArray('.telemetry-node').forEach((node) => {
      gsap.to(node, {
        x: 'random(-125, 125)',
        y: 'random(-125, 125)',
        duration: 'random(6, 12)',
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        repeatRefresh: true
      });
    });

    return () => {
      if (blob1Ref.current) gsap.killTweensOf(blob1Ref.current);
      if (blob2Ref.current) gsap.killTweensOf(blob2Ref.current);
      if (blob3Ref.current) gsap.killTweensOf(blob3Ref.current);
      if (welcomeGlow1Ref.current) gsap.killTweensOf(welcomeGlow1Ref.current);
      if (welcomeGlow2Ref.current) gsap.killTweensOf(welcomeGlow2Ref.current);
      if (welcomeGlow3Ref.current) gsap.killTweensOf(welcomeGlow3Ref.current);
      gsap.killTweensOf('.telemetry-node');
    };
  }, [currentView, user]);

  // Sign up / Login logic
  const handleAuthSubmit = (e) => {
    e.preventDefault();
    if (authMode === 'signup') {
      const newUser = {
        name: authForm.name || 'Aryan',
        email: authForm.email || 'aryan@diagnex.org',
        phone: authForm.phone || '+91 99999 88888'
      };
      setUser(newUser);
    } else {
      setUser({
        name: 'Aryan',
        email: authForm.email || 'aryan@diagnex.org',
        phone: '+91 98765 12345'
      });
    }
    setCurrentView('dashboard');
  };

  const handleGoogleLogin = () => {
    setUser({
      name: 'Aryan Verma',
      email: 'aryan.verma@gmail.com',
      phone: '+91 90123 45678'
    });
    setCurrentView('dashboard');
  };

  const handleLogout = () => {
    setUser(null);
    setCurrentView('welcome');
  };

  // Preset sample click handler
  const handleLoadSample = (sampleId) => {
    const sample = SAMPLE_CASES.find(c => c.id === sampleId);
    if (sample) {
      setSelectedFile({
        name: sample.name,
        size: sample.size,
        type: sample.type,
        isSample: true,
        sampleId: sample.id
      });
      setSelectedScanType(sample.type);
    }
  };

  // Handle manual file selection simulation
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile({
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(1) + ' MB',
        type: selectedScanType,
        isSample: false
      });
    }
  };

  const handleChatSubmit = (e, textOverride = '') => {
    if (e) e.preventDefault();
    const query = textOverride || chatInput;
    if (!query.trim()) return;

    const updatedHistory = [...chatHistory, { sender: 'user', text: query }];
    setChatHistory(updatedHistory);
    setChatInput('');
    setIsChatTyping(true);

    setTimeout(() => {
      let aiResponse = "I'm not sure how to answer that clinical query. Could you please specify if you're asking about X-Rays, MRI scans, Ultrasound guidelines, contrast preparation, or general safety instructions?";

      const q = query.toLowerCase();
      if (q.includes('mri') || q.includes('magnetic resonance')) {
        aiResponse = "**Magnetic Resonance Imaging (MRI) Preparation Guidelines**:\n\n" +
          "1. **Metal Screening**: Absolute metal clearance is mandatory. Please remove keys, coins, cards, jewelry, and hearing aids.\n" +
          "2. **Implant Safety**: Notify the technician if you have any pacemaker, metallic pins, artificial heart valves, or joint replacements.\n" +
          "3. **Fasting**: 4-6 hours of fasting is required only if contrast dye (Gadolinium) is scheduled for abdominal/pelvic MRI scans.\n" +
          "4. **Claustrophobia**: Please mention to staff beforehand if you experience claustrophobia; we can arrange open MRI configurations or soft breathing guides.";
      } else if (q.includes('x-ray') || q.includes('xray') || q.includes('radiation')) {
        aiResponse = "**X-Ray & Radiation Safety Protocol**:\n\n" +
          "- **Lead Shielding**: Always wear protective lead aprons to shield organs not being scanned.\n" +
          "- **Pregnancy Warning**: Alert clinical staff immediately if you are or suspect you might be pregnant. Alternative methods (Ultrasound/MRI) may be scheduled.\n" +
          "- **Clothing**: Wear loose clothing. Remove clothing items containing metal zippers, buttons, or metal clasps near the scan zone.";
      } else if (q.includes('ultrasound') || q.includes('sonography')) {
        aiResponse = "**Ultrasound Preparation Guidelines**:\n\n" +
          "- **Abdomen Ultrasound**: Fast for 8-12 hours prior to the scan (no food or drinks except clear water) to reduce gallbladder gas.\n" +
          "- **Pelvic / Obstetric Ultrasound**: Drink 32-40 ounces of water 1 hour before and **do not urinate**. A full bladder acts as an acoustic window for visualization.\n" +
          "- **Comfort**: Wear two-piece outfits to allow easy access to the scan area.";
      } else if (q.includes('contrast') || q.includes('dye') || q.includes('gadolinium')) {
        aiResponse = "**Contrast Agent Protocols**:\n\n" +
          "- **Hydration**: Drink plenty of water before and after contrast injection to assist kidneys in flushing out the contrast agent.\n" +
          "- **Kidney Function**: A recent GFR/Creatinine blood test is required for patients over 60 or with diabetic histories.\n" +
          "- **Allergies**: If you have history of iodine or contrast dye reactions, inform the radiologist. Prep medication (steroids/antihistamines) may be ordered.";
      } else if (q.includes('hello') || q.includes('hi') || q.includes('help')) {
        aiResponse = "Hello! I am your AI clinical assistant here to guide you. Try asking questions like:\n" +
          "• *What are MRI preparation rules?*\n" +
          "• *How do I prepare for an abdominal ultrasound?*\n" +
          "• *What should I know about X-Ray radiation safety?*\n" +
          "• *Do I need to fast for contrast dye?*";
      }

      setChatHistory(prev => [...prev, { sender: 'ai', text: aiResponse }]);
      setIsChatTyping(false);
    }, 1000);
  };

  // Run AI analysis simulator
  const handleRunAnalysis = () => {
    if (!selectedFile) return;

    setIsScanning(true);
    setScanProgress([logSteps[0]]);

    let stepIndex = 0;
    const interval = setInterval(() => {
      stepIndex++;
      if (stepIndex < logSteps.length) {
        setScanProgress(prev => [...prev, logSteps[stepIndex]]);
      } else {
        clearInterval(interval);
        setTimeout(() => {
          // Finish scanning, assemble results
          let resultData;
          if (selectedFile.isSample) {
            resultData = SAMPLE_CASES.find(c => c.id === selectedFile.sampleId);
          } else {
            // Generate dummy randomized result with varying confidence based on file name/scan type
            const hash = selectedFile.name.length;
            let confidence = 45 + (hash % 50); // range 45 to 95

            // Set specific thresholds
            let status = 'GREEN';
            let diagnosticText = '';

            if (confidence >= 85) {
              status = 'GREEN';
              diagnosticText = `HIGH CONFIDENCE DIAGNOSIS (${confidence}%). Clear visual indicators demonstrate normal structural architecture. No acute pathologic processes, lesions, fractures, or abnormal calcifications are detected in this ${selectedFile.type} scan. Recommended: Annual routine screening.`;
            } else if (confidence >= 70) {
              status = 'YELLOW';
              diagnosticText = `MODERATE CONFIDENCE FINDING (${confidence}%). Minor sub-clinical asymmetry or structural irregularity is detected in the ${selectedFile.type} tissues. AI cannot definitively rule out minor early-stage inflammatory response or mechanical wear. Clinical correlation and specialist evaluation is recommended.`;
            } else {
              status = 'RED';
              diagnosticText = `RED ALERT: LOW CONFIDENCE AI UNCERTAINTY (${confidence}%). Due to complex visual artifacts or atypical findings on the ${selectedFile.type} document, the AI engine has marked this scan under Honest Uncertainty. To prevent clinical errors, the AI REFUSES to render a diagnosis. Urgent clinical checkup is requested.`;
            }

            resultData = {
              id: 'custom-' + Date.now(),
              name: selectedFile.name,
              type: selectedFile.type,
              size: selectedFile.size,
              confidence: confidence,
              diagnosis: diagnosticText,
              summary: confidence < 70 ? 'AI uncertainty trigger. Direct doctor escalation required.' : `Analyzed ${selectedFile.type} with ${confidence}% confidence.`,
              qa: [
                { q: "Is this result definitive?", a: `No, this is a simulated AI prediction running with a confidence score of ${confidence}%. You must verify all findings with a certified professional.` },
                { q: "Should I schedule an appointment?", a: confidence < 85 ? "Yes. A doctor consultation is recommended because the confidence level is under the green safety threshold." : "Only for routine medical correlation since the confidence score is high." }
              ]
            };
          }

          // Format status badge color
          let finalStatus = 'GREEN';
          if (resultData.confidence < 70) finalStatus = 'RED';
          else if (resultData.confidence < 85) finalStatus = 'YELLOW';

          const newHistoryItem = {
            id: 'h-' + Date.now(),
            name: resultData.name,
            type: resultData.type,
            date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
            confidence: resultData.confidence,
            status: finalStatus,
            summary: resultData.summary
          };

          // Add to history and set active result
          setScanHistory(prev => [newHistoryItem, ...prev]);
          setActiveResult(resultData);
          setVqaChat([
            { sender: 'ai', text: `Visual analysis of ${resultData.name} complete. AI confidence: ${resultData.confidence}%. I am ready to answer any questions about this medical document.` }
          ]);
          setIsScanning(false);
          setCurrentView('results');
        }, 800);
      }
    }, 450);
  };

  // Chat/VQA question handling
  const handleSendVqa = (e) => {
    e.preventDefault();
    if (!vqaQuestion.trim() || !activeResult) return;

    const userMsg = vqaQuestion;
    setVqaChat(prev => [...prev, { sender: 'user', text: userMsg }]);
    setVqaQuestion('');

    setTimeout(() => {
      // Find matches in mock QA
      const matchedQa = activeResult.qa.find(
        item => item.q.toLowerCase().includes(userMsg.toLowerCase()) ||
          userMsg.toLowerCase().includes(item.q.toLowerCase())
      );

      let reply = "";
      if (matchedQa) {
        reply = matchedQa.a;
      } else {
        // Generic fallback answers that reflect the safety traffic light logic
        if (activeResult.confidence < 70) {
          reply = `Emergency Alert: Because the confidence score is very low (${activeResult.confidence}%), I am restricted from giving detailed diagnostic answers. Please click the 'Find Nearest Specialist' button below to book an in-person diagnostic consultation immediately.`;
        } else {
          reply = `Regarding your scan ${activeResult.name}, the visual analysis reports ${activeResult.summary} (Certainty: ${activeResult.confidence}%). If you are experiencing symptoms like chest tightness, pain, or fever, please contact your clinician immediately rather than relying solely on automated VQA metrics.`;
        }
      }

      setVqaChat(prev => [...prev, { sender: 'ai', text: reply }]);
    }, 600);
  };

  // Schedule appointment
  const handleBookAppointment = (doc) => {
    setBookingDoctor(doc);
    setBookingForm({ date: new Date().toISOString().split('T')[0], time: '14:30', notes: '' });
    setBookingSuccess(false);
  };

  const submitBooking = (e) => {
    e.preventDefault();
    setBookingSuccess(true);
    setTimeout(() => {
      setBookingDoctor(null);
      setBookingSuccess(false);
    }, 2000);
  };

  // Get matching doctor based on current diagnosis
  const getEscalatedDoctor = () => {
    if (!activeResult) return MOCK_DOCTORS[0];
    const matched = MOCK_DOCTORS.find(d => d.matchTypes.includes(activeResult.type));
    return matched || MOCK_DOCTORS[3]; // Fallback to general lead
  };

  // Quick switch utility to view an old report
  const viewOldReport = (historyItem) => {
    // Look up in sample cases first
    let matchingCase = SAMPLE_CASES.find(c => c.type === historyItem.type && c.confidence === historyItem.confidence);

    if (!matchingCase) {
      // Mock one up based on history values
      matchingCase = {
        id: historyItem.id || 'history-' + Date.now(),
        name: historyItem.name,
        type: historyItem.type,
        size: '5.2 MB',
        confidence: historyItem.confidence,
        diagnosis: `REPORT SUMMARY: ${historyItem.summary}. This historical scan was recorded on ${historyItem.date}. Confidence profile verified at ${historyItem.confidence}%.`,
        summary: historyItem.summary,
        qa: [
          { q: "Is this report final?", a: "This is a record of your previous AI screening. Regular checkups are recommended." }
        ]
      };
    }

    setActiveResult(matchingCase);
    setVqaChat([
      { sender: 'ai', text: `Loaded previous scan report from ${historyItem.date}. How can I assist you today?` }
    ]);
    setCurrentView('results');
  };

  // Filters doctor list based on search/type
  const filteredDoctors = MOCK_DOCTORS.filter(doc => {
    const matchesSearch = doc.name.toLowerCase().includes(searchDoctorQuery.toLowerCase()) ||
      doc.specialty.toLowerCase().includes(searchDoctorQuery.toLowerCase()) ||
      doc.clinic.toLowerCase().includes(searchDoctorQuery.toLowerCase());
    return matchesSearch;
  });

  // Handle welcome landing view separately for full screen style
  if (currentView === 'welcome') {
    return (
      <div key="welcome-viewport" className="dark-welcome-wrap" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '40px', position: 'relative' }}>
        <div className="bg-grid"></div>
        <div ref={welcomeGlow1Ref} className="welcome-glow-1"></div>
        <div ref={welcomeGlow2Ref} className="welcome-glow-2"></div>
        <div ref={welcomeGlow3Ref} className="welcome-glow-3"></div>

        <div style={{ position: 'absolute', top: '24px', left: '24px', width: '24px', height: '24px', borderTop: '2.5px solid rgba(255,255,255,0.3)', borderLeft: '2.5px solid rgba(255,255,255,0.3)' }}></div>
        <div style={{ position: 'absolute', top: '24px', right: '24px', width: '24px', height: '24px', borderTop: '2.5px solid rgba(255,255,255,0.3)', borderRight: '2.5px solid rgba(255,255,255,0.3)' }}></div>
        <div style={{ position: 'absolute', bottom: '24px', left: '24px', width: '24px', height: '24px', borderBottom: '2.5px solid rgba(255,255,255,0.3)', borderLeft: '2.5px solid rgba(255,255,255,0.3)' }}></div>
        <div style={{ position: 'absolute', bottom: '24px', right: '24px', width: '24px', height: '24px', borderBottom: '2.5px solid rgba(255,255,255,0.3)', borderRight: '2.5px solid rgba(255,255,255,0.3)' }}></div>

        <div style={{ textAlign: 'center', maxWidth: '460px', width: '100%', zIndex: 5 }}>
          {/* Shutter logo inside white circle */}
          <div style={{
            width: '120px',
            height: '120px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 32px auto',
            boxShadow: '0 12px 36px rgba(0,0,0,0.18)',
            position: 'relative'
          }}>
            {/* Corner focus brackets inside circle container */}
            <div style={{
              position: 'absolute',
              top: '-12px',
              left: '-12px',
              right: '-12px',
              bottom: '-12px',
              pointerEvents: 'none'
            }}>
              <div style={{ position: 'absolute', top: 0, left: 0, width: '16px', height: '16px', borderTop: '2.5px solid #ffffff', borderLeft: '2.5px solid #ffffff' }}></div>
              <div style={{ position: 'absolute', top: 0, right: 0, width: '16px', height: '16px', borderTop: '2.5px solid #ffffff', borderRight: '2.5px solid #ffffff' }}></div>
              <div style={{ position: 'absolute', bottom: 0, left: 0, width: '16px', height: '16px', borderBottom: '2.5px solid #ffffff', borderLeft: '2.5px solid #ffffff' }}></div>
              <div style={{ position: 'absolute', bottom: 0, right: 0, width: '16px', height: '16px', borderBottom: '2.5px solid #ffffff', borderRight: '2.5px solid #ffffff' }}></div>
            </div>

            <svg viewBox="0 0 100 100" style={{ width: '70px', height: '70px', color: 'var(--dark-green)' }} xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="38" stroke="currentColor" strokeWidth="3.5" fill="none" />
              <circle cx="50" cy="50" r="16" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.3" />
              <path d="M 50 12 L 78 28 L 63 56 L 43 45 Z" fill="currentColor" opacity="0.85" />
              <path d="M 78 28 L 78 64 L 50 64 L 63 38 Z" fill="currentColor" opacity="0.9" />
              <path d="M 78 64 L 50 80 L 35 52 L 50 58 Z" fill="currentColor" opacity="0.85" />
              <path d="M 50 80 L 22 64 L 37 36 L 50 58 Z" fill="currentColor" opacity="0.95" />
              <path d="M 22 64 L 22 28 L 50 28 L 37 54 Z" fill="currentColor" opacity="0.8" />
              <path d="M 22 28 L 50 12 L 65 38 L 50 32 Z" fill="currentColor" opacity="0.9" />
            </svg>
          </div>

          <h1 style={{
            fontSize: '3.6rem',
            fontWeight: '800',
            color: '#ffffff',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            margin: '0 0 10px 0',
            fontFamily: 'var(--font-sans)',
            lineHeight: '1.1'
          }}>Diagnex</h1>

          <p style={{
            fontSize: '0.9rem',
            fontWeight: '600',
            color: '#d8f3dc',
            textTransform: 'uppercase',
            letterSpacing: '0.25em',
            margin: '0 0 48px 0'
          }}>AI Medical Imaging</p>

          <button
            className="btn"
            style={{
              backgroundColor: '#52b788',
              color: 'var(--dark-green)',
              borderRadius: '30px',
              padding: '16px 48px',
              fontSize: '1.05rem',
              fontWeight: '700',
              width: '100%',
              boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
              marginBottom: '28px',
              border: 'none',
              cursor: 'pointer'
            }}
            onClick={() => { setAuthMode('signup'); setCurrentView('auth'); }}
          >
            Get Started
          </button>

          <div style={{ fontSize: '0.95rem', color: 'rgba(255,255,255,0.75)' }}>
            Already a member?{' '}
            <span
              style={{ color: '#52b788', fontWeight: '700', cursor: 'pointer', textDecoration: 'underline' }}
              onClick={() => { setAuthMode('login'); setCurrentView('auth'); }}
            >
              Log in
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Handle auth view separately for clean centered layout
  if (currentView === 'auth') {
    return (
      <div key="auth-viewport" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '40px', backgroundColor: 'var(--primary-bg)', position: 'relative' }}>
        <div className="bg-grid"></div>

        <div style={{ maxWidth: '440px', width: '100%', zIndex: 5 }}>
          {/* Logo header matching Screen 2 */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginBottom: '20px' }}>
            <div style={{
              width: '44px',
              height: '44px',
              borderRadius: '50%',
              backgroundColor: 'var(--dark-green)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <svg viewBox="0 0 100 100" style={{ width: '26px', height: '26px', color: '#ffffff' }} xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="38" stroke="currentColor" strokeWidth="4" fill="none" />
                <path d="M 50 12 L 78 28 L 63 56 L 43 45 Z" fill="currentColor" />
                <path d="M 78 28 L 78 64 L 50 64 L 63 38 Z" fill="currentColor" />
                <path d="M 78 64 L 50 80 L 35 52 L 50 58 Z" fill="currentColor" />
                <path d="M 50 80 L 22 64 L 37 36 L 50 58 Z" fill="currentColor" />
                <path d="M 22 64 L 22 28 L 50 28 L 37 54 Z" fill="currentColor" />
                <path d="M 22 28 L 50 12 L 65 38 L 50 32 Z" fill="currentColor" />
              </svg>
            </div>
            <h2 style={{
              fontSize: '1.8rem',
              fontWeight: '800',
              color: 'var(--dark-green)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              margin: 0,
              fontFamily: 'var(--font-sans)'
            }}>Diagnex</h2>
          </div>

          <div className="glass-card focus-container" style={{ padding: '24px 28px', boxShadow: 'var(--shadow-lg)', transform: 'none', animation: 'none', transition: 'none' }}>
            <div className="focus-corner top-left"></div>
            <div className="focus-corner top-right"></div>
            <div className="focus-corner bottom-left"></div>
            <div className="focus-corner bottom-right"></div>

            <h3 className="text-center" style={{ fontSize: '1.4rem', marginBottom: '6px' }}>
              {authMode === 'signup' ? 'Start Your Journey' : 'Access Your Portal'}
            </h3>
            <p className="text-center" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              {authMode === 'signup' ? 'Take the first step towards AI health screening' : 'Log back in to view your scan history'}
            </p>

            {/* Google Sign In Option */}
            <button type="button" className="oauth-button" onClick={handleGoogleLogin}>
              <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className="auth-divider">or</div>

            <form onSubmit={handleAuthSubmit}>
              {authMode === 'signup' && (
                <>
                  <div className="form-group" style={{ marginBottom: '14px' }}>
                    <label className="form-label">Full Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Aryan Verma"
                      value={authForm.name}
                      onChange={(e) => setAuthForm({ ...authForm, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: '14px' }}>
                    <label className="form-label">Phone Number</label>
                    <input
                      type="tel"
                      className="form-input"
                      placeholder="e.g. +91 98765 43210"
                      value={authForm.phone}
                      onChange={(e) => setAuthForm({ ...authForm, phone: e.target.value })}
                      required
                    />
                  </div>
                </>
              )}

              <div className="form-group" style={{ marginBottom: '14px' }}>
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="e.g. aryan@gmail.com"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="••••••••"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                  required
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{
                  width: '100%',
                  marginTop: '12px',
                  backgroundColor: 'var(--dark-green)',
                  color: '#ffffff',
                  borderRadius: '12px',
                  padding: '14px',
                  fontWeight: '700'
                }}
              >
                {authMode === 'signup' ? 'CONTINUE' : 'LOG IN'}
              </button>
            </form>

            <div className="text-center" style={{ marginTop: '24px', fontSize: '0.85rem' }}>
              {authMode === 'signup' ? (
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                  Already a member?{' '}
                  <span
                    style={{ color: 'var(--forest-green)', fontWeight: '700', cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={() => setAuthMode('login')}
                  >
                    Log In
                  </span>
                </p>
              ) : (
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
                  New to Diagnex?{' '}
                  <span
                    style={{ color: 'var(--forest-green)', fontWeight: '700', cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={() => setAuthMode('signup')}
                  >
                    Sign Up
                  </span>
                </p>
              )}
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <span
              style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: '600', cursor: 'pointer', textDecoration: 'underline' }}
              onClick={() => setCurrentView('welcome')}
            >
              ← Back to welcome screen
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Logged-in screens render inside the dashboard portal layout
  return (
    <div key="app-viewport" className="app-container">
      <div className="bg-grid"></div>
      <div ref={blob1Ref} className="organic-blob-1"></div>
      <div ref={blob2Ref} className="organic-blob-2"></div>
      <div ref={blob3Ref} className="organic-blob-3"></div>

      {/* Dynamic Floating Telemetry Nodes */}
      {bgNodes.map(node => (
        <div
          key={node.id}
          className="telemetry-node"
          style={{
            position: 'absolute',
            width: `${node.size}px`,
            height: `${node.size}px`,
            borderRadius: '50%',
            backgroundColor: 'var(--forest-green)',
            left: node.left,
            top: node.top,
            opacity: node.opacity,
            pointerEvents: 'none',
            zIndex: 0,
            filter: 'blur(1px)'
          }}
        />
      ))}

      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div>
          {/* Logo Brand Frame */}
          <div className="nav-logo-container">
            <div className="logo-aperture-wrap focus-container">
              <div className="focus-corner top-left"></div>
              <div className="focus-corner top-right"></div>
              <div className="focus-corner bottom-left"></div>
              <div className="focus-corner bottom-right"></div>
              {/* Green Aperture Logo */}
              <svg viewBox="0 0 100 100" className="logo-svg" xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="38" stroke="currentColor" strokeWidth="3" fill="none" />
                <circle cx="50" cy="50" r="16" stroke="currentColor" strokeWidth="1.5" fill="none" opacity="0.3" />
                {/* 6 Overlapping shutter blades */}
                <path d="M 50 12 L 78 28 L 63 56 L 43 45 Z" fill="currentColor" opacity="0.85" />
                <path d="M 78 28 L 78 64 L 50 64 L 63 38 Z" fill="currentColor" opacity="0.9" />
                <path d="M 78 64 L 50 80 L 35 52 L 50 58 Z" fill="currentColor" opacity="0.85" />
                <path d="M 50 80 L 22 64 L 37 36 L 50 58 Z" fill="currentColor" opacity="0.95" />
                <path d="M 22 64 L 22 28 L 50 28 L 37 54 Z" fill="currentColor" opacity="0.8" />
                <path d="M 22 28 L 50 12 L 65 38 L 50 32 Z" fill="currentColor" opacity="0.9" />
              </svg>
            </div>
            <h1 className="nav-logo-text">Diagnex</h1>
            <span className="nav-logo-subtext">AI Radiologist</span>
          </div>

          {/* Navigation Items grouped by categories */}
          <nav className="nav-links">
            <div className="nav-group-label">Clinical Suite</div>
            <div
              className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentView('dashboard')}
            >
              <Activity size={18} />
              <span>Dashboard Portal</span>
            </div>
            <div
              className={`nav-item ${currentView === 'lab' ? 'active' : ''}`}
              onClick={() => setCurrentView('lab')}
            >
              <UploadCloud size={18} />
              <span>Diagnostic Lab</span>
            </div>
            {activeResult && (
              <div
                className={`nav-item ${currentView === 'results' ? 'active' : ''}`}
                onClick={() => setCurrentView('results')}
              >
                <Clipboard size={18} />
                <span>Analysis Result</span>
              </div>
            )}

            <div className="nav-group-label" style={{ marginTop: '16px' }}>Intelligence & AI</div>
            <div
              className={`nav-item ${currentView === 'chat' ? 'active' : ''}`}
              onClick={() => setCurrentView('chat')}
            >
              <MessageSquare size={18} />
              <span>Clinical Chat AI</span>
            </div>
            <div
              className={`nav-item ${currentView === 'analytics' ? 'active' : ''}`}
              onClick={() => setCurrentView('analytics')}
            >
              <BarChart3 size={18} />
              <span>Telemetry Analytics</span>
            </div>

            <div className="nav-group-label" style={{ marginTop: '16px' }}>Escalation</div>
            <div
              className={`nav-item ${currentView === 'map' ? 'active' : ''}`}
              onClick={() => setCurrentView('map')}
            >
              <Map size={18} />
              <span>Specialist Locator</span>
            </div>
          </nav>
        </div>

        {/* User profile section at the bottom */}
        {user ? (
          <div className="user-profile-badge">
            <div className="user-avatar">
              {user.name.charAt(0)}
            </div>
            <div className="user-info">
              <span className="user-name">{user.name}</span>
              <span className="user-role">Patient account</span>
            </div>
            <div style={{ marginLeft: 'auto', cursor: 'pointer', display: 'flex', alignItems: 'center' }} onClick={handleLogout} title="Logout">
              <LogOut size={16} className="text-red" />
            </div>
          </div>
        ) : (
          <div className="text-center" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            v1.4.2 · Secure Connection
          </div>
        )}
      </aside>

      {/* Main Panel Viewport */}
      <main className="main-content">

{/* VIEW 3: HEALTH DASHBOARD */ }
{
  currentView === 'dashboard' && (
    <div>
      <div className="dashboard-header">
        <div>
          <h1 style={{ fontSize: '2rem', margin: '0 0 6px 0' }}>Welcome, {user ? user.name.split(' ')[0] : 'Aryan'}</h1>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>Here is your personal diagnostic telemetry overview.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCurrentView('lab')}>
          <Plus size={16} /> Scan New Image
        </button>
      </div>

      {/* Quick Metrics */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <Activity size={22} />
          </div>
          <div className="stat-info">
            <span className="stat-value">{scanHistory.length}</span>
            <span className="stat-label">Scans Completed</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <CheckCircle2 size={22} className="text-green" />
          </div>
          <div className="stat-info">
            <span className="stat-value">
              {Math.round(scanHistory.reduce((acc, curr) => acc + curr.confidence, 0) / scanHistory.length)}%
            </span>
            <span className="stat-label">Avg. Accuracy</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <ShieldAlert size={22} className="text-yellow" />
          </div>
          <div className="stat-info">
            <span className="stat-value">
              {scanHistory.filter(h => h.status === 'RED' || h.status === 'YELLOW').length}
            </span>
            <span className="stat-label">Doctor Referrals</span>
          </div>
        </div>
      </div>

      {/* Two Column Grid */}
      <div className="dashboard-grid">
        {/* Left Column: Recent Scans */}
        <div className="table-card focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          <div className="list-header">
            <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Recent Diagnostic Scans</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Updated real-time</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className="scans-table">
              <thead>
                <tr>
                  <th>Scan Document</th>
                  <th>Type</th>
                  <th>Date Parsed</th>
                  <th>Confidence</th>
                  <th>Safety badge</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {scanHistory.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="scan-title-cell">
                        <div className="scan-icon-pill">
                          <FileText size={16} />
                        </div>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{item.name}</span>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>{item.type}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>{item.date}</span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{item.confidence}%</span>
                    </td>
                    <td>
                      <span className={`badge-dot ${item.status.toLowerCase()}`}>
                        <span className={`dot-indicator ${item.status.toLowerCase()}`}></span>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-outline-green"
                        style={{ padding: '6px 12px', fontSize: '0.75rem', borderRadius: '6px' }}
                        onClick={() => viewOldReport(item)}
                      >
                        Open Report
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Health Tools & Help */}
        <div className="tools-card focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>Diagnostic Toolkit</h3>

          <div className="tools-list">
            <div className="tool-button" onClick={() => setCurrentView('lab')}>
              <div className="tool-icon-wrap">
                <UploadCloud size={18} />
              </div>
              <div className="tool-info">
                <h4>Launch Diagnostic AI</h4>
                <p>Run CrossGate-VQA classification on new scans.</p>
              </div>
            </div>

            <div className="tool-button" onClick={() => { setSelectedDoctor(null); setCurrentView('map'); }}>
              <div className="tool-icon-wrap">
                <MapPin size={18} className="text-red" />
              </div>
              <div className="tool-info">
                <h4>Find Specialist Map</h4>
                <p>Locate nearby clinics for referral escalation.</p>
              </div>
            </div>

            <div className="tool-button" style={{ cursor: 'default' }}>
              <div className="tool-icon-wrap">
                <Phone size={18} className="text-yellow" />
              </div>
              <div className="tool-info">
                <h4>Medical Hotline</h4>
                <p>Direct telehealth connection: +1 800 DIAGNEX</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

{/* VIEW 4: DIAGNOSTIC LAB (UPLOAD & SELECT) */ }
{
  currentView === 'lab' && (
    <div>
      <div className="dashboard-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '2rem', margin: '0' }}>Scan & Ask</h1>
            <span className="badge-dot green" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
              <span className="dot-indicator green" style={{ animation: 'pulse-glow 1.5s infinite' }}></span>
              AI Ready
            </span>
          </div>
          <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>Upload raw medical data to trigger visual answering analytics.</p>
        </div>
      </div>

      <div className="scanner-grid">
        {/* Left Column: File uploader and scan selection */}
        <div className="glass-card focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>1. Prepare Scan Document</h3>

          {/* Scan type selector */}
          <div className="form-group">
            <label className="form-label">Select Scan Category</label>
            <div className="scan-chips-container">
              {['X-Ray', 'CT Scan', 'MRI', 'Ultrasound', 'Pathology'].map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`scan-chip ${selectedScanType === t ? 'active' : ''}`}
                  onClick={() => { setSelectedScanType(t); if (selectedFile && !selectedFile.isSample) setSelectedFile(prev => ({ ...prev, type: t })) }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Drag and Drop Zone */}
          <div className="form-group">
            <label className="form-label">Upload High-Quality Scan File</label>
            <label className="upload-area">
              <input
                type="file"
                style={{ display: 'none' }}
                accept="image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
              />
              <div className="upload-icon-box">
                <UploadCloud size={28} />
              </div>
              <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem' }}>Drag & Drop file or Browse</h4>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Supports high-resolution PNG, JPG, WebP, PDF, or DOC/DOCX.
              </p>
            </label>
          </div>

          {/* Preset samples trigger */}
          <div className="sample-presets">
            <div className="sample-presets-title">Or click a sample patient scan to test:</div>
            <div className="preset-buttons">
              <button
                type="button"
                className="preset-chip"
                onClick={() => handleLoadSample('sample-chest-normal')}
              >
                Sample 1: Chest X-Ray (Normal)
              </button>
              <button
                type="button"
                className="preset-chip"
                onClick={() => handleLoadSample('sample-chest-pneumonia')}
              >
                Sample 2: Chest X-Ray (Pneumonia)
              </button>
              <button
                type="button"
                className="preset-chip"
                onClick={() => handleLoadSample('sample-brain-gliosis')}
              >
                Sample 3: Brain MRI (Gliosis)
              </button>
              <button
                type="button"
                className="preset-chip"
                onClick={() => handleLoadSample('sample-abd-gallstones')}
              >
                Sample 4: Ultrasound (Gallstones)
              </button>
            </div>
          </div>

          {/* File Preview */}
          {selectedFile && (
            <div className="uploaded-file-card mt-24">
              <div className="file-preview-details">
                <div className="file-preview-icon">
                  <FileText size={20} />
                </div>
                <div className="file-meta">
                  <h4>{selectedFile.name}</h4>
                  <p>{selectedFile.type} · {selectedFile.size}</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-close"
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                onClick={() => setSelectedFile(null)}
              >
                <X size={18} />
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Question input and scan simulator */}
        <div className="glass-card focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          <h3 style={{ fontSize: '1.2rem', marginBottom: '16px' }}>2. AI Engine Pipeline</h3>

          {/* Ask question input */}
          <div className="form-group">
            <label className="form-label">Optional: Ask AI a specific clinical question</label>
            <textarea
              className="form-input"
              placeholder="e.g. Is there any evidence of bacterial pneumonia or pleural effusion in this lung lobe?"
              rows="3"
              style={{ resize: 'none' }}
              value={userQuestion}
              onChange={(e) => setUserQuestion(e.target.value)}
            />
          </div>

          {/* Scan Visualizer Simulation Screen */}
          <div className="scan-visualizer-container mb-24">
            <div className="grid-overlay-matrix"></div>

            {isScanning && (
              <>
                <div className="laser-line"></div>
                <div className="scan-overlay-active"></div>
              </>
            )}

            {/* Dynamic SVG illustration representing anatomical scanning based on category */}
            <svg viewBox="0 0 100 100" className="scan-medical-svg" fill="none" stroke="currentColor">
              {selectedScanType === 'X-Ray' && (
                <g strokeWidth="1" stroke="currentColor" opacity="0.6">
                  {/* Ribcage Outline */}
                  <path d="M50,15 Q50,90 50,90" strokeWidth="2" />
                  <path d="M50,22 Q75,18 78,35 Q70,42 50,42" />
                  <path d="M50,22 Q25,18 22,35 Q30,42 50,42" />
                  <path d="M50,42 Q80,38 82,55 Q70,62 50,62" />
                  <path d="M50,42 Q20,38 18,55 Q30,62 50,62" />
                  <path d="M50,62 Q82,58 84,75 Q70,82 50,82" />
                  <path d="M50,62 Q18,58 16,75 Q30,82 50,82" />
                  <path d="M42,12 Q50,8 58,12" strokeWidth="2" />
                </g>
              )}
              {selectedScanType === 'MRI' && (
                <g strokeWidth="1" stroke="currentColor" opacity="0.6">
                  {/* Brain sagittal outline */}
                  <path d="M50,10 C75,10 85,30 85,50 C85,75 70,85 50,85 C30,85 15,75 15,50 C15,30 25,10 50,10 Z" strokeWidth="2" />
                  <path d="M50,25 C65,25 72,35 72,50 C72,65 60,73 50,73 C40,73 28,65 28,50 C28,35 35,25 50,25" />
                  <path d="M50,10 Q50,85 50,85" strokeWidth="1.5" strokeDasharray="3,3" />
                  <path d="M15,50 Q85,50 85,50" strokeWidth="1.5" strokeDasharray="3,3" />
                </g>
              )}
              {selectedScanType === 'Ultrasound' && (
                <g strokeWidth="1" stroke="currentColor" opacity="0.6">
                  {/* Fan radar sweep */}
                  <path d="M50,10 L85,85 A50,50 0 0,1 15,85 Z" strokeWidth="2" />
                  <path d="M50,10 L68,88" strokeDasharray="2,2" />
                  <path d="M50,10 L32,88" strokeDasharray="2,2" />
                  <circle cx="50" cy="55" r="8" strokeWidth="1.5" />
                  <circle cx="52" cy="58" r="3" fill="currentColor" />
                  <circle cx="48" cy="54" r="2" fill="currentColor" />
                </g>
              )}
              {(selectedScanType === 'CT Scan' || selectedScanType === 'Pathology') && (
                <g strokeWidth="1" stroke="currentColor" opacity="0.6">
                  {/* Circular matrix CT scan or tissue layout */}
                  <circle cx="50" cy="50" r="38" strokeWidth="2" />
                  <circle cx="50" cy="50" r="28" strokeDasharray="4,4" />
                  <path d="M25,25 L75,75" strokeDasharray="2,2" />
                  <path d="M75,25 L25,75" strokeDasharray="2,2" />
                  <rect x="42" y="42" width="16" height="16" strokeWidth="1.5" />
                </g>
              )}
            </svg>

            {/* Log console overlay during scanning */}
            {isScanning && (
              <div className="scan-progress-logs">
                {scanProgress.map((line, idx) => (
                  <p key={idx} className="log-line">&gt; {line}</p>
                ))}
                <div ref={logEndRef}></div>
              </div>
            )}

            {!isScanning && !selectedFile && (
              <span style={{ position: 'absolute', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                No Scan Selected
              </span>
            )}
            {!isScanning && selectedFile && (
              <span className="text-green" style={{ position: 'absolute', fontSize: '0.8rem', fontWeight: 600 }}>
                Scan Loaded · Click Run AI Analysis below
              </span>
            )}
          </div>

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={!selectedFile || isScanning}
            onClick={handleRunAnalysis}
          >
            {isScanning ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Processing Neural Network...
              </>
            ) : (
              <>
                <Play size={16} /> Run Diagnostic AI Analysis
              </>
            )}
          </button>
          <div className="text-center mt-24" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            CrossGate-VQA Engine · 206.7M parameter weight · HIPAA Compliant Telemetry
          </div>
        </div>
      </div>
    </div>
  )
}

{/* VIEW 5: ANALYSIS RESULTS SCREEN */ }
{
  currentView === 'results' && activeResult && (
    <div>
      <div className="dashboard-header" style={{ marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', margin: '0' }}>Analysis Result</h1>
          <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>CrossGate-VQA Visual Telemetry Evaluation</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setCurrentView('lab')}>
            Upload Another
          </button>
          <button className="btn btn-primary" onClick={() => setCurrentView('dashboard')}>
            Back to Dashboard
          </button>
        </div>
      </div>

      {/* Main Result Interface */}
      <div className="analysis-main-grid">

        {/* Left Column: Image/Scan view and VQA chat */}
        <div>
          <div className="image-analysis-card focus-container mb-24">
            <div className="focus-corner top-left"></div>
            <div className="focus-corner top-right"></div>
            <div className="focus-corner bottom-left"></div>
            <div className="focus-corner bottom-right"></div>
            <div className="grid-overlay-matrix"></div>

            {/* Glowing focus rectangle framing the medical file */}
            <div style={{ border: '1px solid rgba(82, 183, 136, 0.4)', borderRadius: '12px', padding: '16px', position: 'relative', width: '85%', height: '85%', display: 'flex', alignItems: 'center', justifySelf: 'center', justifyContent: 'center' }}>
              <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', color: 'var(--mint)' }} fill="none" stroke="currentColor">
                {activeResult.type === 'X-Ray' && (
                  <g strokeWidth="1" stroke="currentColor">
                    <path d="M50,15 Q50,90 50,90" strokeWidth="2.5" />
                    <path d="M50,22 Q75,18 78,35 Q70,42 50,42" />
                    <path d="M50,22 Q25,18 22,35 Q30,42 50,42" />
                    <path d="M50,42 Q80,38 82,55 Q70,62 50,62" />
                    <path d="M50,42 Q20,38 18,55 Q30,62 50,62" />
                    <path d="M50,62 Q82,58 84,75 Q70,82 50,82" />
                    <path d="M50,62 Q18,58 16,75 Q30,82 50,82" />
                    {/* If pneumonia is present, render a cloudy red circle highlighting the disease */}
                    {activeResult.id.includes('pneumonia') && (
                      <g>
                        <circle cx="68" cy="65" r="12" fill="var(--color-yellow)" opacity="0.25" stroke="var(--color-yellow)" strokeDasharray="2,2" />
                        <path d="M68,53 L78,65" stroke="var(--color-red)" strokeWidth="1" />
                        <text x="68" y="50" fill="var(--color-red)" fontSize="5" fontWeight="bold" textAnchor="middle">ANOMALY ZONE</text>
                      </g>
                    )}
                  </g>
                )}
                {activeResult.type === 'MRI' && (
                  <g strokeWidth="1" stroke="currentColor">
                    <path d="M50,10 C75,10 85,30 85,50 C85,75 70,85 50,85 C30,85 15,75 15,50 C15,30 25,10 50,10 Z" strokeWidth="2.5" />
                    <path d="M50,25 C65,25 72,35 72,50 C72,65 60,73 50,73 C40,73 28,65 28,50 C28,35 35,25 50,25" />
                    {/* Brain ventricles */}
                    <path d="M42,48 Q50,40 58,48 Q50,55 42,48" strokeWidth="1.5" />
                    {/* If gliosis is selected, render a small yellow anomaly circle */}
                    {activeResult.id.includes('gliosis') && (
                      <g>
                        <circle cx="36" cy="38" r="8" fill="var(--color-yellow)" opacity="0.3" stroke="var(--color-yellow)" strokeDasharray="1.5,1.5" />
                        <text x="36" y="27" fill="var(--color-yellow)" fontSize="5" fontWeight="bold" textAnchor="middle">GLIOSIS ZONE</text>
                      </g>
                    )}
                  </g>
                )}
                {activeResult.type === 'Ultrasound' && (
                  <g strokeWidth="1" stroke="currentColor">
                    <path d="M50,10 L85,85 A50,50 0 0,1 15,85 Z" strokeWidth="2.5" fill="rgba(82, 183, 136, 0.02)" />
                    <path d="M50,10 L68,88" strokeDasharray="2,2" opacity="0.4" />
                    <path d="M50,10 L32,88" strokeDasharray="2,2" opacity="0.4" />
                    <circle cx="50" cy="55" r="8" strokeWidth="1.5" />
                    {/* Gallstones visual */}
                    {activeResult.id.includes('gallstones') && (
                      <g>
                        <circle cx="52" cy="58" r="2.5" fill="var(--color-red)" />
                        <circle cx="47" cy="54" r="2" fill="var(--color-red)" />
                        {/* Acoustic Shadowing */}
                        <path d="M52,60.5 L55,85" stroke="var(--color-red)" strokeWidth="1" strokeDasharray="1,2" />
                        <path d="M47,56 L44,82" stroke="var(--color-red)" strokeWidth="1" strokeDasharray="1,2" />
                        <text x="50" y="42" fill="var(--color-red)" fontSize="4.5" fontWeight="bold" textAnchor="middle">CHOLELITHIASIS ALERT</text>
                      </g>
                    )}
                  </g>
                )}
                {activeResult.type === 'CT Scan' && (
                  <g strokeWidth="1" stroke="currentColor">
                    <circle cx="50" cy="50" r="38" strokeWidth="2" />
                    <circle cx="50" cy="50" r="28" strokeDasharray="4,4" />
                    <rect x="42" y="42" width="16" height="16" strokeWidth="1.5" />
                  </g>
                )}
              </svg>

              <div style={{ position: 'absolute', bottom: '12px', left: '12px', background: 'rgba(0,0,0,0.8)', padding: '4px 10px', borderRadius: '6px', fontSize: '0.7rem', border: '1px solid var(--panel-border)' }}>
                {activeResult.name} · {activeResult.type}
              </div>
            </div>
          </div>

          {/* VQA Interactive Panel */}
          <div className="vqa-container">
            <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={16} className="text-green" /> Interactive Clinical VQA
            </h4>

            <div className="vqa-chat-history">
              {vqaChat.map((msg, idx) => (
                <div key={idx} className={`vqa-message ${msg.sender}`}>
                  {msg.text}
                </div>
              ))}
            </div>

            <form onSubmit={handleSendVqa} className="vqa-input-box">
              <input
                type="text"
                placeholder="Ask the AI radiologist about this scan..."
                value={vqaQuestion}
                onChange={(e) => setVqaQuestion(e.target.value)}
              />
              <button type="submit" className="vqa-send-btn">
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Safety Traffic Light and diagnosis details */}
        <div className="glass-card focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          <h3 style={{ fontSize: '1.25rem', marginBottom: '20px' }}>Diagnostic Analytics</h3>

          {/* Safety Traffic Lights badge card grid */}
          <div className="traffic-light-container">
            {/* GREEN DOT */}
            <div className={`traffic-badge-card green ${activeResult.confidence >= 85 ? 'active' : ''}`}>
              <div className={`traffic-dot-circle green ${activeResult.confidence >= 85 ? 'green' : ''}`}></div>
              <span className="traffic-badge-title">GREEN Dot</span>
              <p className="traffic-badge-desc">Sure (&gt;85% confidence score)</p>
            </div>

            {/* YELLOW DOT */}
            <div className={`traffic-badge-card yellow ${activeResult.confidence >= 70 && activeResult.confidence < 85 ? 'active' : ''}`}>
              <div className={`traffic-dot-circle yellow ${activeResult.confidence >= 70 && activeResult.confidence < 85 ? 'yellow' : ''}`}></div>
              <span className="traffic-badge-title">YELLOW Dot</span>
              <p className="traffic-badge-desc">Verify (70% - 85% confidence score)</p>
            </div>

            {/* RED DOT */}
            <div className={`traffic-badge-card red ${activeResult.confidence < 70 ? 'active' : ''}`}>
              <div className={`traffic-dot-circle red ${activeResult.confidence < 70 ? 'red' : ''}`}></div>
              <span className="traffic-badge-title">RED Dot</span>
              <p className="traffic-badge-desc">ALERT (&lt;70% confidence score)</p>
            </div>
          </div>

          {/* AI diagnosis text details box */}
          <div className="diagnosis-box">
            <h4>
              <FileText size={18} className="text-green" /> Complete Diagnostic telemetry
            </h4>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {activeResult.diagnosis}
            </p>

            <div className="confidence-metric-wrap">
              <div className="confidence-header">
                <span>AI Model Certainty Estimation</span>
                <span style={{ fontWeight: 700 }}>{activeResult.confidence}%</span>
              </div>
              <div className="confidence-bar-outer">
                <div
                  className={`confidence-bar-inner ${activeResult.confidence >= 85 ? 'green' : activeResult.confidence >= 70 ? 'yellow' : 'red'}`}
                  style={{ width: `${activeResult.confidence}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Honest Uncertainty Disclaimer */}
          {activeResult.confidence < 70 && (
            <div className="glass-card mb-24" style={{ border: '1px solid rgba(239, 68, 68, 0.3)', backgroundColor: 'rgba(239, 68, 68, 0.05)', padding: '16px' }}>
              <h4 style={{ margin: '0 0 6px 0', color: 'var(--color-red)', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
                <ShieldAlert size={16} /> Safety Lock: Honest Uncertainty
              </h4>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                The AI model has abstained from confirming diagnosis bounds due to high variance index. To maintain safety regulations, direct physician inspection is required.
              </p>
            </div>
          )}

          {/* Doctor Escalation Panel */}
          <div className="doctor-escalation-alert-panel">
            <div className="escalation-text">
              <h4>
                <AlertTriangle size={18} className={activeResult.confidence < 85 ? 'text-red' : 'text-green'} />
                {activeResult.confidence < 85 ? 'Physician Escalation Recommended' : 'Routine Consult Suggested'}
              </h4>
              <p>
                {activeResult.confidence < 85
                  ? `AI confidence score is below green threshold. Connect with ${getEscalatedDoctor().name.split(',')[0]} immediately.`
                  : 'Your diagnostic scan is marked clean. You can verify with a practitioner for safety.'}
              </p>
            </div>
            <button
              className={`btn ${activeResult.confidence < 85 ? 'btn-danger' : 'btn-outline-green'}`}
              onClick={() => { setSelectedDoctor(getEscalatedDoctor()); setCurrentView('map'); }}
            >
              Find Nearest Radiologist
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

{/* VIEW 6: DOCTOR FINDER / GOOGLE MAP ESCALATION */ }
{
  currentView === 'map' && (
    <div>
      <div className="dashboard-header" style={{ marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', margin: '0' }}>Doctor Escalation Directory</h1>
          <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>Google Maps routing for low confidence warning triggers.</p>
        </div>
        <button className="btn btn-secondary" onClick={() => setCurrentView('dashboard')}>
          Back to Dashboard
        </button>
      </div>

      {/* Maps search and layout split */}
      <div className="maps-view-grid">

        {/* Left Column: Interactive Google Map */}
        <div className="mock-map-container focus-container">
          <div className="focus-corner top-left"></div>
          <div className="focus-corner top-right"></div>
          <div className="focus-corner bottom-left"></div>
          <div className="focus-corner bottom-right"></div>

          {/* Search overlay inside map */}
          <div className="map-search-bar" style={{ zIndex: 10 }}>
            <Search size={16} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search doctor or clinic..."
              value={searchDoctorQuery}
              onChange={(e) => {
                setSearchDoctorQuery(e.target.value);
                setSelectedDoctor(null);
              }}
            />
          </div>

          {/* Map Control filter options */}
          <div className="map-ui-controls" style={{ zIndex: 10 }}>
            <button className="map-control-btn" onClick={() => setMapFilterDistance(mapFilterDistance === '1km' ? 'all' : '1km')}>
              <Navigation size={14} /> {mapFilterDistance === '1km' ? 'Show All' : 'Within 2 km'}
            </button>
          </div>

          <iframe
            title="Google Maps Doctor Escalation"
            width="100%"
            height="100%"
            style={{ border: 0, borderRadius: '20px', display: 'block', zIndex: 1 }}
            src={`https://maps.google.com/maps?q=${encodeURIComponent(
              selectedDoctor 
                ? `${selectedDoctor.clinic}, ${selectedDoctor.address}` 
                : (searchDoctorQuery ? `${searchDoctorQuery} radiologist` : 'radiologist clinic near me')
            )}&t=&z=14&ie=UTF8&iwloc=&output=embed`}
            allowFullScreen
          ></iframe>
        </div>

        {/* Right Column: Doctors directory listing */}
        <div className="doctor-cards-list">
          {selectedDoctor && (
            <div className="glass-card" style={{ border: '1.5px solid var(--mint)', backgroundColor: 'rgba(82, 183, 136, 0.08)', marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span className="badge-dot green" style={{ fontSize: '0.65rem' }}>Selected Match</span>
                <button className="btn-close" style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }} onClick={() => setSelectedDoctor(null)}>
                  <X size={16} />
                </button>
              </div>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '1.1rem' }}>{selectedDoctor.name}</h4>
              <span className="doctor-specialty">{selectedDoctor.specialty}</span>
              <p style={{ fontSize: '0.8rem', margin: '8px 0 12px 0', color: 'var(--text-secondary)' }}>
                📍 {selectedDoctor.address}<br />
                🏥 {selectedDoctor.clinic}
              </p>
              <div className="doctor-actions-row">
                <button className="btn btn-primary" style={{ flexGrow: 1, padding: '8px 16px', fontSize: '0.8rem' }} onClick={() => handleBookAppointment(selectedDoctor)}>
                  Book Appointment
                </button>
                <a href={`tel:${selectedDoctor.phone}`} className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '0.8rem' }}>
                  <Phone size={14} />
                </a>
              </div>
            </div>
          )}

          <h3 style={{ fontSize: '1.1rem', margin: '0 0 12px 0' }}>Available Specialists nearby</h3>
          {filteredDoctors.map(doc => (
            <div
              key={doc.id}
              className={`doctor-item-card ${selectedDoctor?.id === doc.id ? 'selected' : ''}`}
              onClick={() => setSelectedDoctor(doc)}
            >
              <div className="doctor-header-row">
                <div className="doctor-meta-info">
                  <h4>{doc.name}</h4>
                  <span className="doctor-specialty">{doc.specialty}</span>
                </div>
                <span className="doctor-distance-tag">{doc.distance}</span>
              </div>

              <div className="doctor-stats-line">
                <div className="doctor-stat-item">
                  <span>⭐ {doc.rating}</span>
                  <span style={{ opacity: 0.6 }}>({doc.reviews} reviews)</span>
                </div>
                <div className="doctor-stat-item">
                  <Clock size={12} />
                  <span>{doc.availability}</span>
                </div>
              </div>

              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)', opacity: 0.8 }}>
                🏥 {doc.clinic}
              </p>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}

      {/* VIEW 7: CLINICAL CHAT AI */}
      {currentView === 'chat' && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div className="dashboard-header" style={{ marginBottom: '20px' }}>
            <div>
              <h1 style={{ fontSize: '2rem', margin: '0' }}>Clinical Chat Assistant</h1>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>Interact with Diagnex AI about imaging preparation, workflows, and patient protocols.</p>
            </div>
          </div>

          <div className="chat-container">
            <div className="chat-history">
              {chatHistory.map((msg, index) => (
                <div key={index} className={`chat-message ${msg.sender}`}>
                  {msg.sender === 'ai' ? (
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {msg.text.split('\n').map((line, lIdx) => {
                        if (line.startsWith('•') || line.startsWith('-')) {
                          return <li key={lIdx} style={{ marginLeft: '12px', listStyleType: 'disc' }}>{line.replace(/^[•-]\s*/, '')}</li>;
                        }
                        if (line.match(/^\d+\./)) {
                          return <li key={lIdx} style={{ marginLeft: '12px', listStyleType: 'decimal' }}>{line.replace(/^\d+\.\s*/, '')}</li>;
                        }
                        if (line.startsWith('**') && line.endsWith('**')) {
                          return <strong key={lIdx} style={{ display: 'block', margin: '6px 0', fontSize: '0.95rem' }}>{line.replace(/\*\*/g, '')}</strong>;
                        }
                        return <p key={lIdx} style={{ margin: '4px 0' }}>{line}</p>;
                      })}
                    </div>
                  ) : (
                    msg.text
                  )}
                </div>
              ))}
              {isChatTyping && (
                <div className="chat-message ai" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Clinical assistant is thinking...</span>
                </div>
              )}
            </div>

            <div className="chat-chips-container">
              <button className="chat-chip" onClick={() => handleChatSubmit(null, "What are MRI preparation rules?")}>
                🧲 MRI Preparation
              </button>
              <button className="chat-chip" onClick={() => handleChatSubmit(null, "How do I prepare for an abdominal ultrasound?")}>
                🤰 Abdomen Ultrasound
              </button>
              <button className="chat-chip" onClick={() => handleChatSubmit(null, "What should I know about X-Ray radiation safety?")}>
                ☢️ X-Ray Safety
              </button>
              <button className="chat-chip" onClick={() => handleChatSubmit(null, "Do I need to fast for contrast dye?")}>
                💉 Contrast Protocols
              </button>
            </div>

            <form onSubmit={handleChatSubmit} className="chat-input-bar">
              <input
                type="text"
                placeholder="Ask something (e.g. Can I wear jewelry during MRI?)..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
              />
              <button type="submit" className="btn btn-primary" style={{ padding: '12px 24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Send size={16} />
                <span>Send</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* VIEW 8: TELEMETRY ANALYTICS */}
      {currentView === 'analytics' && (
        <div>
          <div className="dashboard-header" style={{ marginBottom: '24px' }}>
            <div>
              <h1 style={{ fontSize: '2rem', margin: '0' }}>Telemetry & Health Analytics</h1>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.9rem' }}>Real-time logs, AI performance indices, and imaging distribution telemetry.</p>
            </div>
            <button className="btn btn-secondary" onClick={() => setCurrentView('dashboard')}>
              Back to Dashboard
            </button>
          </div>

          <div className="analytics-grid">
            <div className="chart-card">
              <h3 style={{ fontSize: '1.1rem', margin: '0 0 8px 0' }}>AI Diagnostics Accuracy Index</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 20px 0' }}>Historical validation against standard radiologist verification benchmarks.</p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600', marginBottom: '4px' }}>
                    <span>Chest X-Ray Segmentation</span>
                    <span className="text-green">94%</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '8px', background: 'var(--panel-border)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '94%', height: '100%', backgroundColor: 'var(--forest-green)', borderRadius: '4px' }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600', marginBottom: '4px' }}>
                    <span>Brain & Spine MRI Classifier</span>
                    <span className="text-yellow" style={{ color: 'var(--color-yellow)' }}>76%</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '8px', background: 'var(--panel-border)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '76%', height: '100%', backgroundColor: 'var(--color-yellow)', borderRadius: '4px' }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: '600', marginBottom: '4px' }}>
                    <span>Thyroid Ultrasound nodule locator</span>
                    <span className="text-red">58%</span>
                  </div>
                  <div className="progress-bar-container" style={{ height: '8px', background: 'var(--panel-border)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: '58%', height: '100%', backgroundColor: 'var(--color-red)', borderRadius: '4px' }}></div>
                  </div>
                </div>

                <div style={{ marginTop: '12px', padding: '16px', background: 'var(--light-mint)', borderRadius: '12px', border: '1px solid rgba(82, 183, 136, 0.15)' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <Activity size={18} style={{ color: 'var(--forest-green)' }} />
                    <div>
                      <h4 style={{ margin: 0, fontSize: '0.85rem', color: 'var(--forest-green)' }}>Weighted Average: 88.4% Confidence</h4>
                      <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Automatically routes cases under 60% confidence directly to Doctor Escalation Finder.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="chart-card">
              <h3 style={{ fontSize: '1.1rem', margin: '0 0 8px 0' }}>Imaging Modality Distribution</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 20px 0' }}>Number of diagnostic documents successfully indexed by type (Monthly).</p>
              
              <div className="chart-row">
                <div className="chart-bar-column">
                  <div className="chart-bar-fill" style={{ height: '140px' }} data-value="14"></div>
                  <span className="chart-bar-label">X-Ray</span>
                </div>
                <div className="chart-bar-column">
                  <div className="chart-bar-fill" style={{ height: '80px' }} data-value="8"></div>
                  <span className="chart-bar-label">MRI</span>
                </div>
                <div className="chart-bar-column">
                  <div className="chart-bar-fill" style={{ height: '60px' }} data-value="6"></div>
                  <span className="chart-bar-label">Ultrasound</span>
                </div>
                <div className="chart-bar-column">
                  <div className="chart-bar-fill" style={{ height: '120px' }} data-value="12"></div>
                  <span className="chart-bar-label">CT Scan</span>
                </div>
                <div className="chart-bar-column">
                  <div className="chart-bar-fill" style={{ height: '40px' }} data-value="4"></div>
                  <span className="chart-bar-label">Pathology</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      </main>

  {/* Appointment booking Modal popup */ }
{
  bookingDoctor && (
    <div className="modal-overlay">
      <div className="modal-content-card focus-container">
        <div className="focus-corner top-left"></div>
        <div className="focus-corner top-right"></div>
        <div className="focus-corner bottom-left"></div>
        <div className="focus-corner bottom-right"></div>

        <button className="modal-close-btn" onClick={() => setBookingDoctor(null)}>
          <X size={20} />
        </button>

        {bookingSuccess ? (
          <div className="text-center" style={{ padding: '24px 0' }}>
            <CheckCircle2 size={48} className="text-green" style={{ margin: '0 auto 16px auto', display: 'block' }} />
            <h3 style={{ fontSize: '1.4rem', color: 'white' }}>Appointment Requested</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Your request has been routed to <strong>{bookingDoctor.name.split(',')[0]}</strong>. Check your phone number <strong>{user?.phone}</strong> for confirmation SMS shortly.
            </p>
          </div>
        ) : (
          <form onSubmit={submitBooking}>
            <h3 style={{ fontSize: '1.3rem', marginBottom: '6px' }}>Request Consultation</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Scheduling with <strong>{bookingDoctor.name}</strong> for clinical scan review.
            </p>

            <div className="form-group">
              <label className="form-label">Preferred Date</label>
              <input
                type="date"
                className="form-input"
                value={bookingForm.date}
                onChange={(e) => setBookingForm({ ...bookingForm, date: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Preferred Time Slot</label>
              <input
                type="time"
                className="form-input"
                value={bookingForm.time}
                onChange={(e) => setBookingForm({ ...bookingForm, time: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Symptoms / Notes (Optional)</label>
              <textarea
                className="form-input"
                placeholder="Describe any symptoms or details regarding this scan..."
                rows="3"
                value={bookingForm.notes}
                onChange={(e) => setBookingForm({ ...bookingForm, notes: e.target.value })}
              />
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button type="button" className="btn btn-secondary" style={{ flexGrow: 1 }} onClick={() => setBookingDoctor(null)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" style={{ flexGrow: 2 }}>
                Request Booking
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  )
}
    </div >
  )
}

export default App
