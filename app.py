"""
app.py - Hospital Management Platform & Intelligent Clinical Triage API
Integrated with MongoDB Hybrid Data Layer
"""

from flask import Flask, render_template, request, jsonify
import os
import json
from triage_engine import triage_engine
from queue_manager import queue_manager
from audit_logger import audit_logger
from surge_simulator import surge_sim
from test_cases import CLINICAL_BENCHMARK_CASES, run_all_benchmarks
from db_mongo import hospital_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hospital-mgmt-mongo-secret-2026'

# Seed initial queue if empty
def seed_initial_queue():
    if len(queue_manager.queue) == 0:
        sample_cases = CLINICAL_BENCHMARK_CASES[:5]
        for case in sample_cases:
            triage_res = triage_engine.evaluate_triage(case)
            queue_manager.add_patient(case, triage_res)
            audit_logger.log_triage_decision(case, triage_res, clinician_id="RN-InitialIntake")

try:
    seed_initial_queue()
except Exception as e:
    print(f"Queue seed note: {e}")

@app.route('/')
def index():
    """Main Hospital Management & Triage Admission Dashboard."""
    return render_template('index.html')

# ----------------- 1. DOCTORS & STAFF APIS -----------------

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    """Returns all doctors, specialties, on-duty status, and backup doctor."""
    docs = hospital_db.get_doctors()
    return jsonify({'success': True, 'doctors': docs})

@app.route('/api/doctors/leave', methods=['POST'])
def handle_doctor_leave():
    """Updates doctor leave status and auto-assigns substitute doctor."""
    data = request.get_json() or {}
    doc_id = data.get('doctor_id')
    on_leave = data.get('on_leave', True)
    reason = data.get('reason', 'Emergency Medical Leave')
    backup_id = data.get('backup_id')

    res = hospital_db.update_doctor_leave(doc_id, on_leave, reason, backup_id)
    return jsonify(res)

# ----------------- 0. MONGODB CONNECTION & CONFIGURATION -----------------

@app.route('/api/mongo/status', methods=['GET'])
def get_mongo_status_route():
    """Returns live connection status, MongoDB URI, and document counts."""
    return jsonify(hospital_db.get_status_info())

@app.route('/api/mongo/connect', methods=['POST'])
def connect_mongo_route():
    """Tests and connects to a user-provided MongoDB URI (e.g. Atlas / Local)."""
    data = request.get_json() or {}
    uri = data.get('uri', '').strip()
    if not uri:
        return jsonify({'success': False, 'error': 'MongoDB URI cannot be empty.'}), 400

    res = hospital_db.try_connect(uri)
    return jsonify(res)

# ----------------- 2. LIVE RESOURCES & WARD APIS -----------------

@app.route('/api/resources', methods=['GET'])
def get_hospital_resources():
    """Returns live wards, bed occupancies, O2 cylinders, dialysis, ventilators, and OTs."""
    res = hospital_db.get_resources()
    return jsonify({'success': True, 'resources': res})

@app.route('/api/resources/empty_all_beds', methods=['POST'])
def empty_all_beds_route():
    """Empties every single bed across all wards in MongoDB."""
    res = hospital_db.empty_all_beds()
    return jsonify(res)

@app.route('/api/resources/update_bed', methods=['POST'])
def update_bed():
    """Updates individual bed status (Occupied, Available, Under_Cleaning)."""
    data = request.get_json() or {}
    ward_key = data.get('ward_key')
    bed_id = data.get('bed_id')
    new_status = data.get('status')
    patient_id = data.get('patient_id')

    res = hospital_db.update_bed_status(ward_key, bed_id, new_status, patient_id)
    return jsonify(res)

@app.route('/api/resources/update_equipment', methods=['POST'])
def update_equipment():
    """Updates medical equipment in-use counts or central O2 pressure."""
    data = request.get_json() or {}
    eq_type = data.get('equipment_type') # dialysis_machines, oxygen_cylinders, ventilators
    delta = int(data.get('delta_in_use', 0))
    psi = data.get('pressure_psi')

    res = hospital_db.update_equipment(eq_type, delta, psi)
    return jsonify(res)

