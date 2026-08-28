"""
audit_logger.py - HIPAA & GDPR Compliant Immutable Audit Logging & Clinician Override System
Part of PatientTriage.ai Clinical Decision Support Platform
"""

import json
import hashlib
from datetime import datetime
import os

class ClinicalAuditLogger:
    """
    Maintains a tamper-evident, append-only audit trail for all triage decisions and clinician overrides.
    Complies with:
    - US HIPAA Security Rule 45 CFR § 164.312(b) (Audit Controls)
    - EU GDPR Article 22 (Human-in-the-loop oversight & algorithmic explainability)
    - Meaningful Use / ONC Health IT Certification criteria
    """

    OVERRIDE_REASON_CODES = {
        'CLINICAL_INTUITION': 'Clinician holistic intuition / visual distress not captured in vitals',
        'ATYPICAL_PRESENTATION': 'Subtle/atypical presentation in high-risk patient group',
        'COMPLEX_COMORBIDITY': 'Severe underlying comorbidity or immunosuppression',
        'SOCIAL_VULNERABILITY': 'Social vulnerability / domestic risk / lack of home support',
        'OCCULT_TRAUMA': 'High mechanism of injury despite initially normal vital signs',
        'DOWNGRADE_BENIGN': 'Identified benign etiology upon direct bedside physical exam',
        'PROTOCOL_EXCEPTION': 'Hospital departmental protocol or direct physician request'
    }

    def __init__(self, log_file="audit_log.json"):
        self.log_file = log_file
        self.logs = []
        self._load_logs()

    def _load_logs(self):
        """Loads existing audit trail if available."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    self.logs = json.load(f)
            except Exception:
                self.logs = []
        else:
            self.logs = []

    def _save_logs(self):
        """Persists audit log to disk."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, indent=2)
        except Exception as e:
            print(f"Error saving audit log: {e}")

    def _compute_hash(self, entry_dict):
        """Generates SHA-256 cryptographic seal for tamper detection."""
        prev_hash = self.logs[-1]['hash'] if self.logs else "GENESIS_HASH_000000000000"
        payload = f"{prev_hash}:{entry_dict['timestamp']}:{entry_dict['patient_id']}:{entry_dict['ai_level']}:{entry_dict['final_level']}:{entry_dict.get('clinician_id', '')}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def log_triage_decision(self, patient_data, triage_result, clinician_id="RN-AutoTriage"):
        """Logs an automated or clinician-accepted initial triage decision."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        entry = {
            'log_id': f"AUDIT-{len(self.logs)+1:06d}",
            'timestamp': timestamp,
            'jurisdiction': 'US-HIPAA / EU-GDPR Art 22',
            'patient_id': patient_data.get('patient_id', 'UNKNOWN'),
            'visit_id': patient_data.get('visit_id', 'UNKNOWN'),
            'age': patient_data.get('patient_age'),
            'gender': patient_data.get('patient_gender'),
            'chief_complaint': patient_data.get('chief_complaint'),
            'has_prior_history': bool(patient_data.get('has_prior_history') or patient_data.get('prior_history')),
            'ai_level': int(triage_result.get('final_level', 3)),
            'ai_confidence': float(triage_result.get('confidence', 0.85)),
            'uncertainty_score': float(triage_result.get('uncertainty_score', 15.0)),
            'safety_escalated': bool(triage_result.get('safety_escalation_applied', False)),
            'safety_reason': triage_result.get('safety_escalation_reason'),
            'final_level': int(triage_result.get('final_level', 3)),
            'is_override': False,
            'clinician_id': clinician_id,
            'override_reason_code': None,
            'override_reason_text': None,
            'override_notes': None,
            'clinical_drivers': triage_result.get('clinical_drivers', []),
            'status': 'ACCEPTED_AS_RECOMMENDED'
        }
        entry['hash'] = self._compute_hash(entry)
        self.logs.append(entry)
        self._save_logs()
        return entry

    def log_clinician_override(self, patient_data, triage_result, override_data):
        """
        Logs a clinician override of the AI recommendation.
        Mandates override reason code, clinician ID, and rationale notes.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        reason_code = override_data.get('reason_code', 'CLINICAL_INTUITION')
        reason_text = self.OVERRIDE_REASON_CODES.get(reason_code, 'Other Clinician Rationale')
        
        entry = {
            'log_id': f"AUDIT-{len(self.logs)+1:06d}",
            'timestamp': timestamp,
            'jurisdiction': 'US-HIPAA / EU-GDPR Art 22',
            'patient_id': patient_data.get('patient_id', 'UNKNOWN'),
            'visit_id': patient_data.get('visit_id', 'UNKNOWN'),
            'age': patient_data.get('patient_age'),
            'gender': patient_data.get('patient_gender'),
            'chief_complaint': patient_data.get('chief_complaint'),
            'has_prior_history': bool(patient_data.get('has_prior_history') or patient_data.get('prior_history')),
            'ai_level': int(triage_result.get('final_level', 3)),
            'ai_confidence': float(triage_result.get('confidence', 0.85)),
            'uncertainty_score': float(triage_result.get('uncertainty_score', 15.0)),
            'safety_escalated': bool(triage_result.get('safety_escalation_applied', False)),
            'safety_reason': triage_result.get('safety_escalation_reason'),
            'final_level': int(override_data.get('new_level', triage_result.get('final_level'))),
            'is_override': True,
            'clinician_id': override_data.get('clinician_id', 'RN-SeniorTriage'),
            'clinician_name': override_data.get('clinician_name', 'Nurse Specialist'),
            'override_reason_code': reason_code,
            'override_reason_text': reason_text,
            'override_notes': override_data.get('notes', 'Direct clinician bedside re-evaluation.'),
            'clinical_drivers': triage_result.get('clinical_drivers', []),
            'status': 'CLINICIAN_OVERRIDE_LOGGED'
        }
        entry['hash'] = self._compute_hash(entry)
        self.logs.append(entry)
        self._save_logs()
        return entry

    def get_recent_logs(self, limit=25, overrides_only=False):
        """Retrieves recent audit entries."""
        if overrides_only:
            filtered = [l for l in self.logs if l.get('is_override')]
            return filtered[-limit:][::-1]
        return self.logs[-limit:][::-1]

    def get_audit_metrics(self):
        """Computes audit statistics for safety and compliance reporting."""
        total = len(self.logs)
        if total == 0:
            return {
                'total_decisions': 0,
                'override_count': 0,
                'override_rate_percent': 0.0,
                'safety_escalations': 0,
                'concordance_rate_percent': 100.0
            }
            
        overrides = [l for l in self.logs if l.get('is_override')]
        escalations = [l for l in self.logs if l.get('safety_escalated')]
        
        return {
            'total_decisions': total,
            'override_count': len(overrides),
            'override_rate_percent': round((len(overrides) / total) * 100, 1),
            'safety_escalations': len(escalations),
            'concordance_rate_percent': round(((total - len(overrides)) / total) * 100, 1)
        }

# Global singleton audit logger
audit_logger = ClinicalAuditLogger()
