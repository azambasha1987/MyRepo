#!/usr/bin/env python3
"""
Azam-Pnet Enterprise Operations Manual - PDF Generator
Generates a comprehensive, professional operations manual detailing:
- Executive Architectural Taxonomy & Feature Placements
- Master vs. Satellite Dual-Plane Architecture & Alignment Matrix
- Exact UI & System Placements
- Step-by-Step Operator Usage Workflows ("How to use")
- Step-by-Step Under-the-Hood Technical Lifecycles ("What happens in the background")
- Enterprise CLI Command-Line Reference
- Future VM Provisioning & Verification
for all 25 Enterprise features + 9 advanced enhancements of Azam-Pnet.
"""

import os
import sys
import shutil
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# --- Numbered Canvas for Two-Pass Page Numbering ---
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        print(f"[INFO] Document compiled with {num_pages} total pages.")
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(54, 750, "AZAM-PNET ENTERPRISE PLATFORM")
            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 54, 750, "OPERATIONS & ARCHITECTURE MANUAL")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 742, 612 - 54, 742)

            # Footer
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(54, 45, 612 - 54, 45)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(54, 32, "Confidential - For Azam-Pnet Infrastructure Administrators Only")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 54, 32, page_text)
        self.restoreState()


def build_pdf(filename_dest):
    doc = SimpleDocTemplate(
        filename_dest,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0F172A")    # Slate 900
    c_secondary = colors.HexColor("#1E3A8A")  # Blue 900
    c_accent = colors.HexColor("#4F46E5")     # Indigo 600
    c_teal = colors.HexColor("#0D9488")       # Teal 600
    c_dark = colors.HexColor("#1E293B")       # Slate 800
    c_muted = colors.HexColor("#475569")      # Slate 600
    c_light_bg = colors.HexColor("#F8FAFC")   # Slate 50
    c_border = colors.HexColor("#E2E8F0")     # Slate 200
    c_badge_bg = colors.HexColor("#EEF2FF")   # Indigo 50
    c_badge_border = colors.HexColor("#C7D2FE")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=c_primary,
        alignment=0,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_muted,
        alignment=0,
        spaceAfter=16
    )

    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=20,
        textColor=c_secondary,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    feature_heading = ParagraphStyle(
        'FeatHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=c_primary,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=c_dark,
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    step_title_user = ParagraphStyle(
        'StepUser',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=c_secondary,
        spaceBefore=3,
        spaceAfter=2,
        keepWithNext=True
    )

    step_title_bg = ParagraphStyle(
        'StepBg',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=c_teal,
        spaceBefore=3,
        spaceAfter=2,
        keepWithNext=True
    )

    step_text = ParagraphStyle(
        'StepText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=c_dark,
        leftIndent=10,
        spaceAfter=2.5
    )

    placement_box_text = ParagraphStyle(
        'PlacementText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11.5,
        textColor=c_secondary
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=c_dark
    )

    story = []

    # ==================== COVER / TITLE SECTION ====================
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<font color='#4F46E5'><b>AZAM-PNET ENTERPRISE PLATFORM &bull; SYSTEM DOCUMENTATION</b></font>",
        ParagraphStyle('Pill', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, spaceAfter=6)
    ))
    story.append(Paragraph("Enterprise Features & Architecture Operations Manual", title_style))
    story.append(Paragraph(
        "A Comprehensive Reference to Dual-Plane Master & Satellite Taxonomy, UI Placements, Operator Workflows, and Technical Background Lifecycles",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=c_accent, spaceBefore=0, spaceAfter=10))

    # Metadata Card Table
    meta_data = [
        [
            Paragraph("<b>Target System:</b> Azam-Pnet / PNETLab Enterprise", table_cell_style),
            Paragraph("<b>Document Version:</b> 2.5.0-LTS Enterprise Edition", table_cell_style)
        ],
        [
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}", table_cell_style),
            Paragraph("<b>Architectural Planes:</b> Master Control Plane + Satellite Compute Plane", table_cell_style)
        ],
        [
            Paragraph("<b>System Daemons:</b> azambasha-ops-api (:8088), azam-watchdog.service", table_cell_style),
            Paragraph("<b>Security & Role Guard:</b> RBAC Admin Guard (Role 0) + Airgap Packaging", table_cell_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[250, 254])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # ==================== SECTION 1: ARCHITECTURAL OVERVIEW ====================
    story.append(Paragraph("1. Executive Architectural Taxonomy & Feature Placements", section_heading))
    story.append(Paragraph(
        "Azam-Pnet organizes all twenty-five enterprise capabilities across three deliberate user and runtime environments: "
        "<b>Outside-the-Lab Canvas</b> (global hypervisor diagnostics, template repository marketplace, multi-cloud and offline air-gapped backups, capacity planning, and SSL automation accessed from the main administrative dashboard), "
        "<b>Inside-the-Lab Canvas</b> (in-workbench workflow tools, live traffic bandwidth heatmaps, OS-level desktop push notifications, anti-bootstorm staggered startup with KSM deduplication, Git version control, and live Wireshark packet capture available right inside the active topology view), and "
        "<b>Autonomous Kernel & Background Daemons</b> (24/7 self-healing watchdogs, Soft-RoCE RXE MTU 9000 kernel engines, MySQL socket auto-healers, and nightly SSD TRIM cron jobs running continuously in the host background).",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Taxonomy Matrix Table
    matrix_data = [
        [
            Paragraph("Feature Name", table_header_style),
            Paragraph("Architectural Zone", table_header_style),
            Paragraph("Exact UI / System Location", table_header_style),
            Paragraph("Primary Trigger", table_header_style),
            Paragraph("Plane Support", table_header_style)
        ],
        # Outside
        [Paragraph("1. Community Templates Marketplace", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Community Templates", table_cell_style), Paragraph("One-Click Import", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("2. Live Hot-Node Profiler (RBAC Guard)", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Health &amp; Diagnostics", table_cell_style), Paragraph("Real-Time / Kill", table_cell_style), Paragraph("Master &amp; CLI", table_cell_style)],
        [Paragraph("3. HTML5 Console Session Reset", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Console Fixer", table_cell_style), Paragraph("Repair Button", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("4. Local, Cloud &amp; Air-Gapped Backups", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Cloud &amp; Local Backup", table_cell_style), Paragraph("Instant Archive", table_cell_style), Paragraph("Master &amp; CLI", table_cell_style)],
        [Paragraph("5. Fleet Multi-Node Cluster Monitor", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Cluster Nodes", table_cell_style), Paragraph("Auto-Refresh (15s)", table_cell_style), Paragraph("Master (Agent: Sat)", table_cell_style)],
        [Paragraph("6. Lab Hardware Capacity Planner", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Capacity Planner", table_cell_style), Paragraph("Interactive Sizer", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("7. Comprehensive Diagnostic Doctor", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; System Doctor", table_cell_style), Paragraph("Run Diagnostics", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("8. QCOW2 Disk Shrinker &amp; Sparse Comp.", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Storage Optimizer", table_cell_style), Paragraph("Batch Compress", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("9. Multi-Cloud Transit Overlay Bridge", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Cloud Transit", table_cell_style), Paragraph("Connect Overlay", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("10. Automated SSL &amp; WhatsApp Alerts", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Alerts &amp; SSL", table_cell_style), Paragraph("Deploy Cert / Test", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("11. Version Synchronizer &amp; PDF Portal", table_cell_style), Paragraph("Outside Lab", table_cell_style), Paragraph("Main Nav &gt; Azam Features &gt; Updates &amp; Header Doc", table_cell_style), Paragraph("Check &amp; Update", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        # Inside
        [Paragraph("12. Anti-Bootstorm &amp; In-Canvas KSM", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Top Toolbar &gt; Anti-Bootstorm", table_cell_style), Paragraph("Toolbar Button", table_cell_style), Paragraph("Master (KSM: Both)", table_cell_style)],
        [Paragraph("13. Topology Git VCS &amp; Auto-Commit", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Left Sidebar &gt; Git VCS Icon &gt; Drawer", table_cell_style), Paragraph("Auto / Commit", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("14. In-Workbench Quick Console Healer", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Top Toolbar &gt; Fix Console", table_cell_style), Paragraph("Toolbar Button", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("15. Live Wireshark &amp; Traffic Heatmap", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Top Toolbar &gt; Heatmap / Right-Click &gt; Capture", table_cell_style), Paragraph("Toolbar &amp; Menu", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("16. AI Lab Copilot &amp; Desktop Alerts", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Bottom-Right &gt; Floating AI &amp; OS Notif", table_cell_style), Paragraph("Chat &amp; Event Hook", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("17. Multi-Node Config Diff &amp; Rollback", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Management Tools &gt; Config Diff", table_cell_style), Paragraph("Compare Configs", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("18. Automated Lab Exam Grader", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Lab Actions &gt; Run Evaluation", table_cell_style), Paragraph("Evaluate Lab", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("19. Ping Mesh &amp; Traffic Generator", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Lab Testing &gt; Traffic Injector", table_cell_style), Paragraph("Generate Traffic", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("20. High-Res Diagram &amp; SVG Exporter", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Workbench &gt; Export &gt; Vector Topology", table_cell_style), Paragraph("Download SVG", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("21. Interactive Canvas Accelerators", table_cell_style), Paragraph("Inside Canvas", table_cell_style), Paragraph("Canvas Navigation Controls (Minimap &amp; Snap)", table_cell_style), Paragraph("Always Active", table_cell_style), Paragraph("Master Only", table_cell_style)],
        # Background
        [Paragraph("22. 24/7 Self-Healing Watchdog", table_cell_style), Paragraph("Daemon Plane", table_cell_style), Paragraph("systemd: azam-watchdog.service", table_cell_style), Paragraph("Autonomous (60s)", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("23. MySQL Socket &amp; Credential Healer", table_cell_style), Paragraph("Daemon Plane", table_cell_style), Paragraph("systemd &amp; Cron: azambasha-fix-web-credentials", table_cell_style), Paragraph("On Boot &amp; Hourly", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("24. Soft-RoCE RXE &amp; Jumbo MTU Engine", table_cell_style), Paragraph("Kernel Plane", table_cell_style), Paragraph("Kernel Module (ib_core, rdma_rxe) &amp; udev", table_cell_style), Paragraph("Boot &amp; Net Hook", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("25. Scheduled Maintenance &amp; TRIM Cron", table_cell_style), Paragraph("Daemon Plane", table_cell_style), Paragraph("cron.d: azambasha-maintenance-trim", table_cell_style), Paragraph("Daily 03:00 UTC", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
    ]

    t_matrix = Table(matrix_data, colWidths=[130, 65, 160, 75, 74])
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_secondary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('BOX', (0, 0), (-1, -1), 1, c_secondary),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg])
    ]))
    story.append(t_matrix)
    story.append(PageBreak())

    # ==================== SECTION 2: MASTER VS SATELLITE DUAL-PLANE ARCHITECTURE ====================
    story.append(Paragraph("2. Master vs. Satellite Dual-Plane Architecture & Alignment Matrix", section_heading))
    story.append(Paragraph(
        "A foundational design principle of the Azam-Pnet Enterprise distribution is strict <b>architectural role separation</b> between "
        "the <b>Master Management Node</b> (the control plane) and <b>Satellite Compute Nodes</b> (the data and execution plane). "
        "Understanding this dual plane is critical for multi-hypervisor cluster deployments.",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>1. Master Node Architectural Role (Control &amp; Presentation Plane):</b>", body_bold))
    story.append(Paragraph(
        "The Master Node hosts the central user interface (Apache2/Nginx), the MariaDB database engine, the Guacamole HTML5 console proxy (guacd and tomcat9), "
        "the central REST API daemon (<code>azambasha-ops-api</code> on port 8088), the Git topology repository root, and all interactive canvas workbench tools. "
        "Administrators and lab students log into the Master Node URL. When a heavy multi-vendor lab topology is launched across a cluster, the Master Node acts as the "
        "orchestrator, assigning virtual machine workloads to Satellite compute nodes according to real-time RAM and CPU availability.",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>2. Satellite Node Architectural Role (Headless High-Performance Compute Plane):</b>", body_bold))
    story.append(Paragraph(
        "Satellite nodes are dedicated, bare-metal or nested KVM execution engines. Their primary responsibility is running heavy virtual machines "
        "(e.g., Cisco IOS-XRv9k, Arista cEOS, Junos vMX, Linux appliances) with zero CPU cycles wasted on unnecessary web servers, SQL databases, or desktop environments. "
        "Therefore, Satellite nodes operate in a <b>headless compute state</b>. Running <code>azambasha-install-azam-features.sh --satellite</code> on a satellite node "
        "purposefully provisions all 26 CLI system tools, installs the 24/7 watchdog daemon (<code>azam-watchdog.service</code>), tunes Kernel Samepage Merging (KSM), "
        "loads Soft-RoCE RXE acceleration with MTU 9000 jumbo frames, and installs the nightly SSD TRIM maintenance cron, while omitting Apache, Guacamole, and MariaDB.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Parity Matrix Table
    parity_data = [
        [
            Paragraph("Platform Component / Feature", table_header_style),
            Paragraph("Master Node Execution", table_header_style),
            Paragraph("Satellite Node Execution", table_header_style),
            Paragraph("Parity &amp; Architectural Rationale", table_header_style)
        ],
        [
            Paragraph("<b>Web GUI &amp; Canvas Workbench</b>", table_cell_style),
            Paragraph("Active (Apache2 / PHP / HTML5)", table_cell_style),
            Paragraph("Disabled (Zero Web Overhead)", table_cell_style),
            Paragraph("<b>Aligned:</b> Satellites are headless compute workers; users access central Master GUI.", table_cell_style)
        ],
        [
            Paragraph("<b>azambasha-ops-api (:8088)</b>", table_cell_style),
            Paragraph("Active (Central REST Engine)", table_cell_style),
            Paragraph("Active or Cluster-Bridged", table_cell_style),
            Paragraph("<b>Aligned:</b> Master serves endpoints; Satellites expose node telemetry via cluster hooks.", table_cell_style)
        ],
        [
            Paragraph("<b>24/7 System Watchdog</b>", table_cell_style),
            Paragraph("Active (<code>azam-watchdog.service</code>)", table_cell_style),
            Paragraph("Active (<code>azam-watchdog.service</code>)", table_cell_style),
            Paragraph("<b>100% Identical:</b> Watchdog self-heals KVM, bridges, and processes on both planes.", table_cell_style)
        ],
        [
            Paragraph("<b>Enterprise CLI Suite (26 Tools)</b>", table_cell_style),
            Paragraph("Linked in <code>/usr/local/bin/</code>", table_cell_style),
            Paragraph("Linked in <code>/usr/local/bin/</code>", table_cell_style),
            Paragraph("<b>100% Identical:</b> Administrators have identical CLI commands on every host.", table_cell_style)
        ],
        [
            Paragraph("<b>Kernel Samepage Merging (KSM)</b>", table_cell_style),
            Paragraph("Enabled &amp; Tuned", table_cell_style),
            Paragraph("Enabled &amp; Aggressively Tuned", table_cell_style),
            Paragraph("<b>100% Identical:</b> Maximizes memory deduplication across identical appliances.", table_cell_style)
        ],
        [
            Paragraph("<b>Soft-RoCE RXE &amp; MTU 9000</b>", table_cell_style),
            Paragraph("Loaded (<code>rdma_rxe, ib_core</code>)", table_cell_style),
            Paragraph("Loaded (<code>rdma_rxe, ib_core</code>)", table_cell_style),
            Paragraph("<b>100% Identical:</b> Unlocks wire-speed inter-node packet fabric without fragmentation.", table_cell_style)
        ],
        [
            Paragraph("<b>SSD TRIM &amp; Log Maintenance</b>", table_cell_style),
            Paragraph("Scheduled (Nightly 03:00 UTC)", table_cell_style),
            Paragraph("Scheduled (Nightly 03:00 UTC)", table_cell_style),
            Paragraph("<b>100% Identical:</b> Reclaims deleted flash blocks and purges stale sockets.", table_cell_style)
        ],
        [
            Paragraph("<b>MariaDB &amp; Guacamole Socket Fixer</b>", table_cell_style),
            Paragraph("Active (Database on Master)", table_cell_style),
            Paragraph("Not Applicable (Headless)", table_cell_style),
            Paragraph("<b>Aligned:</b> Satellites do not host MySQL or Guacamole; no repair needed.", table_cell_style)
        ],
        [
            Paragraph("<b>Air-Gapped Pack Bundler</b>", table_cell_style),
            Paragraph("Full Pack Generator (GUI &amp; CLI)", table_cell_style),
            Paragraph("CLI Extractor / Consumer", table_cell_style),
            Paragraph("<b>Aligned:</b> Master builds the tarball; Satellites consume bundle for air-gapped install.", table_cell_style)
        ]
    ]
    t_parity = Table(parity_data, colWidths=[120, 110, 110, 164])
    t_parity.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_secondary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('BOX', (0, 0), (-1, -1), 1, c_secondary),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg])
    ]))
    story.append(t_parity)
    story.append(PageBreak())

    # Helper function to format each feature entry
    def render_feature(feat_id, feat_name, category_tag, placement_path, how_to_steps, bg_steps):
        elements = []
        
        # Header + Tag
        header_text = f"<b>{feat_id}. {feat_name}</b> &nbsp;&nbsp;<font size=7 color='#4F46E5'><b>[{category_tag}]</b></font>"
        elements.append(Paragraph(header_text, feature_heading))

        # Placement Callout Box
        placement_content = [
            [Paragraph(f"<b>UI &amp; System Placement:</b> {placement_path}", placement_box_text)]
        ]
        t_place = Table(placement_content, colWidths=[504])
        t_place.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_badge_bg),
            ('BOX', (0, 0), (-1, -1), 0.75, c_badge_border),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_place)
        elements.append(Spacer(1, 3))

        # How to use step by step
        elements.append(Paragraph("<b>Operator Workflow (Step-by-Step How-To):</b>", step_title_user))
        for step in how_to_steps:
            elements.append(Paragraph(f"&bull;&nbsp; {step}", step_text))

        # What happens in background step by step
        elements.append(Paragraph("<b>Internal Mechanics &amp; Background Execution Lifecycle:</b>", step_title_bg))
        for bg in bg_steps:
            elements.append(Paragraph(f"&bull;&nbsp; {bg}", step_text))

        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceBefore=2, spaceAfter=6))
        return elements

    # ==================== SECTION 3: OUTSIDE-THE-LAB FEATURES ====================
    story.append(Paragraph("3. Outside-the-Lab Features (Main Dashboard: /main/#/azam-features)", section_heading))
    story.append(Paragraph(
        "Outside-the-lab features are located in the primary management dashboard (<code>/main/#/azam-features</code>) accessible prior to loading any topology. "
        "They provide centralized hypervisor monitoring, repository synchronizations, fleet health oversight, air-gapped bundling, RBAC access control, and disaster recovery.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Feature 1: Templates Marketplace
    f1_how = [
        "<b>Step 1:</b> Navigate to the top administrative bar and click <b>Azam Features</b> (or open URL <code>/main/#/azam-features</code>).",
        "<b>Step 2:</b> Select the <b>Community Templates</b> tab located in the left navigation sidebar.",
        "<b>Step 3:</b> Browse or filter the community catalog (Cisco, Arista, Juniper, Fortinet, Linux, MikroTik).",
        "<b>Step 4:</b> Click the <b>Import Template</b> button next to the desired network operating system template.",
        "<b>Step 5:</b> Observe the live progress bar as image schemas and YAML definitions are verified."
    ]
    f1_bg = [
        "<b>Step 1:</b> Front-end sends HTTP <code>GET /api/azam/templates</code> to <code>azambasha-ops-api</code> (port 8088).",
        "<b>Step 2:</b> API server reads <code>/opt/unetlab/html/templates/</code> and parses device definitions.",
        "<b>Step 3:</b> When import is clicked, API issues <code>POST /api/azam/templates/import</code> with template ID.",
        "<b>Step 4:</b> Python backend queries repository manifest schemas or git repository.",
        "<b>Step 5:</b> Verifies template file syntax, generates corresponding <code>/opt/unetlab/html/templates/{os}.yml</code>, sets permissions to <code>www-data:www-data 0644</code>, and flushes APC/OpCache."
    ]
    for el in render_feature("1", "Community Templates Marketplace", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Community Templates</b> tab (<code>#pane-templates</code>)",
                             f1_how, f1_bg):
        story.append(el)

    # Feature 2: Hot-Node Profiler + RBAC
    f2_how = [
        "<b>Step 1:</b> Navigate to <code>/main/#/azam-features</code> and select the <b>Health & Diagnostics</b> tab.",
        "<b>Step 2:</b> Scroll down to the <b>Hot-Node Live Performance Table</b>.",
        "<b>Step 3:</b> Inspect real-time consumption showing PID, Node Name, Lab Name, CPU %, and Memory %.",
        "<b>Step 4:</b> If a node is looping or hung, click the red <b>Kill Process</b> button in the Action column.",
        "<b>Step 5:</b> If logged in as non-admin, the system enforces RBAC: process termination is disabled and locked to Admin role 0 only."
    ]
    f2_bg = [
        "<b>Step 1:</b> Front-end polls <code>GET /api/azam/perf/top</code> every 4 seconds.",
        "<b>Step 2:</b> Backend runs <code>ps aux --sort=-%cpu</code>, filtering for QEMU (<code>qemu-system-x86_64</code>), IOL, and Dynamips.",
        "<b>Step 3:</b> Correlates PID to Lab UUID and Node ID via <code>/opt/unetlab/tmp/</code> sockets.",
        "<b>Step 4:</b> On Kill trigger, <code>POST /azam-ops/api/perf-kill</code> inspects the <code>X-User-Role</code> header; if not role 0 (Admin), returns HTTP 403 Forbidden.",
        "<b>Step 5:</b> For authorized admins, sends <code>SIGTERM</code> (15) to PID; if unresponsive after 2.5s, sends <code>SIGKILL</code> (9) and logs to <code>/var/log/azam-ops-api.log</code>."
    ]
    for el in render_feature("2", "Live Hot-Node Profiler & Task Manager (RBAC Guard)", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Health & Diagnostics</b> (<code>#pane-health</code>)",
                             f2_how, f2_bg):
        story.append(el)

    # Feature 3: HTML5 Console Auto-Fixer
    f3_how = [
        "<b>Step 1:</b> In the main dashboard, go to <b>Azam Features</b> &gt; <b>Console Fixer</b>.",
        "<b>Step 2:</b> Click the primary button labeled <b>Run Console Full Repair</b>.",
        "<b>Step 3:</b> Wait 3-5 seconds while the system executes the recovery sequence.",
        "<b>Step 4:</b> Review the output modal confirming Guacamole, Tomcat9, and Guacd service reloads."
    ]
    f3_bg = [
        "<b>Step 1:</b> API endpoint <code>POST /api/azam/console-fix-full</code> triggers <code>azambasha-fix-web-credentials.sh --fix-guac</code>.",
        "<b>Step 2:</b> System script kills orphaned <code>websockify</code> and stale Guacamole daemon worker threads.",
        "<b>Step 3:</b> Checks <code>/etc/guacamole/guacamole.properties</code> and MariaDB Guacamole user authorization tables.",
        "<b>Step 4:</b> Executes <code>systemctl restart guacd tomcat9</code> and verifies local socket listening on <code>127.0.0.1:4822</code>.",
        "<b>Step 5:</b> Flushes browser websocket cookies and returns JSON status <code>{success: true, services_reloaded: 3}</code>."
    ]
    for el in render_feature("3", "HTML5 Console Auto-Fixer & Session Cleaner", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Console Fixer</b> (<code>#pane-console</code>)",
                             f3_how, f3_bg):
        story.append(el)

    # Feature 4: Local, Cloud & Air-Gapped Backups
    f4_how = [
        "<b>Step 1:</b> Navigate to <b>Azam Features</b> &gt; <b>Cloud & Local Backups</b> tab.",
        "<b>Step 2:</b> To create an immediate local archive, click <b>Create Local Archive Now</b>.",
        "<b>Step 3:</b> To sync to remote cloud storage, configure AWS S3, Google Cloud, or Mega credentials in settings and click <b>Sync to Cloud</b>.",
        "<b>Step 4:</b> For isolated high-security environments, click <b>Generate Offline Airgap Bundle (.tar.gz)</b> in the Airgap Packaging card.",
        "<b>Step 5:</b> Once generated, click the direct download link or retrieve the tarball from <code>/opt/unetlab/data/Exports/</code>."
    ]
    f4_bg = [
        "<b>Step 1:</b> Request <code>POST /azam-ops/api/airgap-pack</code> or <code>POST /api/azam/backups/local</code> dispatches the bundler.",
        "<b>Step 2:</b> For Airgap packs, <code>azambasha-airgap-pack.sh</code> creates an offline archive containing Debian package archives, pip wheels, schemas, scripts, and web UI components.",
        "<b>Step 3:</b> Moves generated tarball to <code>/opt/unetlab/data/Exports/azam-pnet-airgap-bundle-latest.tar.gz</code> with read permissions.",
        "<b>Step 4:</b> For cloud backups, <code>azambasha-cloud-backup.sh</code> executes <code>rclone sync</code> with AES-256 encryption and validates SHA-256 checksums."
    ]
    for el in render_feature("4", "Local, Multi-Cloud & 100% Air-Gapped Bundler", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Cloud & Local Backups</b> (<code>#pane-cloud</code>)",
                             f4_how, f4_bg):
        story.append(el)

    # Feature 5: Fleet Multi-Node Cluster Monitor
    f5_how = [
        "<b>Step 1:</b> Go to <b>Azam Features</b> &gt; <b>Cluster Fleet Monitor</b> tab.",
        "<b>Step 2:</b> View all connected PNETLab satellite worker nodes, CPU/RAM utilization, and cluster health.",
        "<b>Step 3:</b> Click <b>Add Satellite Node</b> and enter worker IP, SSH Port, and Shared Token.",
        "<b>Step 4:</b> Click <b>Balance Workload</b> to redistribute virtual nodes across cluster hypervisors."
    ]
    f5_bg = [
        "<b>Step 1:</b> Backend daemon <code>azambasha-ops-api</code> queries satellite worker endpoints every 15s via HTTPS/mTLS.",
        "<b>Step 2:</b> Aggregates remote CPU, RAM, and bridge interface states into centralized memory cache.",
        "<b>Step 3:</b> Evaluates node placement affinity rules against worker RAM capacity prior to new VM dispatch.",
        "<b>Step 4:</b> If a worker becomes unresponsive (missing 3 heartbeats), marks node as Degraded and triggers alert hook."
    ]
    for el in render_feature("5", "Fleet Multi-Node Cluster Monitor", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Cluster Fleet</b> (<code>#pane-cluster</code>)",
                             f5_how, f5_bg):
        story.append(el)

    # Feature 6: Lab Capacity Planner
    f6_how = [
        "<b>Step 1:</b> Open <b>Azam Features</b> &gt; <b>Capacity & Sizing Planner</b> tab.",
        "<b>Step 2:</b> Enter estimated count of heavy appliances (e.g., Cisco XRv9k, Arista cEOS, Junos vMX, Linux servers).",
        "<b>Step 3:</b> The interactive calculator displays required vCPU, RAM, QCOW2 storage, and recommended KVM overcommit ratios.",
        "<b>Step 4:</b> Click <b>Apply Resource Limits</b> to enforce memory guardrails."
    ]
    f6_bg = [
        "<b>Step 1:</b> Calculator computes total theoretical footprint against actual available host hardware queried via <code>/proc/meminfo</code>.",
        "<b>Step 2:</b> Checks KSM (Kernel Samepage Merging) deduplication metrics via <code>/sys/kernel/mm/ksm/pages_sharing</code>.",
        "<b>Step 3:</b> Enforces safe limits by writing updated swap thresholds into <code>/etc/sysctl.d/99-pnetlab-perf.conf</code>.",
        "<b>Step 4:</b> Notifies administrator if requested deployment exceeds safe memory thresholds (over 85% host RAM)."
    ]
    for el in render_feature("6", "Lab Capacity & Hardware Sizing Planner", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Capacity Planner</b> (<code>#pane-capacity</code>)",
                             f6_how, f6_bg):
        story.append(el)

    # Feature 7: Comprehensive Diagnostic Doctor
    f7_how = [
        "<b>Step 1:</b> Navigate to <b>Azam Features</b> &gt; <b>System Doctor</b> tab.",
        "<b>Step 2:</b> Click <b>Run Full System Diagnostic</b>.",
        "<b>Step 3:</b> Observe 25+ automated checks spanning MySQL sockets, disk inodes, KVM permissions, bridge MTU, and DNS.",
        "<b>Step 4:</b> Click <b>Auto-Heal Detected Issues</b> to execute automated remediation."
    ]
    f7_bg = [
        "<b>Step 1:</b> Triggers execution of <code>/usr/local/bin/azambasha-doctor</code>.",
        "<b>Step 2:</b> Inspects MariaDB status via unix socket <code>/var/run/mysqld/mysqld.sock</code>.",
        "<b>Step 3:</b> Checks <code>/dev/kvm</code> permissions (<code>0666</code>), IP forwarding (<code>net.ipv4.ip_forward=1</code>), and bridge states.",
        "<b>Step 4:</b> If auto-heal is selected, executes repair routines, resets permissions on <code>/opt/unetlab/</code>, and returns diagnostic report."
    ]
    for el in render_feature("7", "Comprehensive Diagnostic Doctor", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>System Doctor</b> (<code>#pane-doctor</code>)",
                             f7_how, f7_bg):
        story.append(el)

    # Feature 8: QCOW2 Disk Shrinker
    f8_how = [
        "<b>Step 1:</b> Navigate to <b>Azam Features</b> &gt; <b>Storage Optimizer</b> tab.",
        "<b>Step 2:</b> Select target lab or device image directory from the dropdown menu.",
        "<b>Step 3:</b> Click <b>Scan for Reclaimable Space</b>.",
        "<b>Step 4:</b> Click <b>Shrink & Compress Selected Images</b> and observe real-time reclaimed gigabytes."
    ]
    f8_bg = [
        "<b>Step 1:</b> Background worker scans <code>/opt/unetlab/addons/qemu/</code> and active lab storage.",
        "<b>Step 2:</b> Executes <code>qemu-img info</code> to calculate virtual size vs. actual allocated disk blocks.",
        "<b>Step 3:</b> Invokes <code>azambasha-heavy-node-optimizer.sh --shrink</code> which runs <code>qemu-img convert -c -O qcow2</code> with zlib compression.",
        "<b>Step 4:</b> Replaces original image atomically, updating sparse metadata and freeing unused hypervisor blocks."
    ]
    for el in render_feature("8", "QCOW2 Disk Shrinker & Sparse Compressor", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Storage Optimizer</b> (<code>#pane-storage</code>)",
                             f8_how, f8_bg):
        story.append(el)

    # Feature 9: Cloud Transit Multi-Cloud Bridge
    f9_how = [
        "<b>Step 1:</b> Open <b>Azam Features</b> &gt; <b>Cloud Transit</b> tab.",
        "<b>Step 2:</b> Select transit provider: <b>Tailscale</b>, <b>ZeroTier</b>, or <b>WireGuard</b>.",
        "<b>Step 3:</b> Paste network auth key or configuration token and click <b>Connect Transit Bridge</b>.",
        "<b>Step 4:</b> Interconnect local lab Management Cloud (pnet0/pnet1) directly to AWS VPC, Azure VNet, or home LAN."
    ]
    f9_bg = [
        "<b>Step 1:</b> API executes <code>azambasha-cloud-transit.sh</code> with selected provider parameters.",
        "<b>Step 2:</b> Brings up virtual tun/tap interface (e.g. <code>tailscale0</code> or <code>wg0</code>) in host kernel.",
        "<b>Step 3:</b> Configures <code>iptables -t nat -A POSTROUTING -o &lt;tun_interface&gt; -j MASQUERADE</code> and enables proxy ARP.",
        "<b>Step 4:</b> Bridges virtual lab nodes directly to the remote cloud subnet without requiring public IPs."
    ]
    for el in render_feature("9", "Multi-Cloud Transit Overlay Bridge", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Cloud Transit</b> (<code>#pane-transit</code>)",
                             f9_how, f9_bg):
        story.append(el)

    # Feature 10: SSL Certbot & WhatsApp Alerts
    f10_how = [
        "<b>Step 1:</b> Go to <b>Azam Features</b> &gt; <b>Alerts & SSL</b> tab.",
        "<b>Step 2:</b> For SSL: enter fully qualified domain name (FQDN) and admin email, then click <b>Deploy Let's Encrypt SSL</b>.",
        "<b>Step 3:</b> For Alerts: enter Twilio Account SID, Auth Token, and WhatsApp recipient number.",
        "<b>Step 4:</b> Click <b>Send Test WhatsApp Alert</b> to verify real-time notification delivery."
    ]
    f10_bg = [
        "<b>Step 1:</b> SSL process runs <code>certbot certonly --standalone -d domain.com</code>, binding temporarily to port 80.",
        "<b>Step 2:</b> Automatically updates Nginx configuration in <code>/etc/nginx/sites-available/default</code> with TLS certificates and HTTP/2.",
        "<b>Step 3:</b> Reloads Nginx and sets up automatic certbot renewal cron job in <code>/etc/cron.d/certbot</code>.",
        "<b>Step 4:</b> WhatsApp service stores encrypted credentials in <code>/etc/pnetlab/alerts.conf</code> and transmits JSON payload via Twilio REST API."
    ]
    for el in render_feature("10", "Automated SSL & WhatsApp Alerts", "GUI: Outside Lab Canvas",
                             "Main Dashboard Navigation &gt; <b>Azam Features</b> &gt; <b>Alerts & SSL</b> (<code>#pane-alerts</code>)",
                             f10_how, f10_bg):
        story.append(el)

    # Feature 11: Version Synchronizer & PDF Operations Portal
    f11_how = [
        "<b>Step 1:</b> In the top navigation bar of the main dashboard, click the <b>Operations Manual (PDF)</b> button.",
        "<b>Step 2:</b> The document opens directly in a new browser tab with high-resolution vector layout.",
        "<b>Step 3:</b> To update the platform, go to <b>Azam Features</b> &gt; <b>Updates & Engine</b> tab.",
        "<b>Step 4:</b> Click <b>Check for Feature Updates</b> to compare local git commit against upstream release.",
        "<b>Step 5:</b> Click <b>Apply Updates & Re-link CLI Tools</b> to refresh system binaries."
    ]
    f11_bg = [
        "<b>Step 1:</b> Top header button directs browser to <code>/azam-ops/api/docs/manual</code> or <code>/docs/manual.pdf</code>.",
        "<b>Step 2:</b> REST API serves PDF directly from <code>/opt/azambasha/docs/</code> with <code>Content-Type: application/pdf</code>.",
        "<b>Step 3:</b> When update is clicked, queries git repository commit HEAD.",
        "<b>Step 4:</b> Executes <code>azambasha-install-azam-features.sh</code>, updating CLI symlinks in <code>/usr/local/bin/</code> and restarting <code>azambasha-ops-api.service</code>."
    ]
    for el in render_feature("11", "Version Synchronizer & Direct Operations Manual Portal", "GUI: Outside Lab Canvas",
                             "Main Dashboard Header &gt; <b>Operations Manual (PDF)</b> &amp; <b>Updates Tab</b> (<code>#pane-updates</code>)",
                             f11_how, f11_bg):
        story.append(el)

    story.append(PageBreak())

    # ==================== SECTION 4: INSIDE-THE-LAB FEATURES ====================
    story.append(Paragraph("4. Inside-the-Lab Canvas Features (Lab Workbench: /themes/default/)", section_heading))
    story.append(Paragraph(
        "Inside-the-lab features are integrated directly into the visual network topology canvas. "
        "They empower network engineers to execute live troubleshooting, staggered boot scheduling with KSM deduplication, automated version control commits, "
        "live traffic heatmaps, packet sniffing, and AI copilot queries without leaving the workbench.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Feature 12: Anti-Bootstorm & In-Canvas KSM
    f12_how = [
        "<b>Step 1:</b> Open any lab topology inside the PNETLab canvas workspace.",
        "<b>Step 2:</b> In the top workbench navigation toolbar, locate the purple button labeled <b>Anti-Bootstorm</b> (icon: lightning bolt).",
        "<b>Step 3:</b> In the modal, check the box <b>Boost with KSM Memory Deduplication</b>.",
        "<b>Step 4:</b> Select startup profile: <b>Conservative (15s delay)</b>, <b>Balanced (10s delay)</b>, or <b>Aggressive (5s delay)</b>.",
        "<b>Step 5:</b> Click <b>Start All Nodes Safely</b> and watch nodes boot sequentially without hypervisor overload."
    ]
    f12_bg = [
        "<b>Step 1:</b> Trigger executes <code>azamLaunchBootstormModal()</code> which fetches node list and KSM status.",
        "<b>Step 2:</b> If KSM booster is checked, client dispatches <code>POST /azam-ops/api/node-ksm-tune</code> setting <code>/sys/kernel/mm/ksm/run=1</code>.",
        "<b>Step 3:</b> Backend runs <code>azambasha-bootstorm.py</code> ordering nodes by weight (firewalls/spines first).",
        "<b>Step 4:</b> Inspects CPU utilization via <code>/proc/stat</code>; if load exceeds 80%, pauses until CPU stabilizes.",
        "<b>Step 5:</b> Boots nodes individually via <code>unl_wrapper -a start -i {id}</code>, preventing hypervisor OOM panics."
    ]
    for el in render_feature("12", "Anti-Bootstorm Staggered Startup & In-Canvas KSM Booster", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Toolbar &gt; <b>Anti-Bootstorm</b> button (<code>#btn-azam-bootstorm</code>)",
                             f12_how, f12_bg):
        story.append(el)

    # Feature 13: Topology Git VCS & Auto-Commit
    f13_how = [
        "<b>Step 1:</b> Inside the lab canvas, click the <b>Git Version Control</b> icon in the left toolbar (branch icon, <code>#btn-azam-git-vcs</code>).",
        "<b>Step 2:</b> A slide-over drawer displays commit history, authors, and timestamps.",
        "<b>Step 3:</b> When you add nodes, connect interfaces, or save the lab, the system triggers an <b>Automated Auto-Commit</b> in the background.",
        "<b>Step 4:</b> To create a named checkpoint: enter a commit message (e.g. 'Configured OSPF Area 0') and click <b>Commit Topology State</b>.",
        "<b>Step 5:</b> To rollback: click <b>Restore</b> next to any historical commit; the canvas automatically reloads."
    ]
    f13_bg = [
        "<b>Step 1:</b> On drawer open, fetches commit history via <code>GET /api/azam/topology-log?lab={lab_name}</code>.",
        "<b>Step 2:</b> Ensures lab folder <code>/opt/unetlab/labs/&lt;lab&gt;</code> is initialized with git; if not, runs <code>git init</code>.",
        "<b>Step 3:</b> When topology changes occur, front-end issues <code>POST /azam-ops/api/topology-autocommit</code>.",
        "<b>Step 4:</b> Stages the <code>.unl</code> XML file and creates a git commit with timestamp and change description.",
        "<b>Step 5:</b> On rollback, checks out historical snapshot via <code>git checkout &lt;hash&gt; -- &lt;lab.unl&gt;</code> and dispatches reload event."
    ]
    for el in render_feature("13", "Topology Git Version Control & Automated Auto-Commit", "GUI: Inside Lab Canvas",
                             "Lab Workbench Left Sidebar &gt; <b>Git VCS</b> icon (<code>#btn-azam-git-vcs</code>) &gt; Slide-Over Drawer",
                             f13_how, f13_bg):
        story.append(el)

    # Feature 14: In-Canvas HTML5 Console Healer
    f14_how = [
        "<b>Step 1:</b> While inside a lab, if clicking a node yields a blank screen or 'Connection Refused', stay on the canvas.",
        "<b>Step 2:</b> Click the green button in the top toolbar labeled <b>Fix Console</b> (icon: wrench).",
        "<b>Step 3:</b> A confirmation toast appears: 'Restarting HTML5 Console Services...'",
        "<b>Step 4:</b> Wait 2 seconds until the success notification appears ('Console services recovered successfully').",
        "<b>Step 5:</b> Re-click the node to open the working HTML5 terminal immediately."
    ]
    f14_bg = [
        "<b>Step 1:</b> Button executes <code>azamFixConsoleNow()</code> sending asynchronous <code>POST /api/azam/console-fix-full</code>.",
        "<b>Step 2:</b> API server invokes <code>azambasha-fix-web-credentials.sh</code> targeting Guacamole and Tomcat daemon sockets.",
        "<b>Step 3:</b> Flushes stuck client sessions in Guacamole memory cache and verifies port 4822 binds properly.",
        "<b>Step 4:</b> Resets browser terminal session iframe tokens without requiring a full page reload."
    ]
    for el in render_feature("14", "In-Workbench Quick Console Healer", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Toolbar &gt; <b>Fix Console</b> button (<code>#btn-azam-fix-console</code>)",
                             f14_how, f14_bg):
        story.append(el)

    # Feature 15: Live Wireshark & Traffic Heatmap
    f15_how = [
        "<b>Step 1:</b> In the top workbench toolbar, click the pulse icon button labeled <b>Traffic Heatmap</b>.",
        "<b>Step 2:</b> Observe canvas links transition to dynamic color codes: Green (idle/normal &lt;1 Mbps), Yellow (moderate 1-10 Mbps), Red (saturated &gt;10 Mbps).",
        "<b>Step 3:</b> To sniff packets on a specific interface, right-click any device node and select <b>Live Capture (Wireshark)</b>.",
        "<b>Step 4:</b> The capture drawer opens showing live packet decode, or click <b>Download PCAP</b> for local Wireshark analysis."
    ]
    f15_bg = [
        "<b>Step 1:</b> Heatmap engine polls <code>GET /azam-ops/api/link-stats</code> every 3 seconds.",
        "<b>Step 2:</b> Backend reads virtual TAP counters from <code>/sys/class/net/vnet*/statistics/rx_bytes</code> and calculates delta rate (bytes/sec).",
        "<b>Step 3:</b> Front-end matches virtual interfaces to SVG link paths, updating <code>stroke</code> color dynamically.",
        "<b>Step 4:</b> For packet capture, host spawns <code>tcpdump -i vnetX_Y -U -w -</code> and streams raw PCAP bytes over HTTP."
    ]
    for el in render_feature("15", "Live Wireshark Sniffer & In-Canvas Traffic Heatmap", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Toolbar &gt; <b>Traffic Heatmap</b> button (<code>#pnq-btn-heatmap</code>) &amp; Context Menu",
                             f15_how, f15_bg):
        story.append(el)

    # Feature 16: AI Lab Copilot & Desktop Notifications
    f16_how = [
        "<b>Step 1:</b> Click the floating <b>AI Assistant</b> widget at the bottom-right corner of the canvas.",
        "<b>Step 2:</b> Type a query: 'Why isn't BGP EVPN establishing between Leaf1 and Leaf2?' or 'Generate Arista MLAG config'.",
        "<b>Step 3:</b> The AI Copilot analyzes the active topology and streams back verified configuration snippets.",
        "<b>Step 4:</b> If you minimize your browser during long operations, HTML5 Desktop Push Notifications will alert your operating system upon completion."
    ]
    f16_bg = [
        "<b>Step 1:</b> Client serializes current topology structure (nodes, images, links) and queries <code>POST /api/azam/ai-copilot</code>.",
        "<b>Step 2:</b> AI Copilot engine analyzes network architecture against vendor syntax guides (Cisco, Arista, Juniper).",
        "<b>Step 3:</b> Desktop notification helper <code>azamNotifyDesktop()</code> invokes the browser HTML5 Notification API.",
        "<b>Step 4:</b> Pushes native desktop OS toast notifications when Anti-Bootstorm finishes or system health warnings occur."
    ]
    for el in render_feature("16", "AI Lab Copilot & HTML5 OS-Level Desktop Notifications", "GUI: Inside Lab Canvas",
                             "Lab Workbench &gt; Floating Action Widget (Bottom-Right) &amp; OS Desktop Notification Service",
                             f16_how, f16_bg):
        story.append(el)

    # Feature 17: Multi-Node Config Diff
    f17_how = [
        "<b>Step 1:</b> Inside the lab, click <b>Management Tools</b> in the canvas sidebar &gt; <b>Config Diff Engine</b>.",
        "<b>Step 2:</b> Select nodes to compare or choose between two historical configuration snapshots.",
        "<b>Step 3:</b> The split-screen diff viewer highlights added lines in green, removed lines in red, and modified syntax in yellow.",
        "<b>Step 4:</b> Click <b>Rollback Node Config</b> to push previous baseline syntax back to the device."
    ]
    f17_bg = [
        "<b>Step 1:</b> Queries <code>/opt/unetlab/tmp/{lab_id}/{node_id}/startup-config</code> and running snapshots.",
        "<b>Step 2:</b> Python <code>difflib</code> compares normalized configuration text, ignoring non-functional whitespace.",
        "<b>Step 3:</b> Renders unified diff payload and returns structured JSON to client-side CodeMirror diff editor.",
        "<b>Step 4:</b> On rollback, writes chosen config directly to node flash storage via unl wrapper."
    ]
    for el in render_feature("17", "Multi-Node Config Diff & Rollback Engine", "GUI: Inside Lab Canvas",
                             "Lab Workbench &gt; Canvas Management Menu &gt; <b>Config Diff Engine</b>",
                             f17_how, f17_bg):
        story.append(el)

    # Feature 18: Automated Exam Grader
    f18_how = [
        "<b>Step 1:</b> Click <b>Lab Actions</b> in the canvas top menu &gt; <b>Run Lab Assessment / Exam Grader</b>.",
        "<b>Step 2:</b> Select test rubric (e.g. CCNA Routing, BGP Multi-Homing, OSPF Area Verification).",
        "<b>Step 3:</b> Click <b>Execute Validation Tests</b>.",
        "<b>Step 4:</b> View real-time checklist: green ticks for passed objectives, red marks for failed requirements, and final score percentage."
    ]
    f18_bg = [
        "<b>Step 1:</b> Backend orchestrator initiates automated Telnet/SSH probes to target node console ports.",
        "<b>Step 2:</b> Executes verification commands (e.g. <code>show ip route</code>, <code>show ip bgp summary</code>).",
        "<b>Step 3:</b> Regex parsing engine validates prefix reachability, next-hop IP, and protocol neighbor states.",
        "<b>Step 4:</b> Generates scorecard and saves PDF/JSON certificate in <code>/opt/unetlab/labs/{lab}/results/</code>."
    ]
    for el in render_feature("18", "Automated Lab Exam Grader", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Bar &gt; <b>Lab Actions</b> &gt; <b>Run Exam Evaluation</b>",
                             f18_how, f18_bg):
        story.append(el)

    # Feature 19: Ping Mesh & Traffic Generator
    f19_how = [
        "<b>Step 1:</b> In the canvas menu, select <b>Lab Testing</b> &gt; <b>Ping Mesh & Traffic Generator</b>.",
        "<b>Step 2:</b> Select participating nodes or choose 'Full Mesh All Running Nodes'.",
        "<b>Step 3:</b> Set packet size (64 to 9000 bytes) and rate (pps).",
        "<b>Step 4:</b> Click <b>Start Mesh Test</b> to view latency matrix heatmap, packet loss, and jitter."
    ]
    f19_bg = [
        "<b>Step 1:</b> Orchestrator dispatches lightweight ICMP/UDP echo requests across all node bridge endpoints.",
        "<b>Step 2:</b> Collects round-trip time (RTT) telemetry and calculates minimum, average, and maximum latency.",
        "<b>Step 3:</b> Renders interactive matrix heatmap in the canvas interface.",
        "<b>Step 4:</b> Detects path MTU blackholes if packets above 1500 bytes drop unexpectedly."
    ]
    for el in render_feature("19", "Ping Mesh & Traffic Generator Engine", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Bar &gt; <b>Lab Testing</b> &gt; <b>Ping Mesh & Traffic</b>",
                             f19_how, f19_bg):
        story.append(el)

    # Feature 20: High-Res Diagram Exporter
    f20_how = [
        "<b>Step 1:</b> Inside the canvas, click <b>Export</b> in the top-right toolbar &gt; <b>Export Topology Vector/PNG</b>.",
        "<b>Step 2:</b> Choose output format: <b>Scalable Vector Graphics (SVG)</b> or <b>High-Res PNG (300 DPI)</b>.",
        "<b>Step 3:</b> Toggle options: Include IP labels, Include interface names, Watermark with company logo.",
        "<b>Step 4:</b> Click <b>Download Image File</b> for presentation-ready architecture diagrams."
    ]
    f20_bg = [
        "<b>Step 1:</b> JavaScript reads SVG DOM elements representing nodes, custom shapes, text labels, and link paths.",
        "<b>Step 2:</b> Normalizes viewBox coordinates, converts external image icons into inline base64 data URIs.",
        "<b>Step 3:</b> Applies CSS styling and embeds vector fonts directly into the standalone SVG document.",
        "<b>Step 4:</b> Triggers instant browser download without round-tripping to server, preserving client privacy."
    ]
    for el in render_feature("20", "High-Resolution Lab Diagram Exporter", "GUI: Inside Lab Canvas",
                             "Lab Workbench Top Bar &gt; <b>Export</b> &gt; <b>Export Topology Diagram</b>",
                             f20_how, f20_bg):
        story.append(el)

    # Feature 21: Interactive Canvas Accelerators
    f21_how = [
        "<b>Step 1:</b> Locate the interactive <b>Minimap Overview</b> at the bottom-left of the canvas.",
        "<b>Step 2:</b> Drag the viewport indicator in the minimap to pan smoothly across large topologies with 50+ nodes.",
        "<b>Step 3:</b> Select multiple nodes and press <b>Shift + S</b> to snap to grid or <b>Shift + A</b> for automatic alignment.",
        "<b>Step 4:</b> Use mouse wheel for continuous zoom from 25% overview to 200% detail view."
    ]
    f21_bg = [
        "<b>Step 1:</b> Canvas rendering engine creates a secondary hardware-accelerated HTML5 canvas element for the minimap.",
        "<b>Step 2:</b> Listens to canvas pan/zoom transform matrices and recalculates viewport bounding box in real-time.",
        "<b>Step 3:</b> Snap-to-grid algorithm calculates modulo-20 coordinate snapping for node drag events.",
        "<b>Step 4:</b> Persists updated coordinates directly to the underlying <code>.unl</code> XML file upon mouse release."
    ]
    for el in render_feature("21", "Interactive Canvas Accelerators & Minimap", "GUI: Inside Lab Canvas",
                             "Lab Workbench Canvas &gt; Bottom-Left <b>Minimap</b> &amp; Keyboard Accelerators",
                             f21_how, f21_bg):
        story.append(el)

    story.append(PageBreak())

    # ==================== SECTION 5: BACKGROUND DAEMONS ====================
    story.append(Paragraph("5. Background Daemons & Kernel Infrastructure", section_heading))
    story.append(Paragraph(
        "These core features operate autonomously beneath the graphical interface on both Master and Satellite nodes. "
        "They maintain hypervisor stability, self-heal system services, enable hardware-accelerated networking, and perform scheduled system maintenance.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Feature 22: 24/7 Watchdog Daemon
    f22_how = [
        "<b>Step 1:</b> The watchdog runs autonomously as a Linux systemd service: <code>azam-watchdog.service</code> on both Master and Satellite nodes.",
        "<b>Step 2:</b> To inspect live status, open an SSH terminal and run: <code>systemctl status azam-watchdog</code>.",
        "<b>Step 3:</b> To view event logs: <code>tail -f /var/log/azambasha-watchdog.log</code>.",
        "<b>Step 4:</b> No manual interaction is needed; the service auto-starts on boot and runs continuously."
    ]
    f22_bg = [
        "<b>Step 1:</b> Daemon wakes up every 60 seconds and evaluates host health metrics.",
        "<b>Step 2:</b> Inspects essential processes; if any core service is down, triggers automated restart.",
        "<b>Step 3:</b> Monitors available system RAM; if free RAM drops below 5%, identifies hung QEMU processes and alerts.",
        "<b>Step 4:</b> Cleans up zombie processes and stale temporary lock files in <code>/tmp</code> to prevent hypervisor starvation."
    ]
    for el in render_feature("22", "24/7 Self-Healing System Watchdog Daemon", "Background Daemon Plane (Master & Satellite)",
                             "Linux Systemd Service &gt; <code>azam-watchdog.service</code> (Autonomous 24/7)",
                             f22_how, f22_bg):
        story.append(el)

    # Feature 23: MySQL Socket & Credentials Healer
    f23_how = [
        "<b>Step 1:</b> The healer runs automatically during boot, hourly via cron, and upon admin request on the Master Node.",
        "<b>Step 2:</b> To trigger manual repair from CLI, execute: <code>azambasha-fix-web-credentials</code>.",
        "<b>Step 3:</b> The script inspects database user passwords, table permissions, and socket symlinks.",
        "<b>Step 4:</b> Confirms with output message: <code>[OK] Web credentials and MySQL socket successfully verified</code>."
    ]
    f23_bg = [
        "<b>Step 1:</b> Checks if MariaDB unix socket exists at <code>/var/run/mysqld/mysqld.sock</code>; if missing, creates symlink.",
        "<b>Step 2:</b> Connects to database and verifies <code>pnetlab</code> user credentials match <code>/opt/unetlab/html/includes/config.php</code>.",
        "<b>Step 3:</b> Synchronizes Guacamole database credentials in <code>/etc/guacamole/guacamole.properties</code>.",
        "<b>Step 4:</b> Flushes MariaDB privileges (<code>FLUSH PRIVILEGES;</code>) and verifies read/write integrity."
    ]
    for el in render_feature("23", "MySQL Socket & Credential Auto-Healer", "Background Daemon Plane (Master Only)",
                             "Systemd Hook &amp; Cron &gt; <code>/usr/local/bin/azambasha-fix-web-credentials</code>",
                             f23_how, f23_bg):
        story.append(el)

    # Feature 24: Soft-RoCE RXE & Jumbo MTU Engine
    f24_how = [
        "<b>Step 1:</b> Activated on both Master and Satellite nodes during setup via <code>azambasha-os-prerequisites.sh</code>.",
        "<b>Step 2:</b> To inspect RDMA status, run: <code>rdma link</code> or <code>ibv_devices</code>.",
        "<b>Step 3:</b> To verify Jumbo Frame MTU across bridge interfaces: <code>ip link show | grep mtu</code>.",
        "<b>Step 4:</b> All virtual bridges (pnet0 through pnet9) operate with MTU 9000 for high-throughput packet emulation."
    ]
    f24_bg = [
        "<b>Step 1:</b> Loads Linux kernel modules <code>rdma_rxe</code> and <code>ib_core</code> into kernel memory.",
        "<b>Step 2:</b> Binds software RoCE (RDMA over Converged Ethernet) devices to physical NIC interfaces.",
        "<b>Step 3:</b> Configures <code>udev</code> rules and <code>/etc/network/interfaces</code> setting bridge MTU to 9000.",
        "<b>Step 4:</b> Eliminates CPU packet fragmentation overhead for high-speed emulated links (e.g. 10G/40G data center fabrics)."
    ]
    for el in render_feature("24", "Soft-RoCE RXE & MTU 9000 Network Accelerator", "Kernel Infrastructure Plane (Master & Satellite)",
                             "Linux Kernel Module &amp; Network Configuration (<code>/etc/modprobe.d/</code>, <code>udev</code>)",
                             f24_how, f24_bg):
        story.append(el)

    # Feature 25: Scheduled Maintenance & TRIM Engine
    f25_how = [
        "<b>Step 1:</b> Scheduled automatically via cron on Master and Satellite nodes: <code>/etc/cron.d/azambasha-maintenance</code>.",
        "<b>Step 2:</b> Executes nightly at 03:00 UTC without disrupting running user labs.",
        "<b>Step 3:</b> To run on demand from CLI: <code>azambasha-heavy-node-optimizer.sh --maintenance</code>.",
        "<b>Step 4:</b> Check maintenance log at: <code>/var/log/azambasha-maintenance.log</code>."
    ]
    f25_bg = [
        "<b>Step 1:</b> Executes <code>fstrim -av</code> to issue TRIM commands to underlying SSD/NVMe storage, recovering deleted blocks.",
        "<b>Step 2:</b> Clears Linux dentry and inode pagecache buffers via <code>sysctl vm.drop_caches=3</code> if system is idle.",
        "<b>Step 3:</b> Truncates log files in <code>/opt/unetlab/data/Logs/</code> older than 14 days and compresses historical archives.",
        "<b>Step 4:</b> Empties orphaned sockets in <code>/opt/unetlab/tmp/</code> left behind by abnormally terminated nodes."
    ]
    for el in render_feature("25", "Scheduled Maintenance & Storage TRIM Engine", "Background Daemon Plane (Master & Satellite)",
                             "System Cron &gt; <code>/etc/cron.d/azambasha-maintenance</code> (Nightly 03:00 UTC)",
                             f25_how, f25_bg):
        story.append(el)

    story.append(PageBreak())

    # ==================== SECTION 6: CLI QUICK REFERENCE ====================
    story.append(Paragraph("6. Enterprise CLI Command-Line Reference & Distribution", section_heading))
    story.append(Paragraph(
        "All twenty-six Azam-Pnet enterprise utilities are symlinked globally in <code>/usr/local/bin/</code> across both Master and Satellite nodes. "
        "This ensures that infrastructure engineers possess identical troubleshooting capabilities from SSH terminals regardless of node type.",
        body_style
    ))
    story.append(Spacer(1, 4))

    cli_data = [
        [Paragraph("Command / Utility", table_header_style), Paragraph("Target Feature / Scope", table_header_style), Paragraph("Typical Invocation / Options", table_header_style), Paragraph("Node Support", table_header_style)],
        [Paragraph("azam-airgap-pack", table_cell_style), Paragraph("Offline Air-Gapped Bundler", table_cell_style), Paragraph("azam-airgap-pack [output_dir]", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azam-watchdog", table_cell_style), Paragraph("24/7 Autonomous Watchdog", table_cell_style), Paragraph("systemctl status azam-watchdog", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-ops-api", table_cell_style), Paragraph("REST API Daemon Backend", table_cell_style), Paragraph("systemctl restart azam-ops-api", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("azambasha-bootstorm", table_cell_style), Paragraph("Anti-Bootstorm &amp; KSM Engine", table_cell_style), Paragraph("azambasha-bootstorm --lab &lt;lab.unl&gt;", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-doctor", table_cell_style), Paragraph("Diagnostic Health Suite", table_cell_style), Paragraph("azambasha-doctor --full --auto-heal", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-fix-web-credentials", table_cell_style), Paragraph("MySQL &amp; Guac Socket Fixer", table_cell_style), Paragraph("azambasha-fix-web-credentials --fix-guac", table_cell_style), Paragraph("Master Only", table_cell_style)],
        [Paragraph("azambasha-heavy-node-optimizer", table_cell_style), Paragraph("QCOW2 Disk &amp; RAM Optimizer", table_cell_style), Paragraph("azambasha-heavy-node-optimizer --shrink", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-cloud-backup", table_cell_style), Paragraph("Local &amp; Cloud Backup Engine", table_cell_style), Paragraph("azambasha-cloud-backup --local --cloud s3", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-cloud-transit", table_cell_style), Paragraph("Cloud Transit Overlay Bridge", table_cell_style), Paragraph("azambasha-cloud-transit --tailscale --connect", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-install-azam-features", table_cell_style), Paragraph("Symlink &amp; Package Installer", table_cell_style), Paragraph("azambasha-install-azam-features.sh [--satellite]", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-fix-network-boot", table_cell_style), Paragraph("Bridge &amp; TAP Network Boot Fix", table_cell_style), Paragraph("azambasha-fix-network-boot.sh", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
        [Paragraph("azambasha-fix-export-and-apt", table_cell_style), Paragraph("Ubuntu Package Repository Fix", table_cell_style), Paragraph("azambasha-fix-export-and-apt.sh", table_cell_style), Paragraph("Master &amp; Satellite", table_cell_style)],
    ]
    t_cli = Table(cli_data, colWidths=[130, 120, 160, 94])
    t_cli.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_secondary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('BOX', (0, 0), (-1, -1), 1, c_secondary),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg])
    ]))
    story.append(t_cli)
    story.append(Spacer(1, 10))

    # ==================== SECTION 7: FUTURE VM PROVISIONING ====================
    story.append(Paragraph("7. Future VM Automated Provisioning & Verification Guide", section_heading))
    story.append(Paragraph(
        "To guarantee 100% feature alignment on every future virtual machine, the installer scripts in the Azam-Pnet repository have been "
        "standardized into two automated workflows:",
        body_style
    ))
    story.append(Spacer(1, 4))

    vms_info = [
        [
            Paragraph("<b>Future Master VM Provisioning:</b><br/>"
                      "1. Boot a fresh Ubuntu 20.04/22.04/24.04/26.04 server.<br/>"
                      "2. Clone the repository to <code>/opt/azambasha</code>.<br/>"
                      "3. Execute <code>bash /opt/azambasha/install.sh</code>.<br/>"
                      "4. The installer automatically provisions all web assets, MariaDB credentials, Apache/Nginx routing, compiles the REST API daemon, links all 26 CLI tools, and verifies health via Test 6.",
                      table_cell_style),
            Paragraph("<b>Future Satellite VM Provisioning:</b><br/>"
                      "1. Boot a fresh Ubuntu server with KVM virtualization enabled.<br/>"
                      "2. Clone the repository to <code>/opt/azambasha</code>.<br/>"
                      "3. Execute <code>bash /opt/azambasha/install-satellite.sh</code>.<br/>"
                      "4. In Step 9, the script automatically triggers <code>azambasha-install-azam-features.sh --satellite</code>, deploying all 26 CLI symlinks, watchdog daemon, KSM tuning, and TRIM cron in headless mode.",
                      table_cell_style)
        ]
    ]
    t_vms = Table(vms_info, colWidths=[250, 254])
    t_vms.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('BOX', (0, 0), (-1, -1), 1, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_vms)
    story.append(Spacer(1, 10))

    # Summary Box
    summary_text = [
        [Paragraph("<b>Documentation Summary & Compliance Note:</b><br/>"
                   "This manual encompasses all 25 enterprise features and 9 advanced platform enhancements integrated into the Azam-Pnet platform. "
                   "All API endpoints, UI placements, and background scripts adhere to the platform's non-destructive "
                   "design architecture. Stale websockets, hypervisor memory thresholds, and disk structures are guarded "
                   "by automated checks to guarantee continuous lab uptime across both Master and Satellite compute nodes.", body_style)]
    ]
    t_sum = Table(summary_text, colWidths=[504])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#86EFAC")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_sum)

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF generated successfully at: {filename_dest}")


if __name__ == "__main__":
    desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if not os.path.exists(desktop_dir):
        desktop_dir = os.path.expanduser("~/Desktop")
        
    desktop_pdf = os.path.join(desktop_dir, "Azam-Pnet_Enterprise_Features_Operations_Manual.pdf")
    docs_pdf = os.path.join(os.getcwd(), "docs", "Azam-Pnet_Enterprise_Features_Operations_Manual.pdf")

    os.makedirs(os.path.dirname(docs_pdf), exist_ok=True)

    # Build directly to desktop
    build_pdf(desktop_pdf)

    # Also copy to docs/ inside repository
    shutil.copyfile(desktop_pdf, docs_pdf)
    print(f"[SUCCESS] Also copied PDF to repository docs: {docs_pdf}")