@app.route('/api/resources/update_ot', methods=['POST'])
def update_ot():
    """Updates Operation Theatre status, surgeon, and case details."""
    data = request.get_json() or {}
    ot_id = data.get('ot_id')
    new_status = data.get('status') # Available, In_Surgery, Under_Sterilization, Reserved_Emergency
    surgeon = data.get('surgeon')
    case_info = data.get('case')

    res = hospital_db.update_ot_status(ot_id, new_status, surgeon, case_info)
    return jsonify(res)

# ----------------- 3. PATIENT TRIAGE & WARD ADMISSION -----------------

@app.route('/api/patient/transfer', methods=['POST'])
def transfer_patient_route():
    """Transfers patient (e.g. ICU Step-Down to General Ward) and deallocates old bed."""
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    from_ward = data.get('from_ward')
    from_bed = data.get('from_bed')
    to_ward = data.get('to_ward')
    to_bed = data.get('to_bed')
    new_doc_id = data.get('new_doctor_id')

    res = hospital_db.transfer_patient(patient_id, from_ward, from_bed, to_ward, to_bed, new_doc_id)
    return jsonify(res)

@app.route('/api/patient/discharge', methods=['POST'])
def discharge_patient_route():
    """Discharges patient completely, frees medical equipment, and marks bed Under_Cleaning."""
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    ward_key = data.get('ward_key')
    bed_id = data.get('bed_id')

    res = hospital_db.discharge_patient(patient_id, ward_key, bed_id)
    return jsonify(res)

@app.route('/api/resources/clean_bed', methods=['POST'])
def clean_bed_route():
    """Completes terminal bed sanitization, marking it Available."""
    data = request.get_json() or {}
    ward_key = data.get('ward_key')
    bed_id = data.get('bed_id')

    res = hospital_db.complete_bed_cleaning(ward_key, bed_id)
    return jsonify(res)

@app.route('/api/patient/aadhar_lookup', methods=['POST'])
def aadhar_lookup_route():
    """Checks Aadhaar in read-only mode, returns patient identity, true past visits count, and active admission status."""
    data = request.get_json() or {}
    aadhar_no = str(data.get('aadhar_no') or '').replace('-', '').replace(' ', '').strip()

    if len(aadhar_no) != 12 or not aadhar_no.isdigit():
        return jsonify({
            'success': False,
            'error': 'Aadhaar number must be exactly 12 numeric digits.'
        }), 400

    lookup_res = hospital_db.lookup_patient_by_aadhar(aadhar_no)
    patient_id = lookup_res.get('patient_id') or (lookup_res.get('patient', {}).get('_id'))
    adm_info = hospital_db.lookup_patient_active_admission(patient_id) if patient_id else {'is_admitted': False}
    
    return jsonify({
        'success': True,
        'exists': lookup_res.get('exists', False),
        'patient': lookup_res.get('patient'),
        'patient_id': patient_id,
        'masked_aadhar': lookup_res.get('masked_aadhar'),
        'total_past_visits': lookup_res.get('total_past_visits', 0),
        'is_returning': lookup_res.get('is_returning', False),
        'admission_info': adm_info
    })

@app.route('/api/patient/transfer_by_id', methods=['POST'])
def transfer_by_id_route():
    """Directly transfers a patient by Patient ID or Aadhaar without needing to manually search where they are."""
    data = request.get_json() or {}
    query = data.get('query') # Patient ID or Aadhaar
    to_ward = data.get('to_ward')
    to_bed = data.get('to_bed')

    res = hospital_db.transfer_by_patient_id(query, to_ward, to_bed)
    return jsonify(res)

@app.route('/api/patient/discharge_by_id', methods=['POST'])
def discharge_by_id_route():
    """Directly discharges a patient by Patient ID or Aadhaar, freeing their bed and equipment."""
    data = request.get_json() or {}
    query = data.get('query') # Patient ID or Aadhaar

    res = hospital_db.discharge_by_patient_id(query)
    return jsonify(res)

