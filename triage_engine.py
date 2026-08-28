"""
triage_engine.py - Hybrid Clinical Decision Engine with Real KTAS Dataset Parameters
Part of PatientTriage.ai Clinical Decision Support Platform
"""

import math
from ml_model import ml_engine
from db_mongo import hospital_db

class TriageDecisionEngine:
    """
    Hybrid Clinical Decision Support Engine.
    Combines:
    1. Deterministic Clinical Red-Flag Rules (ESI / KTAS Algorithm v4, PEWS, qSOFA)
    2. Real KTAS Parameters: AVPU (Mental 1-4), Arrival Mode (Ambulance vs Walk-in), Injury Type, NRS Pain
    3. Age-Calibrated Physiological Parameter Evaluator (Infant, Child, Adult, Geriatric)
    4. Intelligent Ward/ICU/NICU/OT/Dialysis Admission Allocator
    5. Cost-Sensitive Machine Learning Ensemble (Trained on real data.csv)
    6. Asymmetric Fail-Safe Safety Escalation Policy
    """

    def __init__(self):
        self.vital_norms = {
            'infant': { 'hr_min': 100, 'hr_max': 160, 'rr_min': 30, 'rr_max': 50, 'sbp_min': 70, 'sbp_max': 100, 'temp_min': 36.5, 'temp_max': 37.5, 'spo2_min': 95 },
            'toddler': { 'hr_min': 90, 'hr_max': 140, 'rr_min': 24, 'rr_max': 40, 'sbp_min': 80, 'sbp_max': 110, 'temp_min': 36.5, 'temp_max': 37.5, 'spo2_min': 95 },
            'child': { 'hr_min': 70, 'hr_max': 120, 'rr_min': 18, 'rr_max': 30, 'sbp_min': 90, 'sbp_max': 115, 'temp_min': 36.5, 'temp_max': 37.5, 'spo2_min': 95 },
            'adolescent': { 'hr_min': 60, 'hr_max': 100, 'rr_min': 12, 'rr_max': 20, 'sbp_min': 100, 'sbp_max': 125, 'temp_min': 36.5, 'temp_max': 37.5, 'spo2_min': 95 },
            'adult': { 'hr_min': 60, 'hr_max': 100, 'rr_min': 12, 'rr_max': 20, 'sbp_min': 95, 'sbp_max': 139, 'temp_min': 36.2, 'temp_max': 37.5, 'spo2_min': 95 },
            'geriatric': { 'hr_min': 55, 'hr_max': 95, 'rr_min': 12, 'rr_max': 22, 'sbp_min': 100, 'sbp_max': 149, 'temp_min': 36.0, 'temp_max': 37.2, 'spo2_min': 94 }
        }
        
        self.resus_keywords = [
            'cardiac arrest', 'respiratory arrest', 'unresponsive', 'pulseless',
            'apnea', 'severe anaphylaxis', 'massive hemorrhage', 'exsanguinating',
            'polytrauma', 'gunshot', 'septic shock'
        ]
        
        self.emergent_keywords = [
            'chest pain', 'angina', 'stemi', 'myocardial', 'diaphoresis', 'stroke', 'hemiparesis',
            'facial droop', 'slurred speech', 'severe dyspnea', 'stridor', 'uremia', 'hyperkalemia',
            'altered sensorium', 'altered consciousness', 'active bleeding', 'overdose', 'testicular torsion',
            'open fracture', 'suicidal'
        ]

    def get_age_category(self, age):
        try:
            age = float(age)
        except (ValueError, TypeError):
            age = 35.0
            
        if age < 0.08: return 'neonate', 'Neonate (<28 Days)'
        elif age < 1: return 'infant', 'Pediatric (Infant <1y)'
        elif age <= 3: return 'toddler', 'Pediatric (Toddler 1-3y)'
        elif age <= 11: return 'child', 'Pediatric (Child 4-11y)'
        elif age < 18: return 'adolescent', 'Pediatric (Adolescent 12-17y)'
        elif age < 65: return 'adult', 'Adult (18-64y)'
        else: return 'geriatric', 'Geriatric (65+y)'

    def calculate_completeness_score(self, p):
        required_fields = ['patient_age', 'patient_gender', 'chief_complaint', 'heart_rate', 'resp_rate', 'sbp', 'spo2', 'temp_c', 'pain_score', 'arrival_mode', 'injury', 'mental']
        present_fields = [f for f in required_fields if p.get(f) is not None and str(p.get(f)).strip() != '']
        return int(round((len(present_fields) / len(required_fields)) * 100.0))

    def evaluate_pediatric_vital_deviations(self, age_cat, vitals):
        norm_cat = 'infant' if age_cat in ['neonate', 'infant'] else age_cat
        norm_cat = 'adolescent' if norm_cat not in self.vital_norms else norm_cat
        norms = self.vital_norms.get(norm_cat, self.vital_norms['child'])
        pews = 0
        reasons = []
        
        hr = vitals.get('heart_rate', 100)
        rr = vitals.get('resp_rate', 25)
        spo2 = vitals.get('spo2', 98)
        temp = vitals.get('temp_c', 37.0)
        
        if hr > norms['hr_max'] + 20:
            pews += 2
            reasons.append(f"Severe pediatric tachycardia (HR {hr} > max {norms['hr_max']})")
        elif hr > norms['hr_max'] or hr < norms['hr_min']:
            pews += 1
            reasons.append(f"Pediatric HR out of bounds ({hr} bpm)")
            
        if rr > norms['rr_max'] + 15:
            pews += 2
            reasons.append(f"Severe pediatric tachypnea (RR {rr} > max {norms['rr_max']})")
        elif rr > norms['rr_max'] or rr < norms['rr_min']:
            pews += 1
            reasons.append(f"Pediatric RR out of bounds ({rr} bpm)")
            
        if spo2 < 92:
            pews += 3
            reasons.append(f"Pediatric severe hypoxia (SpO2 {spo2}%)")
        elif spo2 < norms['spo2_min']:
            pews += 1
            reasons.append(f"Pediatric SpO2 below normal ({spo2}%)")
            
        if temp >= 38.5:
            pews += 2 if age_cat in ['neonate', 'infant', 'toddler'] else 1
            reasons.append(f"Pediatric high fever ({temp} C)")
                
        return pews, reasons

    def evaluate_geriatric_vital_deviations(self, vitals, p):
        reasons = []
        is_high_risk = False
        
        temp = vitals.get('temp_c', 37.0)
        sbp = vitals.get('sbp', 120)
        hr = vitals.get('heart_rate', 75)
        rr = vitals.get('resp_rate', 16)
        complaint = str(p.get('chief_complaint', '')).lower()
        
        if temp >= 37.8:
            reasons.append(f"Geriatric Significant Fever ({temp} C)")
            is_high_risk = True
        elif temp < 36.0:
            reasons.append(f"Geriatric Hypothermia ({temp} C - occult sepsis/shock risk)")
            is_high_risk = True
            
        if sbp < 100:
            reasons.append(f"Geriatric Relative Hypotension (SBP {sbp} mmHg)")
            is_high_risk = True
            
        if any(w in complaint for w in ['weakness', 'dizzy', 'confusion', 'fall', 'not feeling well', 'shivering', 'sepsis']):
            if rr >= 22 or hr >= 95 or sbp < 105 or temp >= 37.5:
                reasons.append("Geriatric Atypical Sepsis/Decompensation Flag")
                is_high_risk = True
                
        if rr >= 22:
            reasons.append(f"Geriatric Tachypnea (RR {rr} bpm)")
            is_high_risk = True
            
        return is_high_risk, reasons

    def determine_ward_and_resources(self, level, age, complaint, vitals, mental_code, is_injury, arrival_mode):
        complaint_lower = str(complaint).lower()
        spo2 = vitals.get('spo2', 98)
        sbp = vitals.get('sbp', 120)
        hr = vitals.get('heart_rate', 75)
        rr = vitals.get('resp_rate', 16)
        temp = vitals.get('temp_c', 37.0)

        # 1. Dialysis & Nephrology
        if any(k in complaint_lower for k in ['dialysis', 'renal', 'kidney failure', 'uremia', 'creatinine', 'potassium', 'hyperkalemia']):
            return {
                "ward": "Dialysis & Nephrology Unit",
                "ward_key": "dialysis",
                "equipment_needed": "Hemodialysis Machine + Central Line Standby",
                "specialist": "Dr. Farhan Qureshi (Nephrology & Dialysis)",
                "rationale": "Patient requires immediate hemodialysis / renal clearance monitoring."
            }

        # 2. Emergency Trauma OT
        if is_injury == 1 or any(k in complaint_lower for k in ['active bleeding', 'stab', 'gunshot', 'open fracture', 'polytrauma', 'peritonitis', 'acute abdomen']):
            if level <= 2 or 'open fracture' in complaint_lower or 'active bleeding' in complaint_lower or 'polytrauma' in complaint_lower:
                return {
                    "ward": "Emergency Trauma Operation Theatre (OT-1)",
                    "ward_key": "ot",
                    "equipment_needed": "Surgical Standby + 2 Units O- Blood Crossmatch",
                    "specialist": "Dr. Sneha Patel (Trauma & Ortho Surgery)",
                    "rationale": "High-velocity trauma / acute surgical emergency requiring immediate OR standby."
                }

        # 3. Neonatal ICU (NICU)
        if age < 0.08 or (age < 0.5 and (temp >= 38.8 or spo2 < 93 or rr > 48)):
            return {
                "ward": "Neonatal ICU (NICU - Newborn Care)",
                "ward_key": "nicu",
                "equipment_needed": "Neonatal Radiant Incubator + Micro-ventilator",
                "specialist": "Dr. Ananya Iyer (Pediatrics & Neonatology)",
                "rationale": "Critically vulnerable neonate/infant requiring specialized incubators and continuous micro-monitoring."
            }

        # 4. Pediatric ICU (PICU)
        if age < 16 and (level <= 2 or spo2 < 91 or rr > 40 or 'stridor' in complaint_lower):
            return {
                "ward": "Pediatric ICU (PICU)",
                "ward_key": "picu",
                "equipment_needed": "Pediatric Multi-para Monitor + Oxygen Blender",
                "specialist": "Dr. Ananya Iyer (Pediatrics & Neonatology)",
                "rationale": "Pediatric patient with acute respiratory/neurologic compromise requiring PICU observation."
            }

        # 5. Adult ICU
        if level == 1 or (level == 2 and (sbp < 85 or spo2 < 88 or mental_code >= 3 or hr < 40 or hr > 150 or 'septic shock' in complaint_lower)):
            return {
                "ward": "Adult Intensive Care Unit (ICU)",
                "ward_key": "icu",
                "equipment_needed": "Invasive Ventilator + Arterial Line + Infusion Pump",
                "specialist": "Dr. Vikram Sethi (Critical Care Intensivist)",
                "rationale": "Severe hemodynamic instability / multi-organ failure risk mandating 1:1 intensive care."
            }

        # 6. High Dependency Unit (HDU / Cardiac Telemetry)
        if any(k in complaint_lower for k in ['chest', 'heart', 'ecg', 'angina', 'stemi', 'diaphoresis', 'arrhythmia', 'heart failure']):
            return {
                "ward": "High Dependency Unit (HDU / Cardiac Telemetry)",
                "ward_key": "hdu",
                "equipment_needed": "Continuous 12-Lead Telemetry ECG Monitor",
                "specialist": "Dr. Rajesh Sharma (Cardiology)",
                "rationale": "High-risk cardiac presentation requiring continuous telemetry rhythm tracking."
            }

        # 7. General Ward Inpatient
        if level == 3 or (level == 4 and is_injury == 1 and ('fracture' in complaint_lower or 'dislocation' in complaint_lower)):
            return {
                "ward": "General Ward (Male/Female Inpatient)",
                "ward_key": "general",
                "equipment_needed": "Standard Inpatient Bed + IV Infusion Pole",
                "specialist": "Dr. Meera Nambiar (General Medicine & Sepsis)",
                "rationale": "Stable inpatient requiring multi-dose IV antibiotics, imaging workup, or orthopedic immobilization."
            }

        # 8. Outpatient Fast-Track Pod
        return {
            "ward": "Outpatient Fast-Track / Minor Injury Pod",
            "ward_key": "fast_track",
            "equipment_needed": "Treatment Recliner / Suture Tray / Eye Slit Lamp",
            "specialist": "Dr. Amit Roy (Emergency Medicine Lead)",
            "rationale": "Low acuity condition suitable for rapid outpatient evaluation and discharge."
        }

    def evaluate_triage(self, p):
        """Full hybrid triage assessment incorporating real KTAS parameters."""
        age = float(p.get('patient_age', p.get('Age', 35)))
        age_cat, age_label = self.get_age_category(age)
        
        hr = float(p.get('heart_rate', p.get('HR', 75)))
        rr = float(p.get('resp_rate', p.get('RR', 16)))
        sbp = float(p.get('sbp', p.get('SBP', 120)))
        dbp = float(p.get('dbp', p.get('DBP', 80)))
        spo2 = float(p.get('spo2', p.get('Saturation', p.get('saturation', 98.0))))
        temp = float(p.get('temp_c', p.get('BT', p.get('bt', 36.8))))
        pain = float(p.get('pain_score', p.get('NRS_pain', p.get('nrs_pain', 0))))
        
        # Real KTAS attributes
        arrival_mode = int(p.get('arrival_mode', p.get('Arrival mode', 1)))
        is_injury = int(p.get('injury', p.get('Injury', 2)))
        
        # Mental AVPU: 1=Alert, 2=Verbal, 3=Pain, 4=Unresponsive
        mental = p.get('mental', p.get('Mental', 1))
        if isinstance(mental, str):
            if mental.upper().startswith('U'): mental_code = 4
            elif mental.upper().startswith('P'): mental_code = 3
            elif mental.upper().startswith('V'): mental_code = 2
            else: mental_code = 1
        else:
            mental_code = int(mental)

        complaint = str(p.get('chief_complaint', p.get('Chief_complain', ''))).lower()
        vitals = {'heart_rate': hr, 'resp_rate': rr, 'sbp': sbp, 'dbp': dbp, 'spo2': spo2, 'temp_c': temp, 'pain_score': pain}
        completeness = self.calculate_completeness_score(p)
        
        clinical_drivers = []
        rule_level = None
        rule_reason = None
        
        # 1. Deterministic Level 1 Rules
        if mental_code == 4:
            rule_level = 1
            rule_reason = "Unresponsive Mental Status (AVPU 4) - Immediate Resuscitation required."
        elif spo2 < 85:
            rule_level = 1
            rule_reason = f"Critical Life-Threatening Hypoxia (SpO2 {spo2}%) - Emergency intubation."
        elif hr > 180 or hr < 35:
            rule_level = 1
            rule_reason = f"Extremes of Heart Rate (HR {hr} bpm) - Impending cardiac arrest."
        elif (sbp <= 85 and age >= 18) or (sbp < 90 and temp >= 38.5):
            rule_level = 1
            rule_reason = f"Severe Shock / Critical Hypotension (SBP {sbp} mmHg, Temp {temp} C)."
        elif any(k in complaint for k in self.resus_keywords):
            rule_level = 1
            rule_reason = f"Critical Chief Complaint: '{p.get('chief_complaint')}'."
            
        # 2. Deterministic Level 2 Rules
        if rule_level is None:
            if mental_code in [2, 3]:
                rule_level = 2
                rule_reason = f"Depressed Mental State (AVPU {mental_code} - Responds to Verbal/Pain only)."
            elif any(k in complaint for k in self.emergent_keywords):
                rule_level = 2
                rule_reason = f"High-Risk Presentation: '{p.get('chief_complaint')}'."
            elif spo2 <= 91:
                rule_level = 2
                rule_reason = f"Significant Hypoxia (SpO2 {spo2}%) requiring high-flow oxygen."
            elif sbp < 90 and age >= 18:
                rule_level = 2
                rule_reason = f"Hypotension Alert (SBP {sbp} mmHg) - Sepsis/Shock Protocol."
            elif hr >= 135 or hr <= 45:
                rule_level = 2
                rule_reason = f"Severe Hemodynamic Derangement (HR {hr} bpm)."
            elif pain >= 9 and hr > 100:
                rule_level = 2
                rule_reason = f"Severe Intractable Pain ({pain}/10) with systemic distress."
            elif arrival_mode == 2 and (sbp < 95 or hr > 115):
                rule_level = 2
                rule_reason = "119 Emergency Ambulance Arrival with Hemodynamic Derangement."
                
            # Age-specific Level 2 triggers
            if age_cat in ['neonate', 'infant', 'toddler']:
                pews, ped_reasons = self.evaluate_pediatric_vital_deviations(age_cat, vitals)
                if pews >= 3 or (temp >= 38.8 and age < 1):
                    rule_level = 2
                    rule_reason = f"Pediatric Early Warning Breach (PEWS {pews}): " + "; ".join(ped_reasons[:2])
            elif age_cat == 'geriatric':
                ger_high_risk, ger_reasons = self.evaluate_geriatric_vital_deviations(vitals, p)
                if ger_high_risk and (sbp < 100 or rr >= 22 or temp < 36.0 or temp >= 37.8):
                    rule_level = 2
                    rule_reason = "Geriatric Severe Decompensation Alert: " + "; ".join(ger_reasons[:2])
                    
        # 3. Machine Learning Model Evaluation
        ml_input = dict(p)
        ml_input['patient_age'] = age
        ml_input['heart_rate'] = hr
        ml_input['resp_rate'] = rr
        ml_input['sbp'] = sbp
        ml_input['dbp'] = dbp
        ml_input['spo2'] = spo2
        ml_input['temp_c'] = temp
        ml_input['pain_score'] = pain
        ml_input['arrival_mode'] = arrival_mode
        ml_input['is_injury'] = 1 if is_injury == 1 else 0
        ml_input['avpu'] = 'Unresponsive' if mental_code == 4 else ('Pain' if mental_code == 3 else ('Verbal' if mental_code == 2 else 'Alert'))
        
        ml_res = ml_engine.predict_single(ml_input)
        ml_level = ml_res['predicted_level']
        confidence = ml_res['confidence']
        entropy = ml_res['entropy']
        
        # 4. Hybrid Synthesis & Fail-Safe Escalation
        final_level = ml_level
        safety_escalation_applied = False
        safety_escalation_reason = None
        
        if rule_level is not None:
            if rule_level < ml_level:
                final_level = rule_level
                clinical_drivers.append(f"Clinical Rule Trigger (Level {rule_level}): {rule_reason}")
            else:
                final_level = min(rule_level, ml_level)
                if rule_reason: clinical_drivers.append(rule_reason)
        else:
            if (entropy > 0.88 and confidence < 0.45) or (completeness < 50):
                if final_level > 2:
                    escalated_to = final_level - 1
                    safety_escalation_applied = True
                    safety_escalation_reason = f"Safety Escalation: Upgraded Level {final_level} -> Level {escalated_to} due to high predictive uncertainty (H={entropy:.2f})."
                    final_level = escalated_to
                    clinical_drivers.append(safety_escalation_reason)
                    
        for fa in ml_res['feature_attributions']:
            clinical_drivers.append(f"{fa['feature']}: {fa['value']} ({fa['impact']})")
        clinical_drivers = list(dict.fromkeys(clinical_drivers))
        
        # 5. Determine Exact Ward & Resources
        ward_decision = self.determine_ward_and_resources(final_level, age, complaint, vitals, mental_code, is_injury, arrival_mode)
        
        level_names = {
            1: "Level 1 - Resuscitation (Immediate)",
            2: "Level 2 - Emergent (Immediate/10 min)",
            3: "Level 3 - Urgent (30 min)",
            4: "Level 4 - Less Urgent (60 min)",
            5: "Level 5 - Non-Urgent (120 min)"
        }
        
        return {
            'final_level': int(final_level),
            'level_name': level_names.get(final_level, f"Level {final_level}"),
            'rule_level': rule_level,
            'ml_level': int(ml_level),
            'confidence': float(confidence),
            'confidence_percent': int(round(confidence * 100)),
            'entropy': float(entropy),
            'uncertainty_score': float(round(entropy * 100, 1)),
            'uncertainty_label': "Low Uncertainty" if entropy < 0.3 else ("Moderate" if entropy < 0.55 else "High Uncertainty"),
            'safety_escalation_applied': safety_escalation_applied,
            'safety_escalation_reason': safety_escalation_reason,
            'completeness_score': completeness,
            'age_category': age_label,
            'ward_admission_decision': ward_decision,
            'department_recommendation': ward_decision['ward'],
            'equipment_needed': ward_decision['equipment_needed'],
            'attending_specialist': ward_decision['specialist'],
            'clinical_drivers': clinical_drivers,
            'admission_risk': ml_res['admission_risk'],
            'admission_risk_percent': int(round(ml_res['admission_risk'] * 100)),
            'risk_index': ml_res['risk_index'],
            'probabilities': ml_res['probabilities']
        }

# Global singleton decision engine
triage_engine = TriageDecisionEngine()
