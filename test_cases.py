"""
test_cases.py - Clinical Benchmark Library
"""

CLINICAL_BENCHMARK_CASES = [
    {
        "id": "BENCH-CASE-01",
        "title": "Severe Trauma / Unresponsive (Level 1 - Resuscitation)",
        "category": "Emergency Resuscitation & Trauma OT",
        "description": "Pedestrian struck by car with traumatic brain injury and active torso bleeding, unresponsive on arrival via 119 Ambulance.",
        "patient_age": 48,
        "patient_gender": "Male",
        "arrival_mode": 2, # 119 Ambulance
        "injury": 1, # Injury
        "chief_complaint": "Major polytrauma, massive hemorrhage, unresponsive",
        "mental": 4, # Unresponsive
        "pain": 0,
        "nrs_pain": 0,
        "sbp": 68,
        "dbp": 40,
        "hr": 146,
        "rr": 34,
        "bt": 35.8,
        "saturation": 82.0,
        "expected_level": 1,
        "expected_disposition": "Emergency Trauma OT / ICU",
        "rationale": "Level 1: Unresponsive (AVPU 4), refractory hemorrhagic shock (SBP 68), critical hypoxia (SpO2 82%)."
    },
    {
        "id": "BENCH-CASE-02",
        "title": "Acute Myocardial Infarction / STEMI (Level 2 - Emergent)",
        "category": "Cardiac Emergency & HDU",
        "description": "64-year-old female with crushing retrosternal chest pain radiating to left jaw, diaphoresis x 1 hour via Private Ambulance.",
        "patient_age": 64,
        "patient_gender": "Female",
        "arrival_mode": 3, # Private Ambulance
        "injury": 2, # Medical
        "chief_complaint": "Crushing retrosternal chest pain radiating to jaw and diaphoresis",
        "mental": 1, # Alert
        "pain": 1,
        "nrs_pain": 9,
        "sbp": 164,
        "dbp": 98,
        "hr": 112,
        "rr": 24,
        "bt": 36.6,
        "saturation": 94.0,
        "expected_level": 2,
        "expected_disposition": "Cardiac Telemetry / HDU / Cath Lab",
        "rationale": "Level 2: High-risk ACS presentation with severe intractable ischemic pain (NRS 9/10)."
    },
    {
        "id": "BENCH-CASE-03",
        "title": "Severe Septic Shock in Elderly (Level 1/2 - Adult ICU)",
        "category": "Critical Care & Adult ICU",
        "description": "78-year-old male with severe lethargy, altered sensorium, high fever, and hypotension via 119 Ambulance.",
        "patient_age": 78,
        "patient_gender": "Male",
        "arrival_mode": 2, # 119 Ambulance
        "injury": 2, # Medical
        "chief_complaint": "Altered sensorium, high fever, shivering, unable to stand",
        "mental": 2, # Verbal only
        "pain": 0,
        "nrs_pain": 2,
        "sbp": 82,
        "dbp": 50,
        "hr": 138,
        "rr": 28,
        "bt": 39.4,
        "saturation": 88.0,
        "expected_level": 1,
        "expected_disposition": "Adult Intensive Care Unit (ICU)",
        "rationale": "Level 1/2: Septic shock with qSOFA 3/3, altered mental status (AVPU Verbal), SBP 82, SpO2 88%."
    },
    {
        "id": "BENCH-CASE-04",
        "title": "Acute Uremia / Missed Dialysis (Level 2 - Dialysis Unit)",
        "category": "Nephrology & Dialysis",
        "description": "56-year-old female with ESRD, missed dialysis x 4 days, dyspnea, and K+ 7.4.",
        "patient_age": 56,
        "patient_gender": "Female",
        "arrival_mode": 1, # Walk-in
        "injury": 2, # Medical
        "chief_complaint": "Missed hemodialysis x 4 days, extreme fatigue, uremia, hyperkalemia",
        "mental": 1, # Alert
        "pain": 0,
        "nrs_pain": 3,
        "sbp": 178,
        "dbp": 102,
        "hr": 104,
        "rr": 22,
        "bt": 36.7,
        "saturation": 93.0,
        "expected_level": 2,
        "expected_disposition": "Hemodialysis & Nephrology Unit",
        "rationale": "Level 2: Life-threatening hyperkalemia risk requiring emergency dialysis."
    },
    {
        "id": "BENCH-CASE-05",
        "title": "Closed Humerus Neck Fracture (Level 4 / General Ward)",
        "category": "Orthopedics & Inpatient Ward",
        "description": "68-year-old female with closed fracture of surgical neck of humerus after slip and fall at home.",
        "patient_age": 68,
        "patient_gender": "Female",
        "arrival_mode": 4, # Private Vehicle
        "injury": 1, # Injury
        "chief_complaint": "Left shoulder and arm pain after slip and fall",
        "mental": 1, # Alert
        "pain": 1,
        "nrs_pain": 6,
        "sbp": 130,
        "dbp": 80,
        "hr": 84,
        "rr": 18,
        "bt": 36.6,
        "saturation": 98.0,
        "expected_level": 4,
        "expected_disposition": "General Inpatient Ward / Ortho",
        "rationale": "Level 4: Stable hemodynamics with localized extremity trauma requiring radiographic reduction."
    },
    {
        "id": "BENCH-CASE-06",
        "title": "Superficial Forearm Burn (Level 5 - Fast-Track Outpatient)",
        "category": "Minor Injury & Outpatient",
        "description": "32-year-old male with small 1st-degree superficial cooking burn on right forearm.",
        "patient_age": 32,
        "patient_gender": "Male",
        "arrival_mode": 1, # Walk-in
        "injury": 1, # Injury
        "chief_complaint": "Superficial 1st degree burn on right forearm from hot oil",
        "mental": 1, # Alert
        "pain": 1,
        "nrs_pain": 3,
        "sbp": 122,
        "dbp": 78,
        "hr": 72,
        "rr": 14,
        "bt": 36.5,
        "saturation": 99.0,
        "expected_level": 5,
        "expected_disposition": "Outpatient Fast-Track / Discharge",
        "rationale": "Level 5: Minor superficial localized burn with normal vitals and minimal pain."
    },
    {
        "id": "BENCH-CASE-07",
        "title": "Corneal Abrasion / Foreign Body (Level 4 - Fast-Track)",
        "category": "Ophthalmology & Fast-Track",
        "description": "45-year-old male with right eye pain and foreign body sensation after dust blew into eye.",
        "patient_age": 45,
        "patient_gender": "Male",
        "arrival_mode": 1, # Walk-in
        "injury": 1, # Injury
        "chief_complaint": "Right ocular pain and photophobia after dust exposure",
        "mental": 1, # Alert
        "pain": 1,
        "nrs_pain": 5,
        "sbp": 128,
        "dbp": 82,
        "hr": 76,
        "rr": 16,
        "bt": 36.6,
        "saturation": 99.0,
        "expected_level": 4,
        "expected_disposition": "Outpatient Fast-Track Clinic",
        "rationale": "Level 4: Localized corneal foreign body requiring fluorescein exam and topical ointment."
    },
    {
        "id": "BENCH-CASE-08",
        "title": "Newborn Severe Respiratory Distress (Level 1 - NICU)",
        "category": "Neonatology & NICU",
        "description": "18-day-old male infant with severe grunting, subcostal retractions, and central cyanosis.",
        "patient_age": 0.05,
        "patient_gender": "Male",
        "arrival_mode": 2, # 119 Ambulance
        "injury": 2, # Medical
        "chief_complaint": "18-day newborn with grunting, apnea, severe chest indrawing",
        "mental": 3, # Pain only
        "pain": 0,
        "nrs_pain": 2,
        "sbp": 68,
        "dbp": 38,
        "hr": 182,
        "rr": 64,
        "bt": 39.2,
        "saturation": 86.0,
        "expected_level": 1,
        "expected_disposition": "Neonatal ICU (NICU)",
        "rationale": "Level 1: Severe neonatal respiratory failure requiring radiant incubator and micro-ventilator."
    }
]

def run_all_benchmarks(triage_engine_inst):
    """Evaluates all benchmark cases and produces safety metrics."""
    total = len(CLINICAL_BENCHMARK_CASES)
    exact_matches = 0
    safe_escalations = 0
    under_triage = 0
    
    for case in CLINICAL_BENCHMARK_CASES:
        res = triage_engine_inst.evaluate_triage(case)
        pred = res['final_level']
        exp = case['expected_level']
        
        if pred == exp:
            exact_matches += 1
        elif pred < exp: # Over-triage (Safer)
            safe_escalations += 1
        else: # Under-triage (Dangerous)
            under_triage += 1
            
    safety_rate = round(((total - under_triage) / total) * 100.0, 1)
    
    return {
        'total_cases': total,
        'exact_concordance': exact_matches,
        'safe_escalations': safe_escalations,
        'under_triage_errors': under_triage,
        'clinical_safety_rate': safety_rate
    }
