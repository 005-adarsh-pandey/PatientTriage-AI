// main.js - Hospital Management & Clinical Decision Platform

let currentQueue = [];
let isSurgeActive = false;
let currentPatientId = null;
let currentTriageResult = null;
let currentDoctors = [];
let currentResources = null;

let intakeAadharController = null;
let directAadharController = null;

// 12-Slot Aadhaar Input Controller
function setupAadharSlots(containerId, hiddenInputId, counterId, onComplete) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    const slots = container.querySelectorAll('.aadhar-digit-slot');
    const hiddenInput = document.getElementById(hiddenInputId);
    const counter = counterId ? document.getElementById(counterId) : null;

    function getCombinedValue() {
        let val = '';
        slots.forEach(slot => {
            val += (slot.value || '').trim();
        });
        return val;
    }

    function updateState() {
        const val = getCombinedValue();
        if (hiddenInput) hiddenInput.value = val;
        if (counter) {
            counter.innerText = `${val.length} / 12 Digits`;
            if (val.length === 12) {
                counter.className = "badge bg-success small";
            } else {
                counter.className = "badge bg-light text-secondary border small";
            }
        }
        slots.forEach(s => {
            if (s.value) s.classList.add('filled');
            else s.classList.remove('filled');
        });
        if (typeof updateDataCompleteness === 'function') {
            updateDataCompleteness();
        }
        if (val.length === 12 && typeof onComplete === 'function') {
            onComplete(val);
        }
    }

    slots.forEach((slot, idx) => {
        slot.addEventListener('input', (e) => {
            const digit = e.target.value.replace(/[^0-9]/g, '');
            if (digit.length > 0) {
                slot.value = digit[digit.length - 1];
                if (idx < slots.length - 1) {
                    slots[idx + 1].focus();
                    slots[idx + 1].select();
                }
            } else {
                slot.value = '';
            }
            updateState();
        });

        slot.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace') {
                if (!slot.value && idx > 0) {
                    slots[idx - 1].focus();
                    slots[idx - 1].value = '';
                    updateState();
                    e.preventDefault();
                }
            } else if (e.key === 'ArrowLeft' && idx > 0) {
                slots[idx - 1].focus();
                e.preventDefault();
            } else if (e.key === 'ArrowRight' && idx < slots.length - 1) {
                slots[idx + 1].focus();
                e.preventDefault();
            }
        });

        slot.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text');
            const cleanDigits = text.replace(/[^0-9]/g, '').slice(0, 12);
            for (let i = 0; i < slots.length; i++) {
                slots[i].value = cleanDigits[i] || '';
            }
            const focusTarget = Math.min(cleanDigits.length, slots.length - 1);
            if (slots[focusTarget]) slots[focusTarget].focus();
            updateState();
        });
    });

    return {
        setValue: (valStr) => {
            const clean = String(valStr || '').replace(/[^0-9]/g, '').slice(0, 12);
            slots.forEach((s, i) => {
                s.value = clean[i] || '';
            });
            updateState();
        },
        clear: () => {
            slots.forEach(s => s.value = '');
            updateState();
        },
        getValue: getCombinedValue
    };
}

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    intakeAadharController = setupAadharSlots('intakeAadharContainer', 'aadhar_no', 'intakeAadharCount', (val) => {
        if (val && val.length === 12) checkAadharPatient();
    });
    directAadharController = setupAadharSlots('directAadharContainer', 'directQueryInput', 'directAadharCount');

    setupFormCompletenessListeners();
    checkMongoStatus();
    loadHospitalResources();
    loadStaffAndDoctors();
    loadQueue();
    loadBenchmarks();
    loadAuditLogs();
    updateAgeNorms();
    updateDataCompleteness();
});

// Helper for switching tabs programmatically
function switchTab(tabId) {
    const triggerEl = document.getElementById(tabId);
    if (triggerEl) {
        bootstrap.Tab.getInstance(triggerEl) || new bootstrap.Tab(triggerEl).show();
    }
}

// ----------------- 0. AADHAAR & DIRECT PATIENT ACTION ENGINE -----------------

function clearIntakeAadhar() {
    if (intakeAadharController) intakeAadharController.clear();
    document.getElementById('aadhar_no').value = '';
    document.getElementById('patient_id_display').value = '';
    const statusBox = document.getElementById('aadharStatusAlert');
    if (statusBox) {
        statusBox.classList.add('d-none');
        statusBox.innerHTML = '';
    }
    updateDataCompleteness();
}

function clearDirectAadhar() {
    if (directAadharController) directAadharController.clear();
    document.getElementById('directQueryInput').value = '';
    const card = document.getElementById('directPatientCard');
    if (card) card.classList.add('d-none');
}

async function checkAadharPatient() {
    const aadharVal = (document.getElementById('aadhar_no')?.value || '').replace(/[^0-9]/g, '');
    const statusBox = document.getElementById('aadharStatusAlert');

    if (aadharVal.length !== 12) {
        if (statusBox) {
            statusBox.classList.remove('d-none');
            statusBox.innerHTML = `
                <span class="badge bg-danger bg-opacity-25 text-danger border border-danger small p-1">
                    <i class="fa-solid fa-circle-exclamation me-1"></i> Aadhaar must be exactly 12 numeric digits (${aadharVal.length}/12 entered)
                </span>
            `;
        }
        return;
    }

    try {
        const resp = await fetch('/api/patient/aadhar_lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aadhar_no: aadharVal })
        });
        const data = await resp.json();
        if (data.success) {
            document.getElementById('patient_id_display').value = data.patient_id;
            
            if (statusBox) {
                statusBox.classList.remove('d-none');
                if (data.exists && data.total_past_visits > 0) {
                    const pat = data.patient || {};
                    statusBox.innerHTML = `
                        <span class="badge bg-warning bg-opacity-25 text-dark border border-warning small p-1">
                            <i class="fa-solid fa-user-check me-1 text-primary"></i> Verified Patient Record Found (${data.total_past_visits} Past Visits)
                        </span>
                    `;
                    if (pat.name && !document.getElementById('patient_name').value) {
                        document.getElementById('patient_name').value = pat.name;
                    }
                    if (pat.age && !document.getElementById('patient_age').value) {
                        document.getElementById('patient_age').value = pat.age;
                        updateAgeNorms();
                    }
                    if (pat.gender && !document.getElementById('patient_gender').value) {
                        document.getElementById('patient_gender').value = pat.gender;
                    }
                } else {
                    statusBox.innerHTML = `
                        <span class="badge bg-success bg-opacity-25 text-success border border-success small p-1">
                            <i class="fa-solid fa-id-card me-1"></i> Unique 12-Digit Aadhaar Verified &amp; Linked
                        </span>
                    `;
                }
            }
            updateDataCompleteness();
        } else {
            if (statusBox) {
                statusBox.classList.remove('d-none');
                statusBox.innerHTML = `
                    <span class="badge bg-danger bg-opacity-25 text-danger border border-danger small p-1">
                        <i class="fa-solid fa-circle-xmark me-1"></i> ${data.error || 'Aadhaar validation failed'}
                    </span>
                `;
            }
        }
    } catch (err) {
        console.error(err);
    }
}

function openDirectActionModal() {
    new bootstrap.Modal(document.getElementById('directActionModal')).show();
}

let activeLookupPatient = null;