@app.route('/api/triage/evaluate', methods=['POST'])
def evaluate_patient():
    """Evaluates triage score, calculates ESI, and recommends optimal ward & bed."""
    data = request.get_json() or {}
    aadhar_no = str(data.get('aadhar_no') or '').replace('-', '').replace(' ', '').strip()

    if aadhar_no and (len(aadhar_no) != 12 or not aadhar_no.isdigit()):
        return jsonify({
            'success': False,
            'error': 'Aadhaar number must be exactly 12 numeric digits.'
        }), 400

    try:
        triage_result = triage_engine.evaluate_triage(data)
        
        # 1. Add to ED active queue
        add_to_queue = data.get('add_to_queue', True)
        if add_to_queue:
            queue_manager.add_patient(data, triage_result)

        # 2. Identify best available bed in designated ward from MongoDB
        ward_decision = triage_result.get('ward_admission_decision', {})
        w_key = ward_decision.get('ward_key', 'general')

        res = hospital_db.get_resources()
        target_bed_id = None
        if w_key in res.get("wards", {}):
            for b in res["wards"][w_key].get("beds", []):
                if b["status"] == "Available":
                    target_bed_id = b["id"]
                    break
        if not target_bed_id:
            target_bed_id = f"{w_key.upper()[:3]}-01"

        triage_result["recommended_bed_id"] = target_bed_id

        # 3. Log audit entry
        audit_entry = audit_logger.log_triage_decision(
            data, triage_result, 
            clinician_id=data.get('clinician_id', 'RN-TriageStation1')
        )
        
        return jsonify({
            'success': True,
            'triage_result': triage_result,
            'recommended_bed_id': target_bed_id,
            'audit_entry': audit_entry,
            'queue_summary': queue_manager.get_queue_summary(),
            'live_resources': res
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/triage/confirm_admission', methods=['POST'])
def confirm_admission():
    """Locks bed in MongoDB and formally admits patient to designated ward."""
    data = request.get_json() or {}
    patient_data = data.get('patient_data', {})
    triage_result = data.get('triage_result', {})
    ward_name = data.get('ward_name', 'General Ward')
    bed_id = data.get('bed_id')
    doctor_id = data.get('doctor_id', 'DOC-107')

    aadhar_no = str(patient_data.get('aadhar_no') or '').replace('-', '').replace(' ', '').strip()
    if not aadhar_no or len(aadhar_no) != 12 or not aadhar_no.isdigit():
        return jsonify({
            'success': False,
            'error': 'Aadhaar number must be exactly 12 numeric digits.'
        }), 400

    adm_record = hospital_db.save_admission(patient_data, triage_result, ward_name, bed_id, doctor_id)
    return jsonify({'success': True, 'admission': adm_record, 'resources': hospital_db.get_resources()})

@app.route('/api/triage/override', methods=['POST'])
def log_override():
    """Processes and logs a clinician override with mandatory justification."""
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    override_level = data.get('new_level')
    reason_code = data.get('reason_code')
    clinician_id = data.get('clinician_id', 'RN-SeniorTriage')
    notes = data.get('notes', '')
    
    if not reason_code:
        return jsonify({'success': False, 'error': 'Mandatory override justification code required.'}), 400
        
    patient_entry = None
    for p in queue_manager.queue:
        if p['patient_id'] == patient_id:
            patient_entry = p
            break
            
    if not patient_entry:
        return jsonify({'success': False, 'error': f'Patient {patient_id} not found in active queue.'}), 404
        
    old_level = patient_entry['triage_level']
    patient_entry['triage_level'] = int(override_level)
    patient_entry['max_safe_wait'] = queue_manager.SAFE_WAIT_LIMITS.get(int(override_level), 60)
    queue_manager.sort_queue()
    
    triage_result_mock = {
        'final_level': old_level,
        'confidence': patient_entry.get('confidence', 0.8),
        'uncertainty_score': 20.0,
        'safety_escalation_applied': patient_entry.get('safety_escalated', False),
        'safety_escalation_reason': patient_entry.get('safety_escalation_reason'),
        'clinical_drivers': [f"Clinician Override: Changed from ESI {old_level} to ESI {override_level} ({reason_code})"]
    }
    
    audit_entry = audit_logger.log_clinician_override(
        patient_entry, triage_result_mock, {
            'new_level': override_level,
            'reason_code': reason_code,
            'clinician_id': clinician_id,
            'notes': notes
        }
    )
    
    return jsonify({
        'success': True,
        'message': f"Clinician override recorded: ESI {old_level} → ESI {override_level}",
        'audit_entry': audit_entry,
        'queue_summary': queue_manager.get_queue_summary()
    })

# ----------------- 4. QUEUE & SURGE APIS -----------------

@app.route('/api/queue', methods=['GET'])
def get_queue():
    """Returns active waiting queue and telemetry."""
    return jsonify({
        'success': True,
        'queue': queue_manager.queue,
        'summary': queue_manager.get_queue_summary()
    })

@app.route('/api/queue/advance_time', methods=['POST'])
def advance_queue_time():
    """Simulates passage of time (+5 or +15 min)."""
    data = request.get_json() or {}
    minutes = int(data.get('minutes', 5))
    queue_manager.advance_time(minutes)
    return jsonify({
        'success': True,
        'message': f"Advanced waiting queue by {minutes} minutes.",
        'queue': queue_manager.queue,
        'summary': queue_manager.get_queue_summary()
    })

@app.route('/api/queue/update_vitals', methods=['POST'])
def update_patient_vitals():
    """Updates repeat vitals for a waiting patient to check for deterioration."""
    data = request.get_json() or {}
    patient_id = data.get('patient_id')
    vitals = data.get('vitals', {})
    
    updated_patient = queue_manager.update_repeat_vitals(patient_id, vitals, triage_engine)
    if updated_patient:
        return jsonify({
            'success': True,
            'patient': updated_patient,
            'queue_summary': queue_manager.get_queue_summary()
        })
    return jsonify({'success': False, 'error': f'Patient {patient_id} not found.'}), 404

@app.route('/api/surge/toggle', methods=['POST'])
def toggle_surge():
    """Toggles 3x Surge Mode simulation."""
    data = request.get_json() or {}
    active = data.get('active', True)
    surge_sim.is_surge_active = active
    
    if active:
        surge_sim.surge_multiplier = 3.0
        surge_patients = surge_sim.generate_surge_cohort(num_patients=15, is_surge=True)
        for p in surge_patients:
            triage_res = triage_engine.evaluate_triage(p)
            queue_manager.add_patient(p, triage_res)
            audit_logger.log_triage_decision(p, triage_res, clinician_id="RN-SurgeTriagePod")
            
        impact_metrics = surge_sim.simulate_surge_impact()
    else:
        surge_sim.surge_multiplier = 1.0
        impact_metrics = {'surge_level': 'Normal Shift (1.0x baseline)'}
        
    return jsonify({
        'success': True,
        'is_surge_active': surge_sim.is_surge_active,
        'multiplier': surge_sim.surge_multiplier,
        'impact_metrics': impact_metrics,
        'queue': queue_manager.queue,
        'summary': queue_manager.get_queue_summary()
    })

@app.route('/api/benchmarks', methods=['GET'])
def get_benchmarks():
    """Returns list of 20 clinical benchmark scenarios."""
    return jsonify({'success': True, 'cases': CLINICAL_BENCHMARK_CASES})

@app.route('/api/benchmarks/run_all', methods=['POST'])
def run_benchmarks():
    """Runs all 20 clinical benchmark scenarios."""
    summary = run_all_benchmarks(triage_engine)
    return jsonify({'success': True, 'summary': summary})

@app.route('/api/audit/logs', methods=['GET'])
def get_audit_logs():
    """Returns immutable HIPAA/GDPR audit ledger."""
    overrides_only = request.args.get('overrides_only', 'false').lower() == 'true'
    logs = audit_logger.get_recent_logs(limit=40, overrides_only=overrides_only)
    metrics = audit_logger.get_audit_metrics()
    return jsonify({'success': True, 'logs': logs, 'metrics': metrics})

if __name__ == '__main__':
    print("Starting PatientTriage.ai Hospital Management Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)
