"""
queue_manager.py - Dynamic ED Waiting Queue & Deterioration Monitoring System
Part of PatientTriage.ai Clinical Decision Support Platform
"""

import time
from datetime import datetime, timedelta
import uuid

class EDQueueManager:
    """
    Manages real-time Emergency Department waiting room queue,
    hospital wards/specialty capacity configuration,
    monitors safe wait-time thresholds per ESI level, and triggers
    automatic re-assessment alerts upon wait-time breach or vital sign deterioration.
    """

    SAFE_WAIT_LIMITS = {
        1: 0,    # Immediate (0 min)
        2: 10,   # 10 min
        3: 30,   # 30 min
        4: 60,   # 60 min
        5: 120   # 120 min
    }

    HOSPITAL_PROFILES = {
        'urban_level1': {
            'id': 'urban_level1',
            'name': 'Metro General Level-1 Trauma Center',
            'tier': 'Large Urban Trauma Center (350-500+ visits/day)',
            'total_beds': 48,
            'occupied_beds': 32,
            'wards': {
                'resus': {'name': 'Resuscitation & Trauma Bays', 'capacity': 8, 'occupied': 5, 'esi': 'ESI 1-2'},
                'cardiac': {'name': 'Cardiac Tele-Monitored Suite', 'capacity': 10, 'occupied': 7, 'esi': 'ESI 2-3'},
                'pediatric': {'name': 'Pediatric Emergency & HDU', 'capacity': 10, 'occupied': 6, 'esi': 'ESI 1-3'},
                'acute': {'name': 'Acute Care Bays (Area A)', 'capacity': 14, 'occupied': 11, 'esi': 'ESI 2-3'},
                'fast_track': {'name': 'Fast-Track / Minor Injury Pods', 'capacity': 12, 'occupied': 7, 'esi': 'ESI 4-5'},
                'psych': {'name': 'Secure Psychiatric Assessment Unit', 'capacity': 4, 'occupied': 2, 'esi': 'ESI 2-3'}
            },
            'specialties': ['Trauma Surgery', 'Interventional Cardiology', 'Neurosurgery', 'Pediatrics', 'Orthopedics', 'Psychiatry', 'General Surgery', 'Obs & Gynae']
        },
        'community': {
            'id': 'community',
            'name': 'St. Jude Community Hospital',
            'tier': 'Mid-Size Community Hospital (150-250 visits/day)',
            'total_beds': 26,
            'occupied_beds': 16,
            'wards': {
                'resus': {'name': 'Resuscitation Bays', 'capacity': 4, 'occupied': 2, 'esi': 'ESI 1-2'},
                'acute': {'name': 'General Acute Bays', 'capacity': 12, 'occupied': 8, 'esi': 'ESI 2-3'},
                'pediatric': {'name': 'Pediatric Observation Area', 'capacity': 4, 'occupied': 2, 'esi': 'ESI 2-4'},
                'fast_track': {'name': 'Ambulatory Fast-Track', 'capacity': 6, 'occupied': 4, 'esi': 'ESI 4-5'}
            },
            'specialties': ['Emergency Medicine', 'Cardiology (Consult)', 'General Surgery', 'Pediatrics', 'Orthopedics']
        },
        'rural_critical': {
            'id': 'rural_critical',
            'name': 'Highland Critical Access Rural Hospital',
            'tier': 'Small Rural Emergency Department (40-80 visits/day)',
            'total_beds': 10,
            'occupied_beds': 5,
            'wards': {
                'resus': {'name': 'Emergency Resus / Stabilization', 'capacity': 2, 'occupied': 1, 'esi': 'ESI 1-2'},
                'acute': {'name': 'Multi-Purpose Acute Care', 'capacity': 5, 'occupied': 3, 'esi': 'ESI 2-4'},
                'fast_track': {'name': 'Outpatient Triage Exam Room', 'capacity': 3, 'occupied': 1, 'esi': 'ESI 4-5'}
            },
            'specialties': ['General Emergency Medicine', 'Tele-Specialty Consult', 'EMS Transfer Network']
        }
    }

    def __init__(self):
        self.current_profile_key = 'urban_level1'
        self.hospital_config = dict(self.HOSPITAL_PROFILES['urban_level1'])
        self.queue = [] # Active waiting patients
        self.served_patients = []
        self.alerts = []

    def set_hospital_profile(self, profile_key):
        """Switches active hospital scale and ward topology."""
        if profile_key in self.HOSPITAL_PROFILES:
            self.current_profile_key = profile_key
            self.hospital_config = dict(self.HOSPITAL_PROFILES[profile_key])
            return self.hospital_config
        return None

    def update_custom_config(self, custom_dict):
        """Updates custom hospital ward capacity, specialties, and bed count."""
        self.hospital_config.update(custom_dict)
        return self.hospital_config

    def add_patient(self, patient_data, triage_result):
        """Adds a newly triaged patient to the active waiting queue."""
        patient_id = patient_data.get('patient_id') or f"PT-{uuid.uuid4().hex[:6].upper()}"
        visit_id = patient_data.get('visit_id') or f"VT-{uuid.uuid4().hex[:6].upper()}"
        arrival_time = patient_data.get('arrival_datetime') or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        simulated_wait_min = float(patient_data.get('wait_time_doctor_min', 0))
        final_level = int(triage_result.get('final_level', 3))
        
        entry = {
            'patient_id': patient_id,
            'visit_id': visit_id,
            'name': patient_data.get('name', f"Patient {patient_id}"),
            'age': float(patient_data.get('patient_age', 35)),
            'gender': patient_data.get('patient_gender', 'Unknown'),
            'chief_complaint': patient_data.get('chief_complaint', 'Unspecified'),
            'department': patient_data.get('department', 'Emergency'),
            'triage_level': final_level,
            'original_ai_level': int(triage_result.get('ml_level', final_level)),
            'confidence': triage_result.get('confidence', 0.85),
            'confidence_percent': triage_result.get('confidence_percent', 85),
            'uncertainty_label': triage_result.get('uncertainty_label', 'Low Uncertainty'),
            'safety_escalated': triage_result.get('safety_escalation_applied', False),
            'safety_escalation_reason': triage_result.get('safety_escalation_reason'),
            'recommended_zone': triage_result.get('department_recommendation', 'Acute Bay'),
            'admission_risk_percent': triage_result.get('admission_risk_percent', 25),
            'risk_index': triage_result.get('risk_index', 40),
            'vitals': {
                'heart_rate': patient_data.get('heart_rate', 75),
                'resp_rate': patient_data.get('resp_rate', 16),
                'sbp': patient_data.get('sbp', 120),
                'spo2': patient_data.get('spo2', 98),
                'temp_c': patient_data.get('temp_c', 37.0),
                'pain_score': patient_data.get('pain_score', 0)
            },
            'has_prior_history': bool(patient_data.get('has_prior_history', False) or patient_data.get('prior_history', False)),
            'arrival_time': arrival_time,
            'wait_minutes': simulated_wait_min,
            'max_safe_wait': self.SAFE_WAIT_LIMITS.get(final_level, 60),
            'status': 'WAITING',
            'reassessment_required': False,
            'deterioration_flag': False,
            'vital_history': [{
                'timestamp': arrival_time,
                'vitals': {
                    'heart_rate': patient_data.get('heart_rate', 75),
                    'resp_rate': patient_data.get('resp_rate', 16),
                    'sbp': patient_data.get('sbp', 120),
                    'spo2': patient_data.get('spo2', 98),
                    'temp_c': patient_data.get('temp_c', 37.0)
                }
            }]
        }
        
        self.queue.append(entry)
        self.sort_queue()
        self._check_patient_status(entry)
        return entry

    def sort_queue(self):
        """
        Sorts waiting room queue by clinical priority:
        1. Deteriorating patients first
        2. ESI Triage Level (Level 1 > 2 > 3 > 4 > 5)
        3. Within same ESI level, longest wait time or highest wait-to-safe ratio first
        """
        def queue_key(p):
            is_deteriorating = 0 if p.get('deterioration_flag') else 1
            esi = p.get('triage_level', 5)
            wait_ratio = p.get('wait_minutes', 0) / max(p.get('max_safe_wait', 60), 1)
            return (is_deteriorating, esi, -wait_ratio, -p.get('wait_minutes', 0))
            
        self.queue.sort(key=queue_key)

    def _check_patient_status(self, p):
        """Evaluates wait-time threshold breach and logs alerts."""
        safe_limit = p['max_safe_wait']
        wait_min = p['wait_minutes']
        
        if safe_limit > 0 and wait_min >= safe_limit:
            p['reassessment_required'] = True
            severity = 'CRITICAL' if wait_min >= safe_limit * 1.5 else 'WARNING'
            alert = {
                'id': f"ALT-{uuid.uuid4().hex[:6]}",
                'patient_id': p['patient_id'],
                'severity': severity,
                'message': f"Safe wait time breached for ESI-{p['triage_level']} patient {p['patient_id']} ({wait_min:.0f}m / max {safe_limit}m). Re-assessment mandated.",
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            if not any(a['patient_id'] == p['patient_id'] and a['severity'] == severity for a in self.alerts[-5:]):
                self.alerts.insert(0, alert)

    def update_repeat_vitals(self, patient_id, new_vitals, triage_engine):
        """
        Captures newly measured vitals for a waiting patient.
        If vitals indicate decompensation/deterioration, automatically escalates priority.
        """
        for p in self.queue:
            if p['patient_id'] == patient_id:
                old_vitals = p['vitals']
                p['vitals'] = new_vitals
                p['vital_history'].append({
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'vitals': new_vitals
                })
                
                re_eval = triage_engine.evaluate_triage({
                    'patient_age': p['age'],
                    'patient_gender': p['gender'],
                    'chief_complaint': p['chief_complaint'],
                    'heart_rate': new_vitals.get('heart_rate', old_vitals['heart_rate']),
                    'resp_rate': new_vitals.get('resp_rate', old_vitals['resp_rate']),
                    'sbp': new_vitals.get('sbp', old_vitals['sbp']),
                    'spo2': new_vitals.get('spo2', old_vitals['spo2']),
                    'temp_c': new_vitals.get('temp_c', old_vitals['temp_c']),
                    'pain_score': new_vitals.get('pain_score', old_vitals['pain_score']),
                    'has_prior_history': p['has_prior_history']
                })
                
                new_level = re_eval['final_level']
                old_level = p['triage_level']
                
                if new_level < old_level:
                    p['triage_level'] = new_level
                    p['deterioration_flag'] = True
                    p['max_safe_wait'] = self.SAFE_WAIT_LIMITS.get(new_level, 30)
                    p['safety_escalated'] = True
                    p['safety_escalation_reason'] = f"Dynamic Deterioration: Re-triage escalated ESI {old_level} → ESI {new_level} due to worsening vitals."
                    p['recommended_zone'] = re_eval['department_recommendation']
                    
                    self.alerts.insert(0, {
                        'id': f"ALT-DET-{uuid.uuid4().hex[:4]}",
                        'patient_id': p['patient_id'],
                        'severity': 'CRITICAL_DETERIORATION',
                        'message': f"⚠️ ACTIVE DETERIORATION: Patient {p['patient_id']} decompensating! Upgraded from ESI {old_level} to ESI {new_level}.",
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                    
                self.sort_queue()
                return p
        return None

    def advance_time(self, minutes=5):
        """Simulates passage of time in the ED waiting room."""
        for p in self.queue:
            if p['status'] == 'WAITING':
                p['wait_minutes'] += minutes
                self._check_patient_status(p)
        self.sort_queue()

    def get_queue_summary(self):
        """Returns ED status snapshot for dashboard."""
        waiting_count = len([p for p in self.queue if p['status'] == 'WAITING'])
        level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        reassess_count = 0
        deteriorating_count = 0
        
        for p in self.queue:
            if p['status'] == 'WAITING':
                lvl = p.get('triage_level', 3)
                level_counts[lvl] = level_counts.get(lvl, 0) + 1
                if p.get('reassessment_required'):
                    reassess_count += 1
                if p.get('deterioration_flag'):
                    deteriorating_count += 1
                    
        avg_wait = sum(p['wait_minutes'] for p in self.queue if p['status'] == 'WAITING') / max(waiting_count, 1)
        
        total_beds = self.hospital_config.get('total_beds', 30)
        occ_beds = self.hospital_config.get('occupied_beds', 18)
        
        return {
            'total_waiting': waiting_count,
            'level_counts': level_counts,
            'reassessment_alerts': reassess_count,
            'deteriorating_patients': deteriorating_count,
            'average_wait_minutes': round(avg_wait, 1),
            'hospital_profile': self.hospital_config.get('name', 'Metro General Hospital'),
            'hospital_tier': self.hospital_config.get('tier', 'Level 1 Trauma Center'),
            'bed_capacity': total_beds,
            'occupied_beds': occ_beds,
            'bed_utilization_percent': round((occ_beds / total_beds) * 100, 1),
            'wards': self.hospital_config.get('wards', {}),
            'specialties': self.hospital_config.get('specialties', []),
            'active_alerts': self.alerts[:8]
        }

# Global singleton queue manager
queue_manager = EDQueueManager()