async function searchPatientDirectAction() {
    const query = (document.getElementById('directQueryInput')?.value || '').replace(/[^0-9]/g, '').trim();
    if (!query || query.length !== 12) {
        alert("Please enter a complete 12-digit Aadhaar number to locate patient.");
        return;
    }

    try {
        const resp = await fetch('/api/patient/aadhar_lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aadhar_no: query })
        });
        const data = await resp.json();

        if (data.success) {
            activeLookupPatient = data;
            const card = document.getElementById('directPatientCard');
            card.classList.remove('d-none');

            const pat = data.patient || {};
            const adm = data.admission_info || {};

            document.getElementById('directPatName').innerText = pat.name || 'Admitted Patient';
            if (document.getElementById('directPatId')) {
                document.getElementById('directPatId').innerText = data.patient_id;
            }
            document.getElementById('directPatAadhar').innerText = data.masked_aadhar || `XXXX-XXXX-${query.slice(-4)}`;

            if (adm && adm.is_admitted) {
                document.getElementById('directAdmStatus').className = "badge bg-danger";
                document.getElementById('directAdmStatus').innerText = "CURRENTLY ADMITTED";
                document.getElementById('directPatWard').innerText = (adm.current_ward_key || 'Inpatient').toUpperCase();
                document.getElementById('directPatBed').innerText = adm.current_bed_id || 'Assigned';
                document.getElementById('directPatBed').className = "badge bg-danger fs-6";
            } else {
                document.getElementById('directAdmStatus').className = "badge bg-secondary";
                document.getElementById('directAdmStatus').innerText = "NOT CURRENTLY ADMITTED";
                document.getElementById('directPatWard').innerText = "None (Discharged / Outpatient)";
                document.getElementById('directPatBed').innerText = "N/A";
            }
        } else {
            alert(data.error || "No patient found for this 12-digit Aadhaar.");
        }
    } catch (err) {
        console.error(err);
    }
}

