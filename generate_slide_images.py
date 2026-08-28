"""
generate_slide_images.py - Generates clean, corporate MS-PowerPoint style PNG diagrams for slides.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'

# Colors: Professional Corporate PowerPoint Palette
NAVY = "#1F4E78"
BLUE = "#2F5597"
LIGHT_BLUE = "#D9E1F2"
TEAL = "#2E75B6"
LIGHT_TEAL = "#DEEBF7"
DARK_GRAY = "#262626"
LIGHT_GRAY = "#F2F2F2"
BORDER_GRAY = "#808080"
ALERT_RED = "#C00000"
LIGHT_RED = "#FCE4D6"
GREEN = "#385723"
LIGHT_GREEN = "#E2EFDA"

# ----------------- SLIDE 3: SYSTEM ARCHITECTURE -----------------
def create_slide3_image():
    fig, ax = plt.subplots(figsize=(12, 3.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.5)
    ax.axis('off')

    stages = [
        ("1. Client UI Layer", ["• Patient Intake Form", "• 82-Bed Matrix Grid", "• Dynamic Priority Queue"], LIGHT_TEAL, TEAL),
        ("2. Flask API Gateway", ["• /api/triage (ML & Bed Lock)", "• /api/patient (Identity)", "• /api/resources & doctors"], LIGHT_BLUE, BLUE),
        ("3. Decision Engine", ["• 10:1 Cost-Sensitive ML", "• Age-Stratified Norms", "• Red-Flag Overrides"], LIGHT_GREEN, GREEN),
        ("4. MongoDB Database", ["• hospital_db (Port 27017)", "• patients & admissions", "• resources & audit_logs"], LIGHT_GRAY, NAVY)
    ]

    for i, (title, points, bg_col, border_col) in enumerate(stages):
        x = 0.3 + i * 2.9
        y = 0.4
        w = 2.6
        h = 2.7
        # Card
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", fc=bg_col, ec=border_col, lw=2)
        ax.add_patch(rect)
        # Header banner
        header = patches.FancyBboxPatch((x, y + h - 0.6), w, 0.6, boxstyle="round,pad=0.05", fc=border_col, ec=border_col)
        ax.add_patch(header)
        ax.text(x + w/2, y + h - 0.3, title, color="white", fontsize=11, fontweight="bold", ha="center", va="center")
        # Bullet points
        for j, pt in enumerate(points):
            ax.text(x + 0.15, y + h - 0.95 - (j * 0.55), pt, color=DARK_GRAY, fontsize=9.5, ha="left", va="center")
        # Arrow
        if i < 3:
            ax.annotate('', xy=(x + w + 0.28, y + h/2), xytext=(x + w + 0.02, y + h/2),
                        arrowprops=dict(arrowstyle="-|>", lw=2.5, color=NAVY, mutation_scale=15))

    plt.tight_layout()
    plt.savefig("slide3_architecture.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide3_architecture.png")

# ----------------- SLIDE 4: DECISION PIPELINE -----------------
def create_slide4_image():
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis('off')

    # 1. Intake Box
    rect1 = patches.FancyBboxPatch((0.2, 1.5), 1.8, 1.5, boxstyle="round,pad=0.08", fc=LIGHT_BLUE, ec=BLUE, lw=2)
    ax.add_patch(rect1)
    ax.text(1.1, 2.25, "Patient Intake\n(Age, Vitals, Pain)", color=NAVY, fontsize=10, fontweight="bold", ha="center", va="center")

    # 2. Age Stratification Box
    rect2 = patches.FancyBboxPatch((2.6, 0.4), 2.2, 3.7, boxstyle="round,pad=0.08", fc=LIGHT_GRAY, ec=BORDER_GRAY, lw=2)
    ax.add_patch(rect2)
    ax.text(3.7, 3.8, "Age-Stratified Norms", color=DARK_GRAY, fontsize=10.5, fontweight="bold", ha="center")
    
    # Sub-boxes
    p_box = patches.FancyBboxPatch((2.75, 2.65), 1.9, 0.9, boxstyle="square,pad=0.05", fc="white", ec=TEAL, lw=1.5)
    ax.add_patch(p_box)
    ax.text(3.7, 3.1, "Pediatric (< 18y)\nPEWS, Fever ≥ 38.5°C", fontsize=8.5, ha="center", va="center")

    a_box = patches.FancyBboxPatch((2.75, 1.55), 1.9, 0.9, boxstyle="square,pad=0.05", fc="white", ec=BLUE, lw=1.5)
    ax.add_patch(a_box)
    ax.text(3.7, 2.0, "Adult (18–64y)\nShock Index, qSOFA", fontsize=8.5, ha="center", va="center")

    g_box = patches.FancyBboxPatch((2.75, 0.55), 1.9, 0.85, boxstyle="square,pad=0.05", fc="white", ec=NAVY, lw=1.5)
    ax.add_patch(g_box)
    ax.text(3.7, 0.95, "Geriatric (≥ 65y)\nBlunted Fever, Delirium", fontsize=8.5, ha="center", va="center")

    # 3. Dual Check Box
    rect3 = patches.FancyBboxPatch((5.4, 0.6), 2.2, 3.3, boxstyle="round,pad=0.08", fc=LIGHT_GRAY, ec=BORDER_GRAY, lw=2)
    ax.add_patch(rect3)
    ax.text(6.5, 3.6, "Dual Safety Pipeline", color=DARK_GRAY, fontsize=10.5, fontweight="bold", ha="center")

    red_box = patches.FancyBboxPatch((5.55, 2.2), 1.9, 1.1, boxstyle="square,pad=0.05", fc=LIGHT_RED, ec=ALERT_RED, lw=1.5)
    ax.add_patch(red_box)
    ax.text(6.5, 2.75, "Red-Flag Scanner\nSpO2<90% / SBP≤80\n-> Forces Level 1/2", color=ALERT_RED, fontsize=8.5, fontweight="bold", ha="center", va="center")

    ml_box = patches.FancyBboxPatch((5.55, 0.8), 1.9, 1.1, boxstyle="square,pad=0.05", fc=LIGHT_GREEN, ec=GREEN, lw=1.5)
    ax.add_patch(ml_box)
    ax.text(6.5, 1.35, "10:1 Cost-ML Scorer\nMulti-Output Model\n(Acuity 1-5 & Risk %)", color=GREEN, fontsize=8.5, fontweight="bold", ha="center", va="center")

    # 4. Final Output Box
    rect4 = patches.FancyBboxPatch((8.1, 1.3), 1.7, 1.9, boxstyle="round,pad=0.08", fc=LIGHT_TEAL, ec=TEAL, lw=2)
    ax.add_patch(rect4)
    ax.text(8.95, 2.25, "Final Triage Output\n• Triage Level (1-5)\n• Admission Risk %\n• Target Bed ID", color=NAVY, fontsize=9.5, fontweight="bold", ha="center", va="center")

    # Arrows
    ax.annotate('', xy=(2.55, 2.25), xytext=(2.02, 2.25), arrowprops=dict(arrowstyle="-|>", lw=2, color=NAVY))
    ax.annotate('', xy=(5.35, 2.25), xytext=(4.85, 2.25), arrowprops=dict(arrowstyle="-|>", lw=2, color=NAVY))
    ax.annotate('', xy=(8.05, 2.25), xytext=(7.65, 2.25), arrowprops=dict(arrowstyle="-|>", lw=2, color=NAVY))

    plt.tight_layout()
    plt.savefig("slide4_decision_pipeline.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide4_decision_pipeline.png")

# ----------------- SLIDE 7: PATIENT LIFECYCLE -----------------
def create_slide7_image():
    fig, ax = plt.subplots(figsize=(11, 2.4), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2.4)
    ax.axis('off')

    steps = [
        ("1. Aadhaar Intake", "Deterministic UHID\n(PT-4321-5482)\nRead-Only Lookup", LIGHT_BLUE, BLUE),
        ("2. Bed Lock & Admit", "Insert 'admissions'\nLock Target Bed\n(status: Occupied)", LIGHT_GREEN, GREEN),
        ("3. Step-Down Transfer", "ICU -> General Ward\nOld Bed -> Cleaning\nNew Bed -> Occupied", LIGHT_TEAL, TEAL),
        ("4. 1-Click Discharge", "Bed -> Under_Cleaning\nReturn Ventilator/O2\nStatus: DISCHARGED", LIGHT_GRAY, NAVY)
    ]

    for i, (title, desc, bg_col, border_col) in enumerate(steps):
        x = 0.2 + i * 2.7
        y = 0.2
        w = 2.45
        h = 2.0
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=bg_col, ec=border_col, lw=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + 1.5, title, color=border_col, fontsize=11, fontweight="bold", ha="center")
        ax.text(x + w/2, y + 0.65, desc, color=DARK_GRAY, fontsize=9, ha="center", va="center")
        if i < 3:
            ax.annotate('', xy=(x + w + 0.23, y + h/2), xytext=(x + w + 0.02, y + h/2),
                        arrowprops=dict(arrowstyle="-|>", lw=2.5, color=NAVY, mutation_scale=15))

    plt.tight_layout()
    plt.savefig("slide7_patient_lifecycle.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide7_patient_lifecycle.png")

# ----------------- SLIDE 8: QUEUE & DETERIORATION -----------------
def create_slide8_image():
    fig, ax = plt.subplots(figsize=(9, 4), dpi=300)
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # Step 1
    r1 = patches.FancyBboxPatch((0.2, 1.2), 2.2, 1.6, boxstyle="round,pad=0.08", fc=LIGHT_BLUE, ec=BLUE, lw=2)
    ax.add_patch(r1)
    ax.text(1.3, 2.0, "Waiting Room Queue\nEnforces Safe Limits:\n• L1: 0m  • L2: ≤10m\n• L3: ≤30m • L4: ≤60m", color=NAVY, fontsize=9.5, fontweight="bold", ha="center", va="center")

    # Step 2
    r2 = patches.FancyBboxPatch((3.0, 1.2), 2.4, 1.6, boxstyle="round,pad=0.08", fc=LIGHT_GRAY, ec=BORDER_GRAY, lw=2)
    ax.add_patch(r2)
    ax.text(4.2, 2.0, "Bedside Monitoring\n• Time Breach Tracking\n• Repeat Vitals Entry\n(Delta Evaluation)", color=DARK_GRAY, fontsize=9.5, fontweight="bold", ha="center", va="center")

    # Step 3 Top: Time breach
    r3a = patches.FancyBboxPatch((6.0, 2.3), 2.7, 1.4, boxstyle="round,pad=0.08", fc=LIGHT_RED, ec=ALERT_RED, lw=2)
    ax.add_patch(r3a)
    ax.text(7.35, 3.0, "Time-Limit Breach Alert\nFlashes Red Alert Banner\nPrompts Immediate Review", color=ALERT_RED, fontsize=9, fontweight="bold", ha="center", va="center")

    # Step 3 Bottom: Decompensation
    r3b = patches.FancyBboxPatch((6.0, 0.4), 2.7, 1.5, boxstyle="round,pad=0.08", fc=LIGHT_RED, ec=ALERT_RED, lw=2)
    ax.add_patch(r3b)
    ax.text(7.35, 1.15, "Decompensation Alarm\n(e.g. SpO2 drops 96% -> 88%)\n1. Escalates Triage Acuity\n2. Auto-Bumps to Top of Queue", color=ALERT_RED, fontsize=9, fontweight="bold", ha="center", va="center")

    # Connectors
    ax.annotate('', xy=(2.95, 2.0), xytext=(2.45, 2.0), arrowprops=dict(arrowstyle="-|>", lw=2, color=NAVY))
    ax.annotate('', xy=(5.95, 3.0), xytext=(5.45, 2.2), arrowprops=dict(arrowstyle="-|>", lw=2, color=ALERT_RED))
    ax.annotate('', xy=(5.95, 1.15), xytext=(5.45, 1.8), arrowprops=dict(arrowstyle="-|>", lw=2, color=ALERT_RED))

    plt.tight_layout()
    plt.savefig("slide8_queue_deterioration.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide8_queue_deterioration.png")

# ----------------- SLIDE 9: SURGE ROUTING -----------------
def create_slide9_image():
    fig, ax = plt.subplots(figsize=(9, 3.8), dpi=300)
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 3.8)
    ax.axis('off')

    # Influx
    r1 = patches.FancyBboxPatch((0.2, 1.1), 2.2, 1.6, boxstyle="round,pad=0.08", fc=LIGHT_RED, ec=ALERT_RED, lw=2)
    ax.add_patch(r1)
    ax.text(1.3, 1.9, "3x Surge Influx\n(Mass-Casualty Event /\nSeasonal Epidemic)", color=ALERT_RED, fontsize=10, fontweight="bold", ha="center", va="center")

    # Acute Path
    r2 = patches.FancyBboxPatch((3.8, 2.1), 4.8, 1.4, boxstyle="round,pad=0.08", fc=LIGHT_BLUE, ec=BLUE, lw=2)
    ax.add_patch(r2)
    ax.text(6.2, 2.8, "High-Acuity Pathway (Levels 1, 2, 3)\n• Direct to ICU, HDU & Trauma OT Suites\n• Monitored Beds & Ventilators 100% Protected", color=NAVY, fontsize=9.5, fontweight="bold", ha="center", va="center")

    # Fast-Track Path
    r3 = patches.FancyBboxPatch((3.8, 0.4), 4.8, 1.4, boxstyle="round,pad=0.08", fc=LIGHT_GREEN, ec=GREEN, lw=2)
    ax.add_patch(r3)
    ax.text(6.2, 1.1, "Fast-Track Diversion (Levels 4, 5)\n• Diverted to Outpatient Ambulatory Pods\n• Critical Patient Delay Reduced by -64.1%", color=GREEN, fontsize=9.5, fontweight="bold", ha="center", va="center")

    # Split arrows
    ax.annotate('', xy=(3.75, 2.8), xytext=(2.45, 2.2), arrowprops=dict(arrowstyle="-|>", lw=2.5, color=BLUE))
    ax.annotate('', xy=(3.75, 1.1), xytext=(2.45, 1.6), arrowprops=dict(arrowstyle="-|>", lw=2.5, color=GREEN))

    plt.tight_layout()
    plt.savefig("slide9_surge_routing.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide9_surge_routing.png")

# ----------------- SLIDE 10: AUDIT LEDGER -----------------
def create_slide10_image():
    fig, ax = plt.subplots(figsize=(11, 2.4), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 2.4)
    ax.axis('off')

    steps = [
        ("1. AI Recommendation", "Triage Level (1-5)\nAdmission Risk %\nTarget Bed Proposal", LIGHT_BLUE, BLUE),
        ("2. Clinician Review", "Licensed Nurse / Doctor\n• Accept & Admit\n• Mandatory Override Log", LIGHT_GRAY, DARK_GRAY),
        ("3. Direct Action", "Lock Bed in MongoDB\nUpdate hospital_resources\nNotify On-Duty Doctor", LIGHT_GREEN, GREEN),
        ("4. SHA-256 Audit Trail", "Chained Hash Block\nHIPAA §164.312(b)\nGDPR Art. 22 Compliant", LIGHT_TEAL, TEAL)
    ]

    for i, (title, desc, bg_col, border_col) in enumerate(steps):
        x = 0.2 + i * 2.7
        y = 0.2
        w = 2.45
        h = 2.0
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=bg_col, ec=border_col, lw=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + 1.5, title, color=border_col, fontsize=11, fontweight="bold", ha="center")
        ax.text(x + w/2, y + 0.65, desc, color=DARK_GRAY, fontsize=9, ha="center", va="center")
        if i < 3:
            ax.annotate('', xy=(x + w + 0.23, y + h/2), xytext=(x + w + 0.02, y + h/2),
                        arrowprops=dict(arrowstyle="-|>", lw=2.5, color=NAVY, mutation_scale=15))

    plt.tight_layout()
    plt.savefig("slide10_audit_ledger.png", dpi=300, bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    print("Saved slide10_audit_ledger.png")

if __name__ == '__main__':
    create_slide3_image()
    create_slide4_image()
    create_slide7_image()
    create_slide8_image()
    create_slide9_image()
    create_slide10_image()
    print("All 6 Slide PNG images generated successfully!")
