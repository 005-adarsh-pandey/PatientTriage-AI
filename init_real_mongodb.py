"""
init_real_mongodb.py - Initializes and seeds the complete hospital_db database in MongoDB Compass
"""
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timezone

def initialize_mongodb():
    print("Connecting to MongoDB at mongodb://127.0.0.1:27017/ ...")
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=4000)
    db = client["hospital_db"]

    print("Initializing Collections & Indexes in 'hospital_db'...")

    # 1. Patients Collection
    col_patients = db["patients"]
    col_patients.create_index([("aadhar_no", ASCENDING)], unique=False)
    col_patients.create_index([("patient_id", ASCENDING)], unique=True)

    # 2. Admissions Collection
    col_admissions = db["admissions"]
    col_admissions.create_index([("patient_id", ASCENDING)])
    col_admissions.create_index([("status", ASCENDING)])
    col_admissions.create_index([("assigned_bed_id", ASCENDING)])

    # 3. Doctors Collection
    col_doctors = db["doctors"]
    if col_doctors.count_documents({}) == 0:
        doctors_list = [
            {"_id": "DOC-101", "name": "Dr. Rajesh Sharma", "specialty": "Cardiology", "qualifications": "MD, DM (Cardio)", "room": "OPD-12", "phone": "+91-9876543210", "status": "Available", "backup_id": "DOC-107"},
            {"_id": "DOC-102", "name": "Dr. Ananya Iyer", "specialty": "Pediatrics & Neonatology", "qualifications": "MD (Peds), Fellowship NICU", "room": "NICU Suite", "phone": "+91-9876543211", "status": "Available", "backup_id": "DOC-108"},
            {"_id": "DOC-103", "name": "Dr. Vikram Sethi", "specialty": "Critical Care & ICU (Intensivist)", "qualifications": "MD, EDIC (Critical Care)", "room": "ICU Control", "phone": "+91-9876543212", "status": "Available", "backup_id": "DOC-107"},
            {"_id": "DOC-104", "name": "Dr. Sneha Patel", "specialty": "Trauma & Orthopedic Surgery", "qualifications": "MS (Ortho), MCh (Trauma)", "room": "OT-1 Complex", "phone": "+91-9876543213", "status": "Available", "backup_id": "DOC-106"},
            {"_id": "DOC-105", "name": "Dr. Farhan Qureshi", "specialty": "Nephrology & Dialysis", "qualifications": "MD, DM (Nephrology)", "room": "Dialysis Ward", "phone": "+91-9876543214", "status": "Available", "backup_id": "DOC-101"},
            {"_id": "DOC-106", "name": "Dr. Priya Deshmukh", "specialty": "General & Laparoscopic Surgery", "qualifications": "MS, FMAS", "room": "OT-3 Complex", "phone": "+91-9876543215", "status": "Available", "backup_id": "DOC-104"},
            {"_id": "DOC-107", "name": "Dr. Amit Roy", "specialty": "Emergency Medicine (Lead)", "qualifications": "MD (Emergency Medicine)", "room": "Triage Command", "phone": "+91-9876543216", "status": "Available", "backup_id": "DOC-103"},
            {"_id": "DOC-108", "name": "Dr. Meera Nambiar", "specialty": "General Medicine & Sepsis", "qualifications": "MD (Internal Medicine)", "room": "Ward Area A", "phone": "+91-9876543217", "status": "Available", "backup_id": "DOC-102"}
        ]
        col_doctors.insert_many(doctors_list)
        print("  -> Inserted 8 Specialists into 'doctors' collection.")

    # 4. Staff Collection
    col_staff = db["staff"]
    if col_staff.count_documents({}) == 0:
        staff_list = [
            {"_id": "STF-201", "name": "Sister Kavita Nair", "role": "Senior Triage Nurse", "assigned_ward": "Emergency Triage", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
            {"_id": "STF-202", "name": "Sister Sunita Rao", "role": "ICU Staff Nurse", "assigned_ward": "Adult ICU", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
            {"_id": "STF-203", "name": "Sister Deepa Kumari", "role": "NICU Specialist Nurse", "assigned_ward": "NICU", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
            {"_id": "STF-204", "name": "Ramesh Yadav", "role": "Ward Boy / Patient Transport", "assigned_ward": "General Ward & ER", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
            {"_id": "STF-205", "name": "Suresh Paswan", "role": "Housekeeping / Sanitization Staff", "assigned_ward": "Operation Theatres", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
            {"_id": "STF-206", "name": "Mohan Lal", "role": "Housekeeping / Ward Cleaning", "assigned_ward": "ICU & HDU", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
            {"_id": "STF-207", "name": "Sister Pooja Sen", "role": "Dialysis Technician & Nurse", "assigned_ward": "Dialysis Center", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"}
        ]
        col_staff.insert_many(staff_list)
        print("  -> Inserted 7 Clinical & Support Staff into 'staff' collection.")

    # 5. Hospital Resources (Wards, 82 Beds, Equipment, OTs)
    col_resources = db["hospital_resources"]
    if col_resources.count_documents({"_id": "MAIN_HOSPITAL_RESOURCES"}) == 0:
        res_doc = {
            "_id": "MAIN_HOSPITAL_RESOURCES",
            "hospital_name": "Metro General Hospital & Research Institute",
            "tier": "Level-1 Trauma & Super-Specialty Medical Center",
            "wards": {
                "general": {
                    "name": "General Ward (Male/Female)",
                    "total_beds": 30,
                    "occupied_beds": 18,
                    "target_esi": [3, 4],
                    "beds": [{"id": f"GEN-{i:02d}", "status": "Occupied" if i <= 18 else "Available", "patient": f"PT-G{i}" if i <= 18 else None} for i in range(1, 31)]
                },
                "semi_private": {
                    "name": "Semi-Private & Private Rooms",
                    "total_beds": 16,
                    "occupied_beds": 10,
                    "target_esi": [3, 4],
                    "beds": [{"id": f"PVT-{i:02d}", "status": "Occupied" if i <= 10 else "Available", "patient": f"PT-P{i}" if i <= 10 else None} for i in range(1, 17)]
                },
                "hdu": {
                    "name": "High Dependency Unit (HDU / Cardiac Telemetry)",
                    "total_beds": 10,
                    "occupied_beds": 6,
                    "target_esi": [2, 3],
                    "beds": [{"id": f"HDU-{i:02d}", "status": "Occupied" if i <= 6 else "Available", "patient": f"PT-H{i}" if i <= 6 else None} for i in range(1, 11)]
                },
                "icu": {
                    "name": "Adult Intensive Care Unit (ICU)",
                    "total_beds": 8,
                    "occupied_beds": 5,
                    "target_esi": [1, 2],
                    "beds": [{"id": f"ICU-{i:02d}", "status": "Occupied" if i <= 5 else "Available", "ventilator": True if i <= 3 else False, "patient": f"PT-I{i}" if i <= 5 else None} for i in range(1, 9)]
                },
                "nicu": {
                    "name": "Neonatal ICU (NICU - Newborn Care)",
                    "total_beds": 6,
                    "occupied_beds": 4,
                    "target_esi": [1, 2],
                    "beds": [{"id": f"NICU-{i:02d}", "status": "Occupied" if i <= 4 else "Available", "incubator": True, "patient": f"PT-N{i}" if i <= 4 else None} for i in range(1, 7)]
                },
                "picu": {
                    "name": "Pediatric ICU (PICU)",
                    "total_beds": 4,
                    "occupied_beds": 2,
                    "target_esi": [1, 2],
                    "beds": [{"id": f"PICU-{i:02d}", "status": "Occupied" if i <= 2 else "Available", "patient": f"PT-P{i}" if i <= 2 else None} for i in range(1, 5)]
                },
                "dialysis": {
                    "name": "Dialysis & Nephrology Ward",
                    "total_beds": 4,
                    "occupied_beds": 2,
                    "target_esi": [2, 3],
                    "beds": [{"id": f"DIA-{i:02d}", "status": "Occupied" if i <= 2 else "Available", "dialysis_machine": True, "patient": f"PT-D{i}" if i <= 2 else None} for i in range(1, 5)]
                },
                "fast_track": {
                    "name": "Outpatient Fast-Track / Minor Injury Pod",
                    "total_beds": 4,
                    "occupied_beds": 1,
                    "target_esi": [4, 5],
                    "beds": [{"id": f"FT-{i:02d}", "status": "Occupied" if i <= 1 else "Available", "patient": f"PT-F{i}" if i <= 1 else None} for i in range(1, 5)]
                }
            },
            "medical_equipment": {
                "oxygen_cylinders": { "total_stock": 50, "in_use": 32, "available": 18, "central_pressure_psi": 142, "unit": "D-Type 47L Jumbo Cylinders" },
                "dialysis_machines": { "total": 6, "in_use": 4, "available": 2, "model": "Fresenius 4008S High-Flux" },
                "ventilators": { "total": 16, "in_use": 11, "available": 5, "model": "Hamilton-C6 ICU Invasive" }
            },
            "operation_theatres": [
                { "ot_id": "OT-1", "name": "Emergency Trauma OT-1", "status": "Available", "current_surgeon": "Dr. Sneha Patel", "case": "Standby for incoming major trauma" },
                { "ot_id": "OT-2", "name": "General & Laparoscopy OT-2", "status": "In_Surgery", "current_surgeon": "Dr. Priya Deshmukh", "case": "Emergency Laparotomy (Perforation)" },
                { "ot_id": "OT-3", "name": "Orthopedic Surgery OT-3", "status": "Available", "current_surgeon": "None", "case": "Open for scheduled/emergency fixations" },
                { "ot_id": "OT-4", "name": "Cardiac Catheterization Lab (Cath Lab)", "status": "Reserved_Emergency", "current_surgeon": "Dr. Rajesh Sharma", "case": "Primary PCI on 15-min standby" }
            ]
        }
        col_resources.insert_one(res_doc)
        print("  -> Inserted 8 Wards (82 Beds), Oxygen/Ventilator Stock, and 4 OTs into 'hospital_resources'.")

    # 6. Audit Logs Collection
    col_audit = db["audit_logs"]
    if col_audit.count_documents({}) == 0:
        col_audit.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "MONGODB_SCHEMA_INITIALIZED",
            "details": "MongoDB database 'hospital_db' provisioned with 6 clinical collections.",
            "sha256_seal": "INITIAL_GENESIS_BLOCK_00000000000000000000"
        })
        print("  -> Initialized 'audit_logs' collection with genesis block.")

    print("\nSUCCESS: All 6 collections successfully created in MongoDB 'hospital_db'!")
    print("Databases in Compass now:", client.list_database_names())
    print("Collections in 'hospital_db':", db.list_collection_names())

if __name__ == "__main__":
    initialize_mongodb()