async function executeDirectTransfer() {
    const query = (document.getElementById('directQueryInput')?.value || '').replace(/[^0-9]/g, '').trim();
    const toWard = document.getElementById('directTransferWard').value;

    try {
        const resp = await fetch('/api/patient/transfer_by_id', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, to_ward: toWard })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('directActionModal'))?.hide();
            alert(`Direct Transfer Succeeded!\n${data.message}`);
            loadHospitalResources();
            loadAuditLogs();
        } else {
            alert("Transfer failed: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

async function executeDirectDischarge() {
    const query = document.getElementById('directQueryInput').value.trim();
    if (!query) return;

    if (!activeLookupPatient || !activeLookupPatient.admission_info || !activeLookupPatient.admission_info.is_admitted) {
        alert("Cannot Discharge: Patient is not currently admitted to any hospital bed or ward.");
        return;
    }

    const patName = document.getElementById('directPatName').innerText || 'Patient';
    if (!confirm(`Confirm complete discharge for ${patName}?\nSystem will auto-locate their bed, release equipment, and mark bed for sanitization.`)) {
        return;
    }

    try {
        const resp = await fetch('/api/patient/discharge_by_id', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('directActionModal'))?.hide();
            alert(`Direct Discharge Succeeded!\n${data.message}`);
            loadHospitalResources();
            loadAuditLogs();
        } else {
            alert("Discharge failed: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

// ----------------- 1. HOSPITAL RESOURCES & BEDS -----------------

async function loadHospitalResources() {
    try {
        const resp = await fetch('/api/resources');
        const data = await resp.json();
        if (!data.success) return;

        currentResources = data.resources;
        renderResourcesUI(currentResources);
    } catch (err) {
        console.error("Error loading resources:", err);
    }
}

function renderResourcesUI(res) {
    if (!res) return;

    // 1. Equipment Top Counters & Status Cards
    const eq = res.medical_equipment || {};
    const o2 = eq.oxygen_cylinders || { total_stock: 50, full_stock: 50, in_use: 0, available: 50, central_pressure_psi: 142 };
    const dia = eq.dialysis_machines || { total: 6, in_use: 0, available: 6 };
    const vent = eq.ventilators || { total: 16, in_use: 0, available: 16 };

    const topO2 = document.getElementById('topO2Psi');
    if (topO2) topO2.innerText = `${o2.central_pressure_psi || 142} PSI`;

    const totalO2 = o2.total_stock || o2.full_stock || o2.total || 50;
    const availO2 = o2.available !== undefined ? o2.available : (totalO2 - (o2.in_use || 0));

    const eqO2Stock = document.getElementById('eqO2Stock');
    if (eqO2Stock) eqO2Stock.innerText = `${availO2} Avail / ${totalO2}`;

    const eqO2Psi = document.getElementById('eqO2Psi');
    if (eqO2Psi) eqO2Psi.innerText = `${o2.central_pressure_psi || 142} PSI Central Line`;

    const eqDia = document.getElementById('eqDialysis');
    if (eqDia) eqDia.innerText = `${dia.available} Avail / ${dia.total}`;

    const eqDiaInUse = document.getElementById('eqDialysisInUse');
    if (eqDiaInUse) eqDiaInUse.innerText = dia.in_use;

    const eqVent = document.getElementById('eqVentilators');
    if (eqVent) eqVent.innerText = `${vent.available} Avail / ${vent.total}`;

    const eqVentInUse = document.getElementById('eqVentInUse');
    if (eqVentInUse) eqVentInUse.innerText = vent.in_use;

    // Bed Total & Occupancy Calculation
    let totalBeds = 0, totalOcc = 0;
    const wards = res.wards || {};
    Object.keys(wards).forEach(wk => {
        totalBeds += (wards[wk].total_beds || 0);
        totalOcc += (wards[wk].occupied_beds || 0);
    });

    const occPercent = totalBeds > 0 ? Math.round((totalOcc / totalBeds) * 100) : 0;
    const topBeds = document.getElementById('topBedCount');
    if (topBeds) topBeds.innerText = `${totalOcc} / ${totalBeds} Beds`;

    const eqTotal = document.getElementById('eqTotalBeds');
    if (eqTotal) eqTotal.innerText = `${totalBeds} Beds`;

    const eqOcc = document.getElementById('eqOccupiedBeds');
    if (eqOcc) eqOcc.innerText = totalOcc;

    const eqOccPct = document.getElementById('eqOccPercent');
    if (eqOccPct) eqOccPct.innerText = `${occPercent}%`;

    // 2. Render Operation Theatres Grid
    const otContainer = document.getElementById('otGridContainer');
    if (otContainer && res.operation_theatres) {
        otContainer.innerHTML = '';
        res.operation_theatres.forEach(ot => {
            const col = document.createElement('div');
            col.className = 'col-md-6 col-lg-3';
            
            const statusBadges = {
                'Available': 'bg-success',
                'In_Surgery': 'bg-danger pulse-animation',
                'Under_Sterilization': 'bg-warning text-dark',
                'Reserved_Emergency': 'bg-danger'
            };

            col.innerHTML = `
                <div class="p-3 border rounded bg-white shadow-sm h-100">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <strong class="text-dark"><i class="fa-solid fa-scalpel text-primary me-1"></i>${ot.ot_id}</strong>
                        <span class="badge ${statusBadges[ot.status] || 'bg-secondary'}">${ot.status.replace('_', ' ')}</span>
                    </div>
                    <div class="fw-bold fs-6 mb-1 text-secondary">${ot.name}</div>
                    <div class="small text-muted mb-2">
                        ${ot.current_surgeon ? `<strong>Surgeon:</strong> ${ot.current_surgeon}` : 'No active surgeon'}
                    </div>
                    <div class="small text-secondary mb-3">${ot.case || 'Standby Ready'}</div>
                    <div class="btn-group btn-group-sm w-100">
                        <button class="btn btn-outline-success" onclick="setOTStatus('${ot.ot_id}', 'Available')">Free</button>
                        <button class="btn btn-outline-danger" onclick="setOTStatus('${ot.ot_id}', 'In_Surgery')">In Surgery</button>
                        <button class="btn btn-outline-warning" onclick="setOTStatus('${ot.ot_id}', 'Under_Sterilization')">Clean</button>
                    </div>
                </div>
            `;
            otContainer.appendChild(col);
        });
    }

    // 3. Render Ward Beds Grid
    const wardContainer = document.getElementById('wardBedsContainer');
    if (wardContainer && wards) {
        wardContainer.innerHTML = '';
        Object.keys(wards).forEach(wk => {
            const w = wards[wk];
            const wCard = document.createElement('div');
            wCard.className = 'p-3 border rounded mb-3 bg-light-subtle';

            let bedsHtml = '';
            (w.beds || []).forEach(b => {
                const bStatus = b.status || 'Available';
                const bColor = bStatus === 'Occupied' ? 'btn-danger' : (bStatus === 'Under_Cleaning' ? 'btn-warning text-dark' : 'btn-outline-success');
                bedsHtml += `
                    <button class="btn btn-sm ${bColor} m-1" title="Click to update status (${bStatus})" onclick="openBedUpdateModal('${wk}', '${b.id}', '${bStatus}')">
                        <i class="fa-solid fa-bed me-1"></i>${b.id}
                    </button>
                `;
            });

            wCard.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <strong class="text-dark fs-6">${w.name}</strong>
                        <span class="badge bg-secondary ms-2">${w.occupied_beds || 0} / ${w.total_beds || 0} Occupied</span>
                    </div>
                    <span class="small text-muted">Target Acuity: ESI ${(w.target_esi || []).join(', ')}</span>
                </div>
                <div class="d-flex flex-wrap pt-2 border-top bg-white p-2 rounded">
                    ${bedsHtml || '<span class="text-muted small">No bed array initialized</span>'}
                </div>
            `;
            wardContainer.appendChild(wCard);
        });
    }
}

async function updateEquipmentStock(eqType, delta) {
    try {
        const resp = await fetch('/api/resources/update_equipment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ equipment_type: eqType, delta_in_use: delta })
        });
        const data = await resp.json();
        if (data.success) {
            loadHospitalResources();
        }
    } catch (err) {
        console.error(err);
    }
}

async function setOTStatus(otId, status) {
    try {
        const resp = await fetch('/api/resources/update_ot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ot_id: otId, status: status })
        });
        const data = await resp.json();
        if (data.success) {
            loadHospitalResources();
        }
    } catch (err) {
        console.error(err);
    }
}

function openBedUpdateModal(wardKey, bedId, currentStatus) {
    document.getElementById('modalWardKey').value = wardKey;
    document.getElementById('modalBedId').value = bedId;
    document.getElementById('modalBedTitle').innerText = `${bedId} (${wardKey.toUpperCase()})`;
    document.getElementById('modalBedStatusSelect').value = currentStatus;

    // Check if bed has an assigned patient
    let patientId = "None";
    if (currentResources && currentResources.wards && currentResources.wards[wardKey]) {
        const bedObj = (currentResources.wards[wardKey].beds || []).find(b => b.id === bedId);
        if (bedObj && bedObj.patient) {
            patientId = bedObj.patient;
        }
    }
    document.getElementById('modalPatientTitle').innerText = patientId;

    onTransferWardChange();
    new bootstrap.Modal(document.getElementById('bedUpdateModal')).show();
}

function onTransferWardChange() {
    const targetWard = document.getElementById('transferTargetWard').value;
    let autoBed = `${targetWard.substring(0, 3).toUpperCase()}-01`;
    if (currentResources && currentResources.wards && currentResources.wards[targetWard]) {
        const avail = (currentResources.wards[targetWard].beds || []).find(b => b.status === 'Available');
        if (avail) autoBed = avail.id;
    }
    document.getElementById('transferTargetBedId').value = autoBed;
}

async function executePatientTransfer() {
    const fromWard = document.getElementById('modalWardKey').value;
    const fromBed = document.getElementById('modalBedId').value;
    const patientId = document.getElementById('modalPatientTitle').innerText;
    const toWard = document.getElementById('transferTargetWard').value;
    const toBed = document.getElementById('transferTargetBedId').value;

    if (patientId === "None") {
        alert("No active patient is currently admitted to this bed to transfer.");
        return;
    }

    try {
        const resp = await fetch('/api/patient/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_id: patientId,
                from_ward: fromWard,
                from_bed: fromBed,
                to_ward: toWard,
                to_bed: toBed
            })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('bedUpdateModal'))?.hide();
            alert(`Step-Down Transfer Complete!\nPatient ${patientId} transferred to ${toBed}.\nOld Bed (${fromBed}) is now marked 'Under Cleaning' and ventilator released.`);
            loadHospitalResources();
            loadAuditLogs();
        } else {
            alert("Transfer error: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

async function executePatientDischarge() {
    const wardKey = document.getElementById('modalWardKey').value;
    const bedId = document.getElementById('modalBedId').value;
    const currentStatus = document.getElementById('modalBedStatusSelect').value;
    const patientTitle = document.getElementById('modalPatientTitle').innerText;

    if (patientTitle === "None" || currentStatus !== "Occupied") {
        alert("Cannot Discharge: This bed is not currently occupied by an admitted patient.");
        return;
    }

    if (!confirm(`Are you sure you want to discharge the patient in bed ${bedId}? This will free all attached equipment and queue the bed for sanitization.`)) {
        return;
    }

    try {
        const resp = await fetch('/api/patient/discharge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_id: patientTitle,
                ward_key: wardKey,
                bed_id: bedId
            })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('bedUpdateModal'))?.hide();
            alert(`Patient Discharged Successfully!\nBed ${bedId} is now marked 'Under Cleaning' and returned to inventory.`);
            loadHospitalResources();
            loadAuditLogs();
        } else {
            alert("Discharge error: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

async function submitBedStatusUpdate() {
    const wardKey = document.getElementById('modalWardKey').value;
    const bedId = document.getElementById('modalBedId').value;
    const newStatus = document.getElementById('modalBedStatusSelect').value;

    try {
        const resp = await fetch('/api/resources/update_bed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ward_key: wardKey, bed_id: bedId, status: newStatus })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('bedUpdateModal'))?.hide();
            loadHospitalResources();
        } else {
            alert("Error: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

// ----------------- 2. DOCTORS, STAFF & LEAVE MANAGEMENT -----------------

async function loadStaffAndDoctors() {
    try {
        const docResp = await fetch('/api/doctors');
        const docData = await docResp.json();
        if (docData.success) {
            currentDoctors = docData.doctors;
            renderDoctorsTable(currentDoctors);
        }

        const staffResp = await fetch('/api/staff');
        const staffData = await staffResp.json();
        if (staffData.success) {
            renderStaffTable(staffData.staff);
        }
    } catch (err) {
        console.error("Error loading doctors/staff:", err);
    }
}

function renderDoctorsTable(doctors) {
    const tbody = document.getElementById('doctorsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    let activeCount = 0;
    const selectEl = document.getElementById('leaveDoctorSelect');
    if (selectEl) selectEl.innerHTML = '';

    doctors.forEach(d => {
        if (d.status === 'Available') activeCount++;
        const tr = document.createElement('tr');
        if (d.status === 'On-Leave') tr.className = 'table-danger';

        const statusBadges = {
            'Available': '<span class="badge bg-success">On-Duty / Available</span>',
            'In-Surgery': '<span class="badge bg-warning text-dark">In-Surgery</span>',
            'On-Leave': '<span class="badge bg-danger">ON-LEAVE</span>'
        };

        tr.innerHTML = `
            <td>
                <strong class="text-dark">${d.name}</strong>
                <div class="small text-muted">${d._id}</div>
            </td>
            <td>
                <div>${d.specialty}</div>
                <div class="small text-secondary">${d.qualifications || ''}</div>
            </td>
            <td><span class="badge bg-light text-dark border">${d.room}</span></td>
            <td>${d.phone}</td>
            <td>${statusBadges[d.status] || '<span class="badge bg-secondary">Offline</span>'}</td>
            <td>
                <span class="small text-primary fw-semibold">${d.backup_id ? `${d.backup_id} (On-Call)` : 'None'}</span>
            </td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-primary" onclick="triggerDoctorLeaveQuick('${d._id}', ${d.status !== 'On-Leave'})">
                    ${d.status === 'On-Leave' ? '<i class="fa-solid fa-user-check me-1"></i> Return' : '<i class="fa-solid fa-user-slash me-1"></i> Mark Leave'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);

        if (selectEl) {
            const opt = document.createElement('option');
            opt.value = d._id;
            opt.innerText = `${d.name} (${d.specialty})`;
            selectEl.appendChild(opt);
        }
    });

    const topDoc = document.getElementById('topDocCount');
    if (topDoc) topDoc.innerText = `${activeCount}/${doctors.length} Doctors Active`;
}

function renderStaffTable(staffList) {
    const tbody = document.getElementById('staffTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    staffList.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="badge bg-dark">${s._id}</span></td>
            <td>
                <strong>${s.name}</strong>
                <div class="small text-muted">${s.role}</div>
            </td>
            <td>${s.assigned_ward}</td>
            <td><span class="badge bg-info text-dark">${s.shift}</span></td>
            <td><span class="badge bg-success">${s.status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function openDoctorLeaveModal() {
    onDoctorSelectChange();
    new bootstrap.Modal(document.getElementById('doctorLeaveModal')).show();
}

function onDoctorSelectChange() {
    const docId = document.getElementById('leaveDoctorSelect').value;
    const doc = currentDoctors.find(d => d._id === docId);
    if (doc) {
        const backupDoc = currentDoctors.find(d => d._id === doc.backup_id) || { name: 'Dr. Amit Roy (Emergency Lead)', _id: 'DOC-107' };
        document.getElementById('leaveBackupDocDisplay').value = `${backupDoc.name} (${backupDoc.specialty})`;
        document.getElementById('leaveBackupDocId').value = backupDoc._id;
    }
}

async function triggerDoctorLeaveQuick(docId, setLeave) {
    const doc = currentDoctors.find(d => d._id === docId);
    const backupId = doc?.backup_id || 'DOC-107';

    try {
        const resp = await fetch('/api/doctors/leave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doctor_id: docId, on_leave: setLeave, reason: 'Leave updated by Lead', backup_id: backupId })
        });
        const data = await resp.json();
        if (data.success) {
            loadStaffAndDoctors();
            alert(`Doctor ${data.doctor} is now ${data.status}. Substitute: ${data.substitute}`);
        }
    } catch (err) {
        console.error(err);
    }
}

async function submitDoctorLeave() {
    const docId = document.getElementById('leaveDoctorSelect').value;
    const onLeave = document.getElementById('leaveStatusToggle').value === 'true';
    const reason = document.getElementById('leaveReasonInput').value;
    const backupId = document.getElementById('leaveBackupDocId').value;

    try {
        const resp = await fetch('/api/doctors/leave', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doctor_id: docId, on_leave: onLeave, reason: reason, backup_id: backupId })
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('doctorLeaveModal'))?.hide();
            loadStaffAndDoctors();
            alert(`Roster updated in MongoDB: ${data.doctor} is now ${data.status}. On-Call Backup: ${data.substitute}`);
        }
    } catch (err) {
        console.error(err);
    }
}

// ----------------- 3. INTAKE & CLINICAL ADMISSION -----------------

function updateAgeNorms() {
    const ageInput = document.getElementById('patient_age');
    const age = parseFloat(ageInput ? ageInput.value : 35) || 35;
    const badge = document.getElementById('ageCategoryBadge');
    const hint = document.getElementById('ageNormsHint');
    if (!badge || !hint) return;

    if (age < 0.08) {
        badge.className = "badge bg-danger me-2";
        badge.innerText = "Neonate (<28 Days)";
        hint.innerText = "Normal: HR 120-160 | RR 40-60 | Temp 36.5-37.5°C | Critical Neonatal Vulnerability";
    } else if (age < 1) {
        badge.className = "badge bg-danger me-2";
        badge.innerText = "Pediatric (Infant <1y)";
        hint.innerText = "Normal: HR 100-160 | RR 30-50 | SBP 70-100 | Temp 36.5-37.5°C";
    } else if (age <= 3) {
        badge.className = "badge bg-warning text-dark me-2";
        badge.innerText = "Pediatric (Toddler 1-3y)";
        hint.innerText = "Normal: HR 90-140 | RR 24-40 | SBP 80-110 | Temp 36.5-37.5°C";
    } else if (age <= 11) {
        badge.className = "badge bg-info text-dark me-2";
        badge.innerText = "Pediatric (Child 4-11y)";
        hint.innerText = "Normal: HR 70-120 | RR 18-30 | SBP 90-115 | Temp 36.5-37.5°C";
    } else if (age < 18) {
        badge.className = "badge bg-primary me-2";
        badge.innerText = "Pediatric (Adolescent 12-17y)";
        hint.innerText = "Normal: HR 60-100 | RR 12-20 | SBP 100-125 | SpO2 >=95%";
    } else if (age < 65) {
        badge.className = "badge bg-dark me-2";
        badge.innerText = "Adult (18-64y)";
        hint.innerText = "Normal: HR 60-100 | RR 12-20 | SBP 95-139 | DBP 60-89 | SpO2 >=95%";
    } else {
        badge.className = "badge bg-secondary me-2";
        badge.innerText = "Geriatric (65+y)";
        hint.innerText = "Normal: HR 55-95 | RR 12-22 | SBP 100-149 | Alert: Temp >=37.8°C / SBP <100";
    }
}

// Real Clinical Dataset Presets
function fillPreset(presetKey) {
    const presets = {
        'trauma_unresponsive': {
            aadhar: '548298214321', name: 'Ramesh Sharma',
            age: 48, gender: 'Male', arrival_mode: 2, injury: 1,
            complaint: 'Major polytrauma, massive hemorrhage, unresponsive',
            mental: 4, pain_flag: 0, nrs_pain: 0, sbp: 68, dbp: 40, hr: 146, rr: 34, temp: 35.8, spo2: 82.0
        },
        'stemi_chest_pain': {
            aadhar: '887212349811', name: 'Sunita Devi',
            age: 64, gender: 'Female', arrival_mode: 3, injury: 2,
            complaint: 'Crushing retrosternal chest pain radiating to left jaw with cold diaphoresis',
            mental: 1, pain_flag: 1, nrs_pain: 9, sbp: 164, dbp: 98, hr: 112, rr: 24, temp: 36.6, spo2: 94.0
        },
        'septic_shock': {
            aadhar: '782165439012', name: 'Om Prakash Verma',
            age: 78, gender: 'Male', arrival_mode: 2, injury: 2,
            complaint: 'Altered sensorium, high fever, shivering, unable to stand (Severe Sepsis)',
            mental: 2, pain_flag: 0, nrs_pain: 2, sbp: 82, dbp: 50, hr: 138, rr: 28, temp: 39.4, spo2: 88.0
        },
        'acute_uremia': {
            aadhar: '623489012345', name: 'Kavita Patel',
            age: 56, gender: 'Female', arrival_mode: 1, injury: 2,
            complaint: 'End stage renal disease, missed dialysis x 4 days, severe uremia and K+ 7.4',
            mental: 1, pain_flag: 0, nrs_pain: 3, sbp: 178, dbp: 102, hr: 104, rr: 22, temp: 36.7, spo2: 93.0
        },
        'humerus_fracture': {
            aadhar: '451298763421', name: 'Meena Gupta',
            age: 68, gender: 'Female', arrival_mode: 4, injury: 1,
            complaint: 'Left shoulder and arm pain after slip and fall (Closed Humerus Neck Fracture)',
            mental: 1, pain_flag: 1, nrs_pain: 6, sbp: 130, dbp: 80, hr: 84, rr: 18, temp: 36.6, spo2: 98.0
        },
        'corneal_abrasion': {
            aadhar: '334455667788', name: 'Anil Deshmukh',
            age: 45, gender: 'Male', arrival_mode: 1, injury: 1,
            complaint: 'Right ocular pain and photophobia after dust blown into eye',
            mental: 1, pain_flag: 1, nrs_pain: 5, sbp: 128, dbp: 82, hr: 76, rr: 16, temp: 36.6, spo2: 99.0
        },
        'superficial_burn': {
            aadhar: '223344556677', name: 'Deepak Roy',
            age: 32, gender: 'Male', arrival_mode: 1, injury: 1,
            complaint: 'Superficial 1st degree burn on right forearm from hot oil',
            mental: 1, pain_flag: 1, nrs_pain: 3, sbp: 122, dbp: 78, hr: 72, rr: 14, temp: 36.5, spo2: 99.0
        },
        'newborn_nicu': {
            aadhar: '112233445566', name: 'Baby of Priya',
            age: 0.05, gender: 'Male', arrival_mode: 2, injury: 2,
            complaint: '18-day newborn with grunting, apnea, severe chest indrawing',
            mental: 3, pain_flag: 0, nrs_pain: 2, sbp: 68, dbp: 38, hr: 182, rr: 64, temp: 39.2, spo2: 86.0
        }
    };

    const p = presets[presetKey];
    if (!p) return;

    if (intakeAadharController) {
        intakeAadharController.setValue(p.aadhar);
    }
    document.getElementById('patient_name').value = p.name || '';
    document.getElementById('patient_age').value = p.age;
    document.getElementById('patient_gender').value = p.gender;
    document.getElementById('arrival_mode').value = p.arrival_mode;
    document.getElementById('injury').value = p.injury;
    document.getElementById('chief_complaint').value = p.complaint;
    document.getElementById('mental').value = p.mental;
    document.getElementById('pain_flag').value = p.pain_flag;
    document.getElementById('nrs_pain').value = p.nrs_pain;
    document.getElementById('sbp').value = p.sbp;
    document.getElementById('dbp').value = p.dbp;
    document.getElementById('heart_rate').value = p.hr;
    document.getElementById('resp_rate').value = p.rr;
    document.getElementById('temp_c').value = p.temp;
    document.getElementById('spo2').value = p.spo2;

    updateAgeNorms();
    updateDataCompleteness();
}

function setupFormCompletenessListeners() {
    const form = document.getElementById('triageForm');
    if (!form) return;
    form.querySelectorAll('input, select, textarea').forEach(el => {
        el.addEventListener('input', updateDataCompleteness);
        el.addEventListener('change', updateDataCompleteness);
    });
}

function updateDataCompleteness() {
    const aadharVal = (document.getElementById('aadhar_no')?.value || '').replace(/[^0-9]/g, '');
    const fields = [
        aadharVal.length === 12,
        (document.getElementById('patient_name')?.value || '').trim().length > 0,
        (document.getElementById('patient_age')?.value || '').trim().length > 0,
        (document.getElementById('patient_gender')?.value || '').trim().length > 0,
        (document.getElementById('arrival_mode')?.value || '').trim().length > 0,
        (document.getElementById('injury')?.value || '').trim().length > 0,
        (document.getElementById('chief_complaint')?.value || '').trim().length > 0,
        (document.getElementById('mental')?.value || '').trim().length > 0,
        (document.getElementById('pain_flag')?.value || '').trim().length > 0,
        (document.getElementById('nrs_pain')?.value || '').trim().length > 0,
        (document.getElementById('sbp')?.value || '').trim().length > 0,
        (document.getElementById('dbp')?.value || '').trim().length > 0,
        (document.getElementById('heart_rate')?.value || '').trim().length > 0,
        (document.getElementById('resp_rate')?.value || '').trim().length > 0,
        (document.getElementById('temp_c')?.value || '').trim().length > 0,
        (document.getElementById('spo2')?.value || '').trim().length > 0
    ];

    const filled = fields.filter(Boolean).length;
    const pct = Math.round((filled / fields.length) * 100);
    const badge = document.getElementById('dataCompletenessBadge');
    if (badge) {
        badge.innerText = `Completeness: ${pct}%`;
        if (pct === 100) {
            badge.className = "badge bg-success small";
        } else if (pct >= 50) {
            badge.className = "badge bg-warning text-dark small";
        } else {
            badge.className = "badge bg-info text-dark small";
        }
    }
}

async function evaluatePatient() {
    const aadharVal = (document.getElementById('aadhar_no')?.value || '').replace(/[^0-9]/g, '');

    if (aadharVal.length !== 12) {
        alert("Validation Error: Please enter a complete 12-digit Aadhaar number before evaluating.");
        document.querySelector('#intakeAadharContainer .aadhar-digit-slot')?.focus();
        return;
    }

    const patientAge = document.getElementById('patient_age').value;
    const patientGender = document.getElementById('patient_gender').value;
    const arrivalMode = document.getElementById('arrival_mode').value;
    const injury = document.getElementById('injury').value;
    const chiefComplaint = document.getElementById('chief_complaint').value.trim();
    const mental = document.getElementById('mental').value;
    const painFlag = document.getElementById('pain_flag').value;
    const nrsPain = document.getElementById('nrs_pain').value;
    const sbp = document.getElementById('sbp').value;
    const dbp = document.getElementById('dbp').value;
    const hr = document.getElementById('heart_rate').value;
    const rr = document.getElementById('resp_rate').value;
    const temp = document.getElementById('temp_c').value;
    const spo2 = document.getElementById('spo2').value;

    if (!patientAge || !patientGender || !arrivalMode || !injury || !chiefComplaint || !mental || painFlag === "" || !nrsPain || !sbp || !dbp || !hr || !rr || !temp || !spo2) {
        alert("Validation Error: Please complete all required patient clinical parameters and vital signs.");
        return;
    }

    const patientId = document.getElementById('patient_id_display')?.value || `PT-${aadharVal.slice(-4)}-${aadharVal.slice(0, 4)}`;
    const patientName = document.getElementById('patient_name')?.value.trim() || `Patient (${patientId})`;

    const payload = {
        aadhar_no: aadharVal,
        patient_id: patientId,
        name: patientName,
        patient_name: patientName,
        patient_age: parseFloat(patientAge),
        patient_gender: patientGender,
        arrival_mode: parseInt(arrivalMode),
        injury: parseInt(injury),
        chief_complaint: chiefComplaint,
        mental: parseInt(mental),
        pain_flag: parseInt(painFlag),
        pain_score: parseFloat(nrsPain),
        nrs_pain: parseFloat(nrsPain),
        sbp: parseFloat(sbp),
        dbp: parseFloat(dbp),
        heart_rate: parseFloat(hr),
        resp_rate: parseFloat(rr),
        temp_c: parseFloat(temp),
        spo2: parseFloat(spo2),
        add_to_queue: true,
        clinician_id: 'RN-TriageWorkstation'
    };

    const btn = document.getElementById('btnEvaluate');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i> Running Clinical Decision Model & Saving to MongoDB...`;
    btn.disabled = true;

    try {
        const resp = await fetch('/api/triage/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();

        if (data.success) {
            currentTriageResult = data.triage_result;
            renderEvaluationResult(data.triage_result);
            checkMongoStatus();
            loadQueue();
            loadHospitalResources();
            loadAuditLogs();
        } else {
            alert("Evaluation error: " + data.error);
        }
    } catch (err) {
        console.error(err);
        alert("Server error.");
    } finally {
        btn.innerHTML = `<i class="fa-solid fa-calculator me-1"></i> Evaluate Clinical Decision & Allocate Ward`;
        btn.disabled = false;
    }
}

function renderEvaluationResult(res) {
    document.getElementById('emptyResultPlaceholder').classList.add('d-none');
    document.getElementById('evaluationOutput').classList.remove('d-none');
    document.getElementById('evalStatusBadge').className = "badge bg-success";
    document.getElementById('evalStatusBadge').innerText = "Clinical Recommendation Ready";

    const lvl = res.final_level;
    const banner = document.getElementById('esiLevelBanner');
    const levelColors = {
        1: '#dc2626', // Red
        2: '#ea580c', // Orange
        3: '#d97706', // Yellow/Amber
        4: '#2563eb', // Blue
        5: '#16a34a'  // Green
    };
    banner.style.backgroundColor = levelColors[lvl] || '#64748b';
    document.getElementById('esiLevelTitle').innerText = res.level_name;
    document.getElementById('esiLevelNumber').innerText = lvl;
    document.getElementById('deptRecommendation').innerText = `Recommended Ward: ${res.department_recommendation}`;

    const maxWaitMap = { 1: 'Immediate (0 min)', 2: '≤ 10 min', 3: '≤ 30 min', 4: '≤ 60 min', 5: '≤ 120 min' };
    document.getElementById('maxSafeWaitBadge').innerText = `Safe Wait: ${maxWaitMap[lvl]}`;

    // Target Ward Allocation
    document.getElementById('allocWard').innerText = res.department_recommendation;
    document.getElementById('allocDoctor').innerText = res.attending_specialist;
    document.getElementById('allocEquipment').innerText = res.equipment_needed;

    // Safety Escalation Box
    const escBox = document.getElementById('safetyEscalationBox');
    if (res.safety_escalation_applied) {
        escBox.classList.remove('d-none');
        document.getElementById('safetyEscalationText').innerText = res.safety_escalation_reason || "Safety-First Escalation Triggered";
    } else {
        escBox.classList.add('d-none');
    }

    // Confidence & Admission Risk
    document.getElementById('confidencePercent').innerText = `${res.confidence_percent}%`;
    document.getElementById('confidenceBar').style.width = `${res.confidence_percent}%`;
    document.getElementById('admissionRiskDisplay').innerText = `${res.admission_risk_percent}%`;
    document.getElementById('admissionRiskBar').style.width = `${res.admission_risk_percent}%`;

    // Clinical Drivers
    const driversList = document.getElementById('clinicalDriversList');
    driversList.innerHTML = '';
    (res.clinical_drivers || []).forEach(d => {
        const li = document.createElement('li');
        li.className = "list-group-item py-1 text-dark";
        li.innerHTML = `<i class="fa-solid fa-angle-right text-primary me-2"></i>${d}`;
        driversList.appendChild(li);
    });

    // Reset Lock Bed Button
    const btnLock = document.querySelector('#resultBody button.btn-success') || document.querySelector('#resultBody button.btn-secondary');
    if (btnLock) {
        btnLock.disabled = false;
        btnLock.className = "btn btn-success fw-bold";
        const bedId = res.recommended_bed_id || "Available Bed";
        btnLock.innerHTML = `<i class="fa-solid fa-bed me-1"></i> Lock Bed & Admit (${bedId})`;
    }
}

async function confirmAndLockBed() {
    if (!currentTriageResult) return;

    const aadharInput = document.getElementById('aadhar_no');
    const aadharVal = (aadharInput?.value || '').replace(/[^0-9]/g, '');
    let patientId = (document.getElementById('patient_id_display')?.value || '').trim();
    if (!patientId) {
        patientId = aadharVal ? `PT-${aadharVal.slice(-4)}-${aadharVal.slice(0, 4)}` : `PT-${Math.floor(1000 + Math.random() * 9000)}`;
    }

    const patientName = (document.getElementById('patient_name')?.value || '').trim() || `Patient (${patientId})`;

    const patientPayload = {
        patient_id: patientId,
        aadhar_no: aadharVal,
        name: patientName,
        patient_name: patientName,
        patient_age: parseFloat(document.getElementById('patient_age').value),
        patient_gender: document.getElementById('patient_gender').value,
        arrival_mode: parseInt(document.getElementById('arrival_mode').value),
        injury: parseInt(document.getElementById('injury').value),
        chief_complaint: document.getElementById('chief_complaint').value,
        mental: parseInt(document.getElementById('mental').value),
        heart_rate: parseFloat(document.getElementById('heart_rate').value),
        resp_rate: parseFloat(document.getElementById('resp_rate').value),
        sbp: parseFloat(document.getElementById('sbp').value),
        dbp: parseFloat(document.getElementById('dbp').value),
        spo2: parseFloat(document.getElementById('spo2').value),
        temp_c: parseFloat(document.getElementById('temp_c').value),
        pain_score: parseFloat(document.getElementById('nrs_pain').value)
    };

    const wardName = currentTriageResult.department_recommendation;
    
    // Auto-pick first available bed in ward
    let targetBedId = currentTriageResult.recommended_bed_id || "BED-AUTO";
    if (currentResources && currentResources.wards) {
        const wKey = currentTriageResult.ward_admission_decision?.ward_key || 'general';
        const wardObj = currentResources.wards[wKey];
        if (wardObj && wardObj.beds) {
            const availBed = wardObj.beds.find(b => b.status === 'Available');
            if (availBed) targetBedId = availBed.id;
        }
    }

    const btnLock = document.querySelector('#resultBody button.btn-success');
    if (btnLock) {
        btnLock.disabled = true;
        btnLock.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i> Admitting to MongoDB...`;
    }

    try {
        const resp = await fetch('/api/triage/confirm_admission', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_data: patientPayload,
                triage_result: currentTriageResult,
                ward_name: wardName,
                bed_id: targetBedId
            })
        });
        const data = await resp.json();
        if (data.success) {
            if (btnLock) {
                btnLock.className = "btn btn-secondary fw-bold disabled";
                btnLock.innerHTML = `<i class="fa-solid fa-check-circle text-success me-1"></i> Admitted to ${targetBedId} (MongoDB Saved)`;
            }
            alert(`Admission Confirmed in Hospital Database!\n\n• Patient: ${patientName}\n• Aadhaar: ${aadharVal || 'N/A'}\n• Assigned Bed: ${targetBedId} (${wardName})\n• Attending Doctor: ${currentTriageResult.attending_specialist}`);
            checkMongoStatus();
            loadHospitalResources();
            switchTab('resources-tab');
        } else {
            alert("Admission error: " + data.error);
            if (btnLock) {
                btnLock.disabled = false;
                btnLock.innerHTML = `<i class="fa-solid fa-bed me-1"></i> Lock Bed & Admit`;
            }
        }
    } catch (err) {
        console.error(err);
        if (btnLock) {
            btnLock.disabled = false;
            btnLock.innerHTML = `<i class="fa-solid fa-bed me-1"></i> Lock Bed & Admit`;
        }
    }
}

// ----------------- MONGODB CONNECTION MANAGER -----------------

async function checkMongoStatus() {
    try {
        const resp = await fetch('/api/mongo/status');
        const data = await resp.json();
        if (data.success) {
            const navText = document.getElementById('navDbStatusText');
            const navIcon = document.getElementById('navDbIcon');
            
            if (data.is_connected_to_mongo) {
                if (navText) navText.innerText = `🍃 Real MongoDB: Connected`;
                if (navIcon) navIcon.className = "fa-solid fa-leaf text-success";
            } else {
                if (navText) navText.innerText = `📁 Storage: Local JSON`;
                if (navIcon) navIcon.className = "fa-solid fa-database text-info";
            }

            // Update modal fields if present
            const modeBadge = document.getElementById('modalDbModeBadge');
            if (modeBadge) {
                modeBadge.innerText = data.mode;
                modeBadge.className = data.is_connected_to_mongo ? "badge bg-success" : "badge bg-secondary";
            }
            const uriEl = document.getElementById('modalDbUri');
            if (uriEl) uriEl.innerText = data.uri;

            if (data.counts) {
                const pEl = document.getElementById('modalCountPatients');
                if (pEl) pEl.innerText = data.counts.patients;
                const aEl = document.getElementById('modalCountAdmissions');
                if (aEl) aEl.innerText = data.counts.admissions;
                const lEl = document.getElementById('modalCountLogs');
                if (lEl) lEl.innerText = data.counts.audit_logs;
            }
        }
    } catch (err) {
        console.error("Error checking Mongo status:", err);
    }
}

function openMongoConfigModal() {
    checkMongoStatus();
    new bootstrap.Modal(document.getElementById('mongoConfigModal')).show();
}

async function connectCustomMongoUri() {
    const uri = document.getElementById('customMongoUriInput').value.trim();
    if (!uri) return;

    const btn = document.getElementById('btnConnectMongo');
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i> Connecting to MongoDB...`;
    btn.disabled = true;

    try {
        const resp = await fetch('/api/mongo/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uri: uri })
        });
        const data = await resp.json();
        if (data.success) {
            alert(`Connected to Real MongoDB Cluster Successfully!\nDatabase: ${data.db_name}\nMode: Live MongoDB`);
            bootstrap.Modal.getInstance(document.getElementById('mongoConfigModal'))?.hide();
            checkMongoStatus();
            loadHospitalResources();
            loadStaffAndDoctors();
        } else {
            alert(`Connection Failed: ${data.error || 'Check your MongoDB URI credentials.'}`);
        }
    } catch (err) {
        console.error(err);
        alert("Could not reach server to test MongoDB URI.");
    } finally {
        btn.innerHTML = `<i class="fa-solid fa-plug me-1"></i> Test & Connect to MongoDB`;
        btn.disabled = false;
    }
}

async function useLocalJsonMode() {
    bootstrap.Modal.getInstance(document.getElementById('mongoConfigModal'))?.hide();
    alert("Switched to Local JSON Persistence mode (Files: data_*.json). All patient admissions and bed changes are saved locally.");
    checkMongoStatus();
}

// ----------------- 4. QUEUE & AUDIT LOGS -----------------

async function loadQueue() {
    try {
        const resp = await fetch('/api/queue');
        const data = await resp.json();
        if (!data.success) return;

        currentQueue = data.queue;
        const summary = data.summary;

        document.getElementById('queueCountBadge').innerText = summary.total_waiting;
        document.getElementById('queueTotalWaiting').innerText = `${summary.total_waiting} Patients in Queue (${summary.reassessment_alerts} Re-assessment Alerts)`;

        const tbody = document.getElementById('queueTableBody');
        tbody.innerHTML = '';

        if (currentQueue.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">No patients currently waiting in ED.</td></tr>`;
            return;
        }

        const arrivalModeLabels = { 1: 'Walk-in', 2: '119 Ambulance', 3: 'Pvt Ambulance', 4: 'Private Car', 5: 'Transfer' };
        const mentalLabels = { 1: 'Alert (1)', 2: 'Verbal (2)', 3: 'Pain (3)', 4: 'Unresponsive (4)' };

        currentQueue.forEach(p => {
            const tr = document.createElement('tr');
            const isBreached = p.wait_minutes >= p.max_safe_wait && p.max_safe_wait > 0;
            if (p.deterioration_flag) tr.className = "table-danger";
            else if (isBreached) tr.className = "table-warning";

            const esiBadges = {
                1: 'badge bg-danger', 2: 'badge bg-warning text-dark', 3: 'badge bg-warning', 4: 'badge bg-primary', 5: 'badge bg-success'
            };

            const arrMode = arrivalModeLabels[p.arrival_mode] || 'Walk-in';
            const injType = p.injury === 1 ? '<span class="badge bg-danger">Trauma/Injury</span>' : '<span class="badge bg-secondary">Medical</span>';
            const mentalText = mentalLabels[p.mental] || (p.vitals?.avpu || 'Alert');

            tr.innerHTML = `
                <td><span class="${esiBadges[p.triage_level] || 'badge bg-secondary'} fs-6">Level ${p.triage_level}</span></td>
                <td>
                    <div class="fw-bold text-dark">${p.name || 'Patient'}</div>
                </td>
                <td>
                    <div>${p.age}y (${p.gender})</div>
                </td>
                <td class="small">
                    <div><i class="fa-solid fa-truck-medical text-primary me-1"></i>${arrMode}</div>
                    <div>${injType}</div>
                </td>
                <td style="max-width: 180px;" class="small">${p.chief_complaint}</td>
                <td class="small">
                    <div>HR: ${p.vitals.heart_rate} | BP: ${p.vitals.sbp}/${p.vitals.dbp || 80}</div>
                    <div>SpO2: ${p.vitals.spo2}% | <strong>${mentalText}</strong></div>
                </td>
                <td>
                    <div class="fw-bold ${isBreached ? 'text-danger' : 'text-dark'}">${p.wait_minutes.toFixed(0)} min</div>
                    <div class="small text-muted">Max safe: ${p.max_safe_wait}m</div>
                </td>
                <td class="small text-secondary">${p.recommended_zone}</td>
                <td>
                    ${p.deterioration_flag ? '<span class="badge bg-danger pulse-animation"><i class="fa-solid fa-bell"></i> DECOMPENSATING</span>' : 
                      (isBreached ? '<span class="badge bg-warning text-dark">RE-ASSESS</span>' : '<span class="badge bg-light text-dark border">STABLE</span>')}
                </td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" title="Record Repeat Vitals" onclick="openRepeatVitalsModal('${p.patient_id}')">
                            <i class="fa-solid fa-heart-pulse"></i>
                        </button>
                        <button class="btn btn-outline-danger" title="Clinician Override" onclick="openOverrideModalForPatient('${p.patient_id}')">
                            <i class="fa-solid fa-user-pen"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (summary.active_alerts && summary.active_alerts.length > 0) {
            const topAlert = summary.active_alerts[0];
            const banner = document.getElementById('liveAlertBanner');
            if (banner) {
                banner.classList.remove('d-none');
                banner.classList.add('d-flex');
                document.getElementById('alertTitle').innerText = topAlert.severity;
                document.getElementById('alertMessage').innerText = topAlert.message;
            }
        }

    } catch (err) {
        console.error(err);
    }
}

async function advanceQueueTime(minutes) {
    try {
        const resp = await fetch('/api/queue/advance_time', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ minutes: minutes })
        });
        const data = await resp.json();
        if (data.success) {
            loadQueue();
        }
    } catch (err) {
        console.error(err);
    }
}

async function toggleSurgeMode() {
    isSurgeActive = !isSurgeActive;
    try {
        const resp = await fetch('/api/surge/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active: isSurgeActive })
        });
        const data = await resp.json();
        if (data.success) {
            const btn = document.getElementById('btnToggleSurge');
            const lbl = document.getElementById('surgeLabel');
            const icon = document.getElementById('surgeIcon');

            if (btn && lbl && icon) {
                if (isSurgeActive) {
                    btn.className = "btn btn-sm btn-danger py-0 px-2";
                    btn.innerText = "End Surge";
                    lbl.innerText = "SURGE ACTIVE (3.0x)";
                    lbl.className = "small fw-bold text-danger";
                    icon.className = "fa-solid fa-bolt text-danger pulse-animation";
                } else {
                    btn.className = "btn btn-sm btn-outline-warning py-0 px-2";
                    btn.innerText = "Simulate 3x Surge";
                    lbl.innerText = "Normal Load (1.0x)";
                    lbl.className = "small fw-semibold text-light";
                    icon.className = "fa-solid fa-bolt text-warning";
                }
            }
            loadQueue();
            loadHospitalResources();
            loadAuditLogs();
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadBenchmarks() {
    try {
        const resp = await fetch('/api/benchmarks');
        const data = await resp.json();
        if (!data.success) return;

        const grid = document.getElementById('benchmarkGrid');
        grid.innerHTML = '';

        data.cases.forEach((c, idx) => {
            const col = document.createElement('div');
            col.className = "col-md-6 col-lg-3";
            col.innerHTML = `
                <div class="card h-100 border shadow-sm">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-dark">${c.id}</span>
                            <span class="badge bg-secondary">${c.category}</span>
                        </div>
                        <h6 class="fw-bold mb-1 text-dark">${c.title}</h6>
                        <p class="small text-muted mb-2">${c.description}</p>
                        <div class="small mb-3">
                            <div><strong>Vitals:</strong> HR ${c.hr} | BP ${c.sbp}/${c.dbp} | SpO2 ${c.saturation}% | AVPU: ${c.mental}</div>
                            <div><strong>Target Level:</strong> <span class="badge bg-primary">Level ${c.expected_level}</span></div>
                            <div class="text-secondary mt-1"><strong>Ward Target:</strong> ${c.expected_disposition}</div>
                        </div>
                        <button class="btn btn-sm btn-outline-primary w-100" onclick="loadCaseToForm(${idx})">
                            <i class="fa-solid fa-arrow-up-right-from-square me-1"></i> Load to Intake
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(col);
        });
    } catch (err) {
        console.error(err);
    }
}

