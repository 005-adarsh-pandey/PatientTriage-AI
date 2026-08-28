"""
db_mongo.py - MongoDB Database Layer & Hybrid Persistence Engine
Part of PatientTriage.ai Hospital Management Platform
"""

import os
import json
import uuid
import datetime
from datetime import datetime, timezone

# Try importing pymongo, gracefully fallback to in-memory/JSON Mongo-compatible engine
try:
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


class LocalMongoCollection:
    """In-memory & JSON-persisted collection mirroring MongoDB interface."""
    def __init__(self, name, filepath=None):
        self.name = name
        self.filepath = filepath or f"data_{name}.json"
        self.data = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = []

    def _save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error persisting {self.name}: {e}")

    def find(self, query=None):
        if not query:
            return list(self.data)
        results = []
        for doc in self.data:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(doc)
        return results

    def find_one(self, query):
        results = self.find(query)
        return results[0] if results else None

    def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        self.data.append(doc)
        self._save()
        return doc

    def update_one(self, query, update_spec):
        for doc in self.data:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                if "$set" in update_spec:
                    for sk, sv in update_spec["$set"].items():
                        doc[sk] = sv
                self._save()
                return True
        return False

    def count_documents(self, query=None):
        return len(self.find(query))


class HospitalDatabase:
    """
    Central Database Manager supporting real MongoDB server / Atlas connection
    with seamless local JSON persistence fallback.
    """

    def __init__(self, uri=None):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/hospital_db")
        self.is_connected_to_mongo = False
        self.client = None
        self.db = None
        self.connection_info = {"mode": "Local JSON Persistence", "uri": "local_storage", "db_name": "hospital_db"}

        # Attempt connection to MongoDB if URI provided or pymongo available
        self.try_connect(self.uri)

    def try_connect(self, uri):
        """Attempts to connect to a real MongoDB / Atlas instance."""
        if not uri:
            uri = "mongodb://127.0.0.1:27017/hospital_db"
            
        if PYMONGO_AVAILABLE:
            try:
                self.client = MongoClient(uri, serverSelectionTimeoutMS=2500)
                self.client.server_info() # Ping test
                self.uri = uri
                
                # Extract database name or default to hospital_db
                try:
                    db_name = uri.split("/")[-1].split("?")[0]
                    if not db_name or "mongodb" in db_name: db_name = "hospital_db"
                except Exception:
                    db_name = "hospital_db"
                    
                self.db = self.client.get_database(db_name)
                self.is_connected_to_mongo = True
                
                # Assign real MongoDB collections
                self.doctors = self.db["doctors"]
                self.staff = self.db["staff"]
                self.schedules = self.db["schedules"]
                self.patients = self.db["patients"]
                self.hospital_resources = self.db["hospital_resources"]
                self.admissions = self.db["admissions"]
                self.audit_logs = self.db["audit_logs"]

                # Mask URI for display
                masked_uri = uri
                if "@" in uri:
                    prefix = uri.split("@")[0].split("//")[0] + "//"
                    suffix = "@" + uri.split("@")[1]
                    masked_uri = f"{prefix}****:****{suffix}"

                self.connection_info = {
                    "mode": "Real MongoDB Server (Live)",
                    "uri": masked_uri,
                    "db_name": db_name,
                    "is_connected": True
                }
                print(f"CONNECTED TO REAL MONGODB: {masked_uri}")
                self._seed_default_data()
                return {"success": True, "mode": "Real MongoDB Server", "uri": masked_uri, "db_name": db_name}
            except Exception as e:
                self.is_connected_to_mongo = False
                print(f"MongoDB connection failed ({e}). Using persistent local collection layer.")

        # Fallback to local persistent collections
        self.is_connected_to_mongo = False
        self.doctors = LocalMongoCollection("doctors")
        self.staff = LocalMongoCollection("staff")
        self.schedules = LocalMongoCollection("schedules")
        self.patients = LocalMongoCollection("patients")
        self.hospital_resources = LocalMongoCollection("hospital_resources")
        self.admissions = LocalMongoCollection("admissions")
        self.audit_logs = LocalMongoCollection("audit_logs")
        self.connection_info = {
            "mode": "Local JSON Persistence",
            "uri": "Local JSON Files (data_*.json)",
            "db_name": "hospital_db",
            "is_connected": False
        }
        self._seed_default_data()
        return {"success": False, "mode": "Local JSON Persistence", "error": "MongoDB server offline. Active in local JSON storage mode."}

    def _ensure_mongo(self):
        """Ensures that the real MongoDB connection is active and healthy."""
        if not self.is_connected_to_mongo or self.client is None:
            self.try_connect(self.uri)
        else:
            try:
                self.client.admin.command('ping')
            except Exception:
                self.try_connect(self.uri)

    def get_status_info(self):
        """Returns live database status and document counts."""
        self._ensure_mongo()
        return {
            "success": True,
            "mode": self.connection_info.get("mode"),
            "uri": self.connection_info.get("uri"),
            "db_name": self.connection_info.get("db_name"),
            "is_connected_to_mongo": self.is_connected_to_mongo,
            "counts": {
                "patients": self.patients.count_documents({} if self.is_connected_to_mongo else None),
                "admissions": self.admissions.count_documents({} if self.is_connected_to_mongo else None),
                "doctors": self.doctors.count_documents({} if self.is_connected_to_mongo else None),
                "staff": self.staff.count_documents({} if self.is_connected_to_mongo else None),
                "audit_logs": self.audit_logs.count_documents({} if self.is_connected_to_mongo else None)
            }
        }

    def _seed_default_data(self):
        """Pre-seeds default doctors, staff, wards, and equipment if empty."""
        # 1. Seed Doctors
        if self.doctors.count_documents({}) == 0:
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
            for d in doctors_list:
                self.doctors.insert_one(d)

        # 2. Seed Staff
        if self.staff.count_documents({}) == 0:
            staff_list = [
                {"_id": "STF-201", "name": "Sister Kavita Nair", "role": "Senior Triage Nurse", "assigned_ward": "Emergency Triage", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
                {"_id": "STF-202", "name": "Sister Sunita Rao", "role": "ICU Staff Nurse", "assigned_ward": "Adult ICU", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
                {"_id": "STF-203", "name": "Sister Deepa Kumari", "role": "NICU Specialist Nurse", "assigned_ward": "NICU", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"},
                {"_id": "STF-204", "name": "Ramesh Yadav", "role": "Ward Boy / Patient Transport", "assigned_ward": "General Ward & ER", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
                {"_id": "STF-205", "name": "Suresh Paswan", "role": "Housekeeping / Sanitization Staff", "assigned_ward": "Operation Theatres", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
                {"_id": "STF-206", "name": "Mohan Lal", "role": "Housekeeping / Ward Cleaning", "assigned_ward": "ICU & HDU", "shift": "Morning (07:00 - 15:00)", "status": "Available"},
                {"_id": "STF-207", "name": "Sister Pooja Sen", "role": "Dialysis Technician & Nurse", "assigned_ward": "Dialysis Center", "shift": "Morning (07:00 - 15:00)", "status": "On-Duty"}
            ]
            for s in staff_list:
                self.staff.insert_one(s)

        # 3. Seed Hospital Resources (Wards, Equipment, OTs)
        if self.hospital_resources.count_documents({"_id": "MAIN_HOSPITAL_RESOURCES"}) == 0:
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
                        "total_beds": 12,
                        "occupied_beds": 8,
                        "target_esi": [1, 2],
                        "beds": [{"id": f"ICU-{i:02d}", "status": "Occupied" if i <= 8 else "Available", "ventilator": f"VENT-{i}" if i <= 8 else None} for i in range(1, 13)]
                    },
                    "nicu": {
                        "name": "Neonatal ICU (NICU - Newborns <28 Days)",
                        "total_beds": 8,
                        "occupied_beds": 4,
                        "target_esi": [1, 2],
                        "beds": [{"id": f"NICU-{i:02d}", "status": "Occupied" if i <= 4 else "Available", "incubator": f"INC-{i}"} for i in range(1, 9)]
                    },
                    "picu": {
                        "name": "Pediatric ICU (PICU - Children 1m to 16y)",
                        "total_beds": 6,
                        "occupied_beds": 3,
                        "target_esi": [1, 2],
                        "beds": [{"id": f"PICU-{i:02d}", "status": "Occupied" if i <= 3 else "Available"} for i in range(1, 7)]
                    },
                    "dialysis": {
                        "name": "Hemodialysis & Nephrology Unit",
                        "total_beds": 6,
                        "occupied_beds": 4,
                        "target_esi": [2, 3],
                        "beds": [{"id": f"DIA-{i:02d}", "status": "Occupied" if i <= 4 else "Available", "machine": f"DIA-MACH-{i}"} for i in range(1, 7)]
                    },
                    "fast_track": {
                        "name": "Outpatient Fast-Track / Minor Injury Pods",
                        "total_beds": 10,
                        "occupied_beds": 5,
                        "target_esi": [4, 5],
                        "beds": [{"id": f"FT-{i:02d}", "status": "Occupied" if i <= 5 else "Available"} for i in range(1, 11)]
                    }
                },
                "medical_equipment": {
                    "dialysis_machines": {"total": 6, "in_use": 4, "available": 2},
                    "oxygen_cylinders": {"full_stock": 50, "in_use": 32, "available": 18, "central_pressure_psi": 142},
                    "ventilators": {"total": 16, "in_use": 11, "available": 5},
                    "defibrillators": {"total": 8, "available": 8}
                },
                "operation_theatres": [
                    {"ot_id": "OT-1", "name": "Emergency Trauma OT", "status": "Reserved_Emergency", "current_surgeon": "Dr. Sneha Patel", "case": "Standby for Trauma Influx"},
                    {"ot_id": "OT-2", "name": "Cardiac Surgery Complex", "status": "In_Surgery", "current_surgeon": "Dr. Rajesh Sharma", "case": "CABG (Expected End: 18:00)"},
                    {"ot_id": "OT-3", "name": "General Laparoscopic OT", "status": "Available", "current_surgeon": None, "case": None},
                    {"ot_id": "OT-4", "name": "Orthopedic & Neuro OT", "status": "Under_Sterilization", "current_surgeon": None, "case": "Cleaning (15m remaining)"}
                ]
            }
            self.hospital_resources.insert_one(res_doc)

    # ----------------- DB API Methods -----------------
    def get_doctors(self):
        self._ensure_mongo()
        return self.doctors.find()

    def get_staff(self):
        self._ensure_mongo()
        return self.staff.find()

    def get_resources(self):
        self._ensure_mongo()
        doc = self.hospital_resources.find_one({"_id": "MAIN_HOSPITAL_RESOURCES"})
        return doc or {}

    def update_doctor_leave(self, doctor_id, on_leave=True, reason="Medical Leave", backup_id=None):
        doc = self.doctors.find_one({"_id": doctor_id})
        if doc:
            new_status = "On-Leave" if on_leave else "Available"
            substitute = backup_id or doc.get("backup_id", "DOC-107")
            self.doctors.update_one(
                {"_id": doctor_id},
                {"$set": {"status": new_status, "on_leave": on_leave, "leave_reason": reason, "substitute_id": substitute}}
            )
            # Record audit
            self.audit_logs.insert_one({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "DOCTOR_LEAVE_UPDATE",
                "doctor_id": doctor_id,
                "status": new_status,
                "reason": reason,
                "backup_assigned": substitute
            })
            return {"success": True, "doctor": doc["name"], "status": new_status, "substitute": substitute}
        return {"success": False, "error": "Doctor not found"}

    def update_bed_status(self, ward_key, bed_id, new_status, patient_id=None):
        res = self.get_resources()
        if ward_key in res.get("wards", {}):
            ward = res["wards"][ward_key]
            for b in ward.get("beds", []):
                if b["id"] == bed_id:
                    old_status = b["status"]
                    b["status"] = new_status
                    b["patient"] = patient_id if new_status == "Occupied" else None
                    # Update occupied count
                    occ = sum(1 for item in ward["beds"] if item["status"] == "Occupied")
                    ward["occupied_beds"] = occ
                    self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"wards": res["wards"]}})
                    return {"success": True, "ward": ward_key, "bed_id": bed_id, "status": new_status, "occupied_beds": occ}
        return {"success": False, "error": f"Bed {bed_id} not found in ward {ward_key}"}

    def empty_all_beds(self):
        """Empties every hospital bed across all wards in MongoDB."""
        res = self.get_resources()
        wards = res.get("wards", {})
        total_beds = 0

        for wk, w in wards.items():
            w["occupied_beds"] = 0
            for b in w.get("beds", []):
                b["status"] = "Available"
                b["patient"] = None
                total_beds += 1

        eq = res.get("medical_equipment", {})
        if "oxygen_cylinders" in eq:
            eq["oxygen_cylinders"]["in_use"] = 0
            eq["oxygen_cylinders"]["available"] = eq["oxygen_cylinders"].get("full_stock", 50)
        if "dialysis_machines" in eq:
            eq["dialysis_machines"]["in_use"] = 0
            eq["dialysis_machines"]["available"] = eq["dialysis_machines"].get("total", 6)
        if "ventilators" in eq:
            eq["ventilators"]["in_use"] = 0
            eq["ventilators"]["available"] = eq["ventilators"].get("total", 16)

        ots = res.get("operation_theatres", [])
        for ot in ots:
            ot["status"] = "Available"
            ot["case"] = "Ready for emergency surgical case"

        self.hospital_resources.update_one(
            {"_id": "MAIN_HOSPITAL_RESOURCES"},
            {"$set": {"wards": wards, "medical_equipment": eq, "operation_theatres": ots}}
        )

        if self.is_connected_to_mongo:
            self.admissions.update_many(
                {"status": "ADMITTED_ACTIVE"},
                {"$set": {"status": "DISCHARGED", "discharge_timestamp": datetime.now(timezone.utc).isoformat()}}
            )
        else:
            for adm in self.admissions.find():
                if adm.get("status") == "ADMITTED_ACTIVE":
                    adm["status"] = "DISCHARGED"
            self.admissions._save()

        self.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "HOSPITAL_ALL_BEDS_EMPTIED",
            "total_beds": total_beds,
            "details": f"All {total_beds} beds emptied and reset to Available."
        })

        return {"success": True, "total_beds": total_beds, "message": f"All {total_beds} hospital beds are now 100% vacant and Available."}

    def update_equipment(self, eq_type, delta_in_use=0, new_pressure_psi=None):
        res = self.get_resources()
        eq = res.get("medical_equipment", {})
        if eq_type in eq:
            item = eq[eq_type]
            tot = item.get("total", item.get("total_stock", item.get("full_stock", 50)))
            item["full_stock"] = tot
            item["total_stock"] = tot
            item["total"] = tot
            if "in_use" in item:
                item["in_use"] = max(0, min(tot, item["in_use"] + delta_in_use))
                item["available"] = max(0, tot - item["in_use"])
            if new_pressure_psi is not None and "central_pressure_psi" in item:
                item["central_pressure_psi"] = int(new_pressure_psi)
            self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"medical_equipment": eq}})
            return {"success": True, "equipment": item}
        return {"success": False, "error": "Equipment not found"}

    def update_ot_status(self, ot_id, new_status, surgeon=None, case_info=None):
        res = self.get_resources()
        ots = res.get("operation_theatres", [])
        for ot in ots:
            if ot["ot_id"] == ot_id:
                ot["status"] = new_status
                if surgeon is not None: ot["current_surgeon"] = surgeon
                if case_info is not None: ot["case"] = case_info
                self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"operation_theatres": ots}})
                return {"success": True, "ot": ot}
    def save_admission(self, patient_data, triage_result, assigned_ward, assigned_bed_id=None, doctor_id="DOC-107"):
        self._ensure_mongo()
        aadhar_no = patient_data.get("aadhar_no")
        pat_doc = self.register_or_update_patient_on_admit(
            aadhar_no,
            name=patient_data.get("name") or patient_data.get("patient_name"),
            age=patient_data.get("patient_age"),
            gender=patient_data.get("patient_gender"),
            phone=patient_data.get("phone")
        )
        patient_id = pat_doc["_id"]

        doc = {
            "_id": f"ADM-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patient_id": patient_id,
            "patient_name": pat_doc.get("name", f"Patient {patient_id}"),
            "aadhar_no": pat_doc.get("aadhar_no"),
            "masked_aadhar": pat_doc.get("masked_aadhar"),
            "age": patient_data.get("patient_age", 35),
            "gender": patient_data.get("patient_gender", "Female"),
            "chief_complaint": patient_data.get("chief_complaint", "General"),
            "vitals": {
                "heart_rate": patient_data.get("heart_rate", 75),
                "resp_rate": patient_data.get("resp_rate", 16),
                "sbp": patient_data.get("sbp", 120),
                "dbp": patient_data.get("dbp", 80),
                "spo2": patient_data.get("spo2", 98.0),
                "temp_c": patient_data.get("temp_c", 37.0),
                "pain_score": patient_data.get("pain_score", 0)
            },
            "triage_level": triage_result.get("final_level", 3),
            "acuity_name": triage_result.get("level_name", "Urgent"),
            "assigned_ward": assigned_ward,
            "assigned_bed_id": assigned_bed_id,
            "attending_doctor_id": doctor_id,
            "admission_risk_percent": triage_result.get("admission_risk_percent", 25),
            "status": "ADMITTED_ACTIVE"
        }
        self.admissions.insert_one(doc)
        
        # Lock bed if assigned
        if assigned_bed_id:
            w_key = "general"
            res = self.get_resources()
            for wk, w in res.get("wards", {}).items():
                for b in w.get("beds", []):
                    if b["id"] == assigned_bed_id:
                        w_key = wk
                        break
            self.update_bed_status(w_key, assigned_bed_id, "Occupied", patient_id)

        return doc

    def transfer_patient(self, patient_id, from_ward_key, from_bed_id, to_ward_key, to_bed_id, new_doctor_id=None):
        """
        Transfers a patient (e.g., Step-Down from ICU to General Ward).
        - Deallocates old bed (marks Under_Cleaning)
        - Frees attached equipment (e.g. Ventilator)
        - Allocates new bed (marks Occupied)
        - Updates patient admission document & logs audit event
        """
        res = self.get_resources()
        wards = res.get("wards", {})
        
        # 1. Release old bed
        if from_ward_key in wards:
            for b in wards[from_ward_key].get("beds", []):
                if b["id"] == from_bed_id:
                    b["status"] = "Under_Cleaning"
                    b["patient"] = None
                    if "ventilator" in b and b["ventilator"]:
                        # Return ventilator to pool
                        self.update_equipment("ventilators", delta_in_use=-1)
            wards[from_ward_key]["occupied_beds"] = max(0, sum(1 for item in wards[from_ward_key]["beds"] if item["status"] == "Occupied"))

        # 2. Lock new bed
        if to_ward_key in wards:
            for b in wards[to_ward_key].get("beds", []):
                if b["id"] == to_bed_id:
                    b["status"] = "Occupied"
                    b["patient"] = patient_id
            wards[to_ward_key]["occupied_beds"] = sum(1 for item in wards[to_ward_key]["beds"] if item["status"] == "Occupied")

        self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"wards": wards}})

        # 3. Update Admission Record
        adm = self.admissions.find_one({"patient_id": patient_id})
        if adm:
            self.admissions.update_one(
                {"patient_id": patient_id},
                {"$set": {
                    "assigned_ward": wards.get(to_ward_key, {}).get("name", to_ward_key),
                    "assigned_bed_id": to_bed_id,
                    "attending_doctor_id": new_doctor_id or adm.get("attending_doctor_id")
                }}
            )

        # 4. Audit Log
        self.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "PATIENT_WARD_TRANSFER",
            "patient_id": patient_id,
            "from_ward": from_ward_key,
            "from_bed": from_bed_id,
            "to_ward": to_ward_key,
            "to_bed": to_bed_id,
            "transferred_by": "RN-WardSupervisor"
        })

        return {"success": True, "message": f"Patient {patient_id} transferred from {from_bed_id} to {to_bed_id}. Old bed queued for sanitization."}

    def discharge_patient(self, patient_id, ward_key, bed_id):
        """
        Discharges a patient completely from the hospital after validating active admission.
        - Verifies patient is currently admitted to the specified bed
        - Deallocates bed (marks Under_Cleaning)
        - Frees attached equipment (Ventilator, O2, Dialysis)
        - Updates admission status to DISCHARGED
        - Logs audit event
        """
        if not patient_id or patient_id == "None":
            return {"success": False, "error": "Cannot discharge: No patient is assigned to this bed."}

        res = self.get_resources()
        wards = res.get("wards", {})

        if ward_key not in wards:
            return {"success": False, "error": f"Ward '{ward_key}' not found."}

        target_bed = next((b for b in wards[ward_key].get("beds", []) if b["id"] == bed_id), None)
        if not target_bed:
            return {"success": False, "error": f"Bed '{bed_id}' not found in ward '{ward_key}'."}

        if target_bed.get("status") != "Occupied":
            return {"success": False, "error": f"Cannot discharge: Bed {bed_id} is currently '{target_bed.get('status')}', not occupied by an admitted patient."}

        # 1. Release Bed
        target_bed["status"] = "Under_Cleaning"
        target_bed["patient"] = None
        if "ventilator" in target_bed and target_bed["ventilator"]:
            self.update_equipment("ventilators", delta_in_use=-1)

        wards[ward_key]["occupied_beds"] = max(0, sum(1 for item in wards[ward_key]["beds"] if item["status"] == "Occupied"))
        self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"wards": wards}})

        # 2. Mark Admission Record Discharged
        if self.is_connected_to_mongo:
            self.admissions.update_many(
                {"patient_id": patient_id, "status": "ADMITTED_ACTIVE"},
                {"$set": {
                    "status": "DISCHARGED",
                    "discharge_timestamp": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            for adm in self.admissions.find():
                if adm.get("patient_id") == patient_id and adm.get("status") == "ADMITTED_ACTIVE":
                    adm["status"] = "DISCHARGED"
                    adm["discharge_timestamp"] = datetime.now(timezone.utc).isoformat()
            self.admissions._save()

        # 3. Audit Log
        self.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "PATIENT_DISCHARGE",
            "patient_id": patient_id,
            "ward": ward_key,
            "bed_id": bed_id,
            "discharged_by": "Physician-DischargeLead"
        })

        return {"success": True, "message": f"Patient discharged successfully. Bed {bed_id} is now queued for sanitization."}

    def complete_bed_cleaning(self, ward_key, bed_id):
        """Marks a cleaned bed as Available."""
        return self.update_bed_status(ward_key, bed_id, "Available")



    # ----------------- AADHAAR & ID-BASED PATIENT MANAGEMENT -----------------

    def lookup_patient_by_aadhar(self, aadhar_no):
        """
        Pure READ-ONLY lookup. Does NOT insert or mutate anything.
        - Requires exactly 12 numeric digits.
        - If Aadhaar is in DB: returns exists=True, patient profile, and true visit count.
        - If Aadhaar is NOT in DB: returns exists=False, deterministic UHID, and visit_count=0.
        """
        self._ensure_mongo()
        clean_aadhar = str(aadhar_no or '').replace('-', '').replace(' ', '').strip()
        if len(clean_aadhar) != 12 or not clean_aadhar.isdigit():
            return {
                "success": False,
                "exists": False,
                "error": "Aadhaar number must be exactly 12 numeric digits.",
                "patient_id": None,
                "total_past_visits": 0,
                "masked_aadhar": "XXXX-XXXX-XXXX"
            }

        masked_aadhar = f"XXXX-XXXX-{clean_aadhar[-4:]}"
        patient_id = f"PT-{clean_aadhar[-4:]}-{clean_aadhar[:4]}"

        # Search existing patient in database
        existing_patient = self.patients.find_one({"aadhar_no": clean_aadhar})
        if not existing_patient:
            existing_patient = self.patients.find_one({"_id": patient_id})

        if existing_patient:
            return {
                "exists": True,
                "patient": existing_patient,
                "patient_id": existing_patient["_id"],
                "masked_aadhar": existing_patient.get("masked_aadhar", masked_aadhar),
                "total_past_visits": existing_patient.get("total_past_visits", 1),
                "is_returning": True
            }
        else:
            return {
                "exists": False,
                "patient": None,
                "patient_id": patient_id,
                "masked_aadhar": masked_aadhar,
                "total_past_visits": 0,
                "is_returning": False
            }

    def register_or_update_patient_on_admit(self, aadhar_no, name=None, age=None, gender=None, phone=None):
        """
        Idempotently registers a patient in the database upon hospital intake / bed lock.
        - If Aadhaar exists: increments total past visits counter.
        - If new: creates permanent record.
        """
        self._ensure_mongo()
        clean_aadhar = str(aadhar_no).replace('-', '').replace(' ', '').strip()
        if not clean_aadhar or len(clean_aadhar) < 4:
            clean_aadhar = f"TMP{uuid.uuid4().hex[:8]}"

        masked_aadhar = f"XXXX-XXXX-{clean_aadhar[-4:]}"
        patient_id = f"PT-{clean_aadhar[-4:]}-{clean_aadhar[:4]}"

        existing = self.patients.find_one({"aadhar_no": clean_aadhar})
        if not existing:
            existing = self.patients.find_one({"_id": patient_id})

        if existing:
            v_count = existing.get("total_past_visits", 1) + 1
            self.patients.update_one(
                {"_id": existing["_id"]},
                {"$set": {"total_past_visits": v_count, "has_prior_history": True}}
            )
            existing["total_past_visits"] = v_count
            return existing
        else:
            new_doc = {
                "_id": patient_id,
                "patient_id": patient_id,
                "aadhar_no": clean_aadhar,
                "masked_aadhar": masked_aadhar,
                "name": name or f"Patient {patient_id}",
                "age": float(age) if age else 40.0,
                "gender": gender or "Female",
                "phone": phone or "+91-9876543210",
                "has_prior_history": False,
                "total_past_visits": 1,
                "chronic_conditions": [],
                "allergies": [],
                "registered_at": datetime.now(timezone.utc).isoformat()
            }
            self.patients.insert_one(new_doc)
            return new_doc

    def lookup_patient_active_admission(self, query):
        """
        Finds a patient and their exact active bed/ward by Aadhaar or Patient ID.
        """
        clean_q = str(query).replace('-', '').replace(' ', '').strip()
        
        # 1. Search in Patients
        patient = None
        for p in self.patients.find():
            if p.get("aadhar_no") == clean_q or clean_q in p.get("_id", "") or clean_q.lower() in p.get("name", "").lower():
                patient = p
                break

        patient_id = patient.get("_id") if patient else query

        # 2. Search Active Admission
        active_adm = None
        for adm in self.admissions.find():
            if adm.get("patient_id") == patient_id and adm.get("status") == "ADMITTED_ACTIVE":
                active_adm = adm
                break

        # 3. Locate exact bed in hospital resources
        current_ward = None
        current_bed_id = None
        res = self.get_resources()
        for wk, w in res.get("wards", {}).items():
            for b in w.get("beds", []):
                if b.get("patient") == patient_id and b.get("status") == "Occupied":
                    current_ward = wk
                    current_bed_id = b.get("id")
                    break

        is_admitted = (current_bed_id is not None) or (active_adm is not None)

        return {
            "success": True,
            "patient": patient or {"_id": patient_id, "name": f"Patient {patient_id}"},
            "active_admission": active_adm,
            "current_ward_key": current_ward or (active_adm.get("assigned_ward") if active_adm else None),
            "current_bed_id": current_bed_id or (active_adm.get("assigned_bed_id") if active_adm else None),
            "is_admitted": is_admitted
        }

    def transfer_by_patient_id(self, query, to_ward_key, to_bed_id=None):
        """
        Direct 1-Click Transfer: Finds where patient is admitted, deallocates old bed, and locks target bed.
        """
        lookup = self.lookup_patient_active_admission(query)
        if not lookup["is_admitted"]:
            return {"success": False, "error": f"Patient is not currently admitted to any bed. Transfer cannot be performed."}

        patient_id = lookup["patient"]["_id"]
        from_ward = lookup["current_ward_key"]
        from_bed = lookup["current_bed_id"]

        # Auto-pick available bed in target ward if not specified
        res = self.get_resources()
        if not to_bed_id and to_ward_key in res.get("wards", {}):
            for b in res["wards"][to_ward_key].get("beds", []):
                if b["status"] == "Available":
                    to_bed_id = b["id"]
                    break
        if not to_bed_id:
            to_bed_id = f"{to_ward_key.upper()[:3]}-AUTO"

        return self.transfer_patient(patient_id, from_ward, from_bed, to_ward_key, to_bed_id)

    def discharge_by_patient_id(self, query):
        """
        Direct 1-Click Discharge: Validates patient is currently admitted, frees active bed to Under_Cleaning, and returns equipment.
        """
        lookup = self.lookup_patient_active_admission(query)
        if not lookup.get("is_admitted"):
            return {
                "success": False,
                "error": "Patient is not currently admitted to any hospital bed or ward. Discharge cannot be processed."
            }

        patient = lookup.get("patient")
        patient_id = patient["_id"] if patient else query

        res = self.get_resources()
        wards = res.get("wards", {})
        freed_beds = []

        # Find and free any bed occupied by this patient across all wards
        for wk, w in wards.items():
            for b in w.get("beds", []):
                if b.get("patient") == patient_id and b.get("status") == "Occupied":
                    b["status"] = "Under_Cleaning"
                    b["patient"] = None
                    freed_beds.append(b['id'])
                    if "ventilator" in b and b["ventilator"]:
                        self.update_equipment("ventilators", delta_in_use=-1)
            w["occupied_beds"] = max(0, sum(1 for item in w.get("beds", []) if item["status"] == "Occupied"))

        self.hospital_resources.update_one({"_id": "MAIN_HOSPITAL_RESOURCES"}, {"$set": {"wards": wards}})

        # Mark all active admissions for this patient as DISCHARGED
        if self.is_connected_to_mongo:
            self.admissions.update_many(
                {"patient_id": patient_id, "status": "ADMITTED_ACTIVE"},
                {"$set": {
                    "status": "DISCHARGED",
                    "discharge_timestamp": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            for adm in self.admissions.find():
                if adm.get("patient_id") == patient_id and adm.get("status") == "ADMITTED_ACTIVE":
                    adm["status"] = "DISCHARGED"
                    adm["discharge_timestamp"] = datetime.now(timezone.utc).isoformat()
            self.admissions._save()

        # Audit Log
        self.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "PATIENT_DISCHARGE",
            "patient_id": patient_id,
            "freed_beds": freed_beds,
            "discharged_by": "Physician-DischargeLead"
        })

        bed_msg = f"Bed {freed_beds[0]}" if freed_beds else "Admission record"
        return {"success": True, "message": f"Patient discharged successfully. {bed_msg} is now marked for sanitization."}


# Global singleton instance
hospital_db = HospitalDatabase()
