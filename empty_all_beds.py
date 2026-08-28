"""
empty_all_beds.py - Empties every hospital bed across all wards in MongoDB hospital_db
"""
from pymongo import MongoClient
from datetime import datetime, timezone

def empty_all_hospital_beds():
    print("Connecting to MongoDB at mongodb://127.0.0.1:27017/hospital_db ...")
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=3000)
    db = client["hospital_db"]

    res_doc = db.hospital_resources.find_one({"_id": "MAIN_HOSPITAL_RESOURCES"})
    if not res_doc:
        print("Error: MAIN_HOSPITAL_RESOURCES document not found.")
        return

    wards = res_doc.get("wards", {})
    total_beds_count = 0

    # 1. Reset every bed in every ward to "Available"
    for wk, w in wards.items():
        w["occupied_beds"] = 0
        for b in w.get("beds", []):
            b["status"] = "Available"
            b["patient"] = None
            total_beds_count += 1

    # 2. Reset in-use medical equipment
    eq = res_doc.get("medical_equipment", {})
    if "oxygen_cylinders" in eq:
        eq["oxygen_cylinders"]["in_use"] = 0
        eq["oxygen_cylinders"]["available"] = eq["oxygen_cylinders"].get("full_stock", 50)
    if "dialysis_machines" in eq:
        eq["dialysis_machines"]["in_use"] = 0
        eq["dialysis_machines"]["available"] = eq["dialysis_machines"].get("total", 6)
    if "ventilators" in eq:
        eq["ventilators"]["in_use"] = 0
        eq["ventilators"]["available"] = eq["ventilators"].get("total", 16)

    # 3. Reset Operation Theatres to Available
    ots = res_doc.get("operation_theatres", [])
    for ot in ots:
        ot["status"] = "Available"
        ot["case"] = "Ready for emergency surgical case"

    # Save to MongoDB
    db.hospital_resources.update_one(
        {"_id": "MAIN_HOSPITAL_RESOURCES"},
        {"$set": {
            "wards": wards,
            "medical_equipment": eq,
            "operation_theatres": ots
        }}
    )

    # 4. Clear/Discharge any active admissions in MongoDB
    db.admissions.update_many(
        {"status": "ADMITTED_ACTIVE"},
        {"$set": {
            "status": "DISCHARGED",
            "discharge_timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": "Bulk discharged on hospital reset"
        }}
    )

    # 5. Log audit event in MongoDB
    db.audit_logs.insert_one({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "HOSPITAL_ALL_BEDS_EMPTIED",
        "total_beds_reset": total_beds_count,
        "details": f"All {total_beds_count} hospital beds across all 8 wards reset to Available (100% capacity free).",
        "action_by": "Administrator"
    })

    print(f"\nSUCCESS: All {total_beds_count} beds across all 8 wards have been reset to 'Available' (Green) in MongoDB!")
    print(f"Hospital Occupancy: 0 / {total_beds_count} Beds (0% Occupancy - 100% Available)")

if __name__ == "__main__":
    empty_all_hospital_beds()