async function runAllBenchmarkTests() {
    document.getElementById('benchmarkSummaryBox').classList.remove('d-none');
    try {
        const resp = await fetch('/api/benchmarks/run_all', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            const s = data.summary;
            document.getElementById('benchSafetyRate').innerText = `${s.clinical_safety_rate}%`;
            document.getElementById('benchExactMatches').innerText = `${s.exact_concordance} / ${s.total_cases}`;
            document.getElementById('benchSafeEscalations').innerText = `${s.safe_escalations}`;
            document.getElementById('benchUnderTriage').innerText = `${s.under_triage_errors}`;
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadCaseToForm(caseIdx) {
    const resp = await fetch('/api/benchmarks');
    const data = await resp.json();
    const c = data.cases[caseIdx];
    if (!c) return;

    const caseAadhaar = `99${String(caseIdx + 1).padStart(2, '0')}12345678`;
    if (intakeAadharController) {
        intakeAadharController.setValue(caseAadhaar);
    }
    document.getElementById('patient_name').value = `Benchmark Case ${c.id}`;
    document.getElementById('patient_age').value = c.patient_age;
    document.getElementById('patient_gender').value = c.patient_gender;
    document.getElementById('arrival_mode').value = c.arrival_mode;
    document.getElementById('injury').value = c.injury;
    document.getElementById('chief_complaint').value = c.chief_complaint;
    document.getElementById('mental').value = c.mental;
    document.getElementById('pain_flag').value = c.pain;
    document.getElementById('nrs_pain').value = c.nrs_pain;
    document.getElementById('sbp').value = c.sbp;
    document.getElementById('dbp').value = c.dbp;
    document.getElementById('heart_rate').value = c.hr;
    document.getElementById('resp_rate').value = c.rr;
    document.getElementById('temp_c').value = c.bt;
    document.getElementById('spo2').value = c.saturation;

    updateAgeNorms();
    updateDataCompleteness();
    switchTab('intake-tab');
    evaluatePatient();
}

function openOverrideModal() {
    new bootstrap.Modal(document.getElementById('overrideModal')).show();
}

function openOverrideModalForPatient(patientId) {
    currentPatientId = patientId;
    document.getElementById('overridePatientId').value = patientId;
    new bootstrap.Modal(document.getElementById('overrideModal')).show();
}

async function submitClinicianOverride() {
    const patientId = document.getElementById('overridePatientId').value || currentQueue[0]?.patient_id;
    const clinicianId = document.getElementById('overrideClinicianId').value.trim();
    const newLevel = document.getElementById('overrideNewLevel').value;
    const reasonCode = document.getElementById('overrideReasonCode').value;
    const notes = document.getElementById('overrideNotes').value.trim();

    if (!clinicianId || !newLevel || !notes) {
        alert("Please enter clinician ID, overridden level, and decision notes.");
        return;
    }

    const payload = {
        patient_id: patientId,
        new_level: parseInt(newLevel),
        reason_code: reasonCode,
        clinician_id: clinicianId,
        notes: notes
    };

    try {
        const resp = await fetch('/api/triage/override', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('overrideModal'))?.hide();
            loadQueue();
            loadAuditLogs();
            alert("Clinician override permanently recorded in MongoDB audit ledger.");
        } else {
            alert("Override error: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

function openRepeatVitalsModal(patientId) {
    currentPatientId = patientId;
    document.getElementById('repeatPatientId').value = patientId;
    new bootstrap.Modal(document.getElementById('repeatVitalsModal')).show();
}

async function submitRepeatVitals() {
    const hr = document.getElementById('repeat_hr').value;
    const rr = document.getElementById('repeat_rr').value;
    const sbp = document.getElementById('repeat_sbp').value;
    const spo2 = document.getElementById('repeat_spo2').value;

    if (!hr || !rr || !sbp || !spo2) {
        alert("Please enter all repeat vital signs.");
        return;
    }

    const payload = {
        patient_id: document.getElementById('repeatPatientId').value,
        vitals: {
            heart_rate: parseFloat(hr),
            resp_rate: parseFloat(rr),
            sbp: parseFloat(sbp),
            spo2: parseFloat(spo2)
        }
    };

    try {
        const resp = await fetch('/api/queue/update_vitals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('repeatVitalsModal'))?.hide();
            loadQueue();
            loadAuditLogs();
        } else {
            alert("Update error: " + data.error);
        }
    } catch (err) {
        console.error(err);
    }
}

async function loadAuditLogs(overridesOnly = false) {
    try {
        const resp = await fetch(`/api/audit/logs?overrides_only=${overridesOnly}`);
        const data = await resp.json();
        if (!data.success) return;

        const tbody = document.getElementById('auditTableBody');
        tbody.innerHTML = '';

        data.logs.forEach(l => {
            const tr = document.createElement('tr');
            if (l.is_override) tr.className = "table-warning";

            tr.innerHTML = `
                <td><span class="badge bg-dark">${l.log_id}</span></td>
                <td>${l.timestamp.substring(11, 19)}</td>
                <td class="fw-bold">${l.patient_name || (l.patient_id && !l.patient_id.startsWith('PT-') ? l.patient_id : 'Patient Record')}</td>
                <td><span class="badge bg-secondary">Level ${l.ai_level}</span></td>
                <td><span class="badge ${l.is_override ? 'bg-danger' : 'bg-primary'}">Level ${l.final_level}</span></td>
                <td>${l.is_override ? '<span class="badge bg-danger">OVERRIDE</span>' : '<span class="badge bg-light text-dark border">ACCEPTED</span>'}</td>
                <td>${l.clinician_id}</td>
                <td class="small" style="max-width: 250px;">
                    ${l.is_override ? `<strong>[${l.override_reason_code}]</strong> ${l.override_notes}` : (l.clinical_drivers ? l.clinical_drivers[0] : 'Standard intake accepted')}
                </td>
                <td class="small text-muted" title="${l.hash}">${l.hash ? l.hash.substring(0, 12) + '...' : 'SEALED'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
    }
}

function resetForm() {
    document.getElementById('triageForm').reset();
    clearIntakeAadhar();
    document.getElementById('patient_id_display').value = '';
    document.getElementById('patient_name').value = '';
    document.getElementById('patient_age').value = '';
    document.getElementById('patient_gender').value = '';
    document.getElementById('arrival_mode').value = '';
    document.getElementById('injury').value = '';
    document.getElementById('chief_complaint').value = '';
    document.getElementById('mental').value = '';
    document.getElementById('pain_flag').value = '';
    document.getElementById('nrs_pain').value = '';
    document.getElementById('sbp').value = '';
    document.getElementById('dbp').value = '';
    document.getElementById('heart_rate').value = '';
    document.getElementById('resp_rate').value = '';
    document.getElementById('temp_c').value = '';
    document.getElementById('spo2').value = '';
    
    document.getElementById('emptyResultPlaceholder').classList.remove('d-none');
    document.getElementById('evaluationOutput').classList.add('d-none');
    document.getElementById('evalStatusBadge').className = "badge bg-secondary";
    document.getElementById('evalStatusBadge').innerText = "Ready for Evaluation";
    
    const badge = document.getElementById('ageCategoryBadge');
    const hint = document.getElementById('ageNormsHint');
    if (badge) {
        badge.className = "badge bg-dark me-2";
        badge.innerText = "Age Category";
    }
    if (hint) {
        hint.innerText = "Enter age to view reference physiological norms";
    }
    updateDataCompleteness();
}
